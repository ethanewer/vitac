#!/usr/bin/env bun
/**
 * Voice trial runner: creates voice sessions on primary + collaborator OpenCode servers,
 * routes audio between them, detects completion, writes result JSON.
 *
 * Usage: bun run ts-runner/run-trial.ts <config.json> <output.json>
 */

import { createOpencodeClient } from "@opencode-ai/sdk/v2/client"
import { createVoiceSession, tts, pcmToWav, stt } from "@opencode-ai/sdk/v2/voice"
import type { TrialConfig, TrialResult, VoiceMessageLog } from "./types.js"

const configPath = Bun.argv[2]
const outputPath = Bun.argv[3]

if (!configPath || !outputPath) {
  console.error("Usage: bun run run-trial.ts <config.json> <output.json>")
  process.exit(1)
}

const config: TrialConfig = JSON.parse(await Bun.file(configPath).text())

const maxTimeout = config.maxTimeoutMs ?? 360_000
const voiceMessages: VoiceMessageLog[] = []
const terminalCommands: string[] = []
let totalInputTokens = 0
let totalOutputTokens = 0

// Connect to both OpenCode servers
const primaryClient = createOpencodeClient({ baseUrl: config.primaryUrl })
const collabClient = createOpencodeClient({ baseUrl: config.collabUrl })

// Wait for servers to be ready (retry a few times)
async function waitForServer(client: ReturnType<typeof createOpencodeClient>, name: string, maxRetries = 30) {
  for (let i = 0; i < maxRetries; i++) {
    try {
      await client.session.list()
      console.log(`${name} server ready`)
      return
    } catch {
      if (i === maxRetries - 1) throw new Error(`${name} server not ready after ${maxRetries} retries`)
      await Bun.sleep(1000)
    }
  }
}

await Promise.all([
  waitForServer(primaryClient, "Primary"),
  waitForServer(collabClient, "Collaborator"),
])

// System prompt for the primary agent
const primarySystem = `You are completing a coding task. You have access to a bash shell and file editing tools.

YOUR TASK:
${config.instruction}

WORKFLOW:
1. If the task says to ask your collaborator, ask ONE clear question and wait for their response.
2. After getting the collaborator's answer, immediately execute the necessary commands.
3. Verify the result (e.g., check file contents).
4. Say "TASK_COMPLETE" when done.

RULES:
- Include the exact phrase "TASK_COMPLETE" in your response when the task is fully done.
- Do NOT say TASK_COMPLETE until commands have run and you've verified the result.
- Do NOT keep chatting after executing commands. Verify and complete.
- Keep bash commands simple and single-line.`

// System prompt for the collaborator
const collabSystem = `You are a helpful collaborator assisting someone with a coding task.
You do NOT have access to a terminal or any tools. You can only provide information and guidance through conversation.
Answer questions concisely and specifically. Don't volunteer information that wasn't asked about.

CONTEXT:
${config.collaboratorContext}`

console.log("Creating voice sessions...")

// Create primary voice session
const primarySession = await createVoiceSession(primaryClient, {
  agent: "voice-build",
  model: config.model,
  system: primarySystem,
  permission: "dangerous",
  nativeAudioInput: config.nativeAudioInput,
  nativeAudioOutput: config.nativeAudioOutput,
  tts: config.ttsOptions ? {
    model: config.ttsOptions.model,
    apiKey: config.ttsOptions.apiKey,
    baseUrl: config.ttsOptions.baseUrl,
    voice: config.ttsOptions.voice ?? config.voice ?? "coral",
  } : { voice: config.voice ?? "coral" },
  stt: config.sttOptions ? {
    model: config.sttOptions.model,
    apiKey: config.sttOptions.apiKey,
    baseUrl: config.sttOptions.baseUrl,
  } : undefined,
  toolStatus: false,
})

// Create collaborator voice session (no tools allowed)
const collabSession = await createVoiceSession(collabClient, {
  agent: "voice-build",
  model: config.collabModel ?? config.model,
  system: collabSystem,
  permission: [{ permission: "*", pattern: "*", action: "deny" as const }],
  nativeAudioInput: config.nativeAudioInput,
  nativeAudioOutput: config.nativeAudioOutput,
  tts: config.ttsOptions ? {
    model: config.ttsOptions.model,
    apiKey: config.ttsOptions.apiKey,
    baseUrl: config.ttsOptions.baseUrl,
    voice: config.ttsOptions.voice ?? "shimmer",
  } : { voice: "shimmer" },
  stt: config.sttOptions ? {
    model: config.sttOptions.model,
    apiKey: config.sttOptions.apiKey,
    baseUrl: config.sttOptions.baseUrl,
  } : undefined,
  toolStatus: false,
})

console.log(`Primary session: ${primarySession.sessionID}`)
console.log(`Collaborator session: ${collabSession.sessionID}`)

// Track completion
let completed = false
let error: string | undefined

// Monitor primary SSE events for completion detection and terminal commands
const primaryEventCtrl = new AbortController()
const primaryEvents = await primaryClient.event.subscribe({}, { signal: primaryEventCtrl.signal })

const sseMonitor = (async () => {
  let textBuffer = ""
  try {
    for await (const event of primaryEvents.stream) {
      if (completed) break
      const evt = event as any

      // Track text output for completion detection
      if (evt.type === "message.part.delta" && evt.properties.sessionID === primarySession.sessionID) {
        if (evt.properties.field === "text") {
          textBuffer += evt.properties.delta
          if (textBuffer.includes("TASK_COMPLETE")) {
            console.log("Detected TASK_COMPLETE")
            completed = true
            break
          }
        }
      }

      // Track terminal commands
      if (evt.type === "message.part.updated" && evt.properties.sessionID === primarySession.sessionID) {
        const part = evt.properties.part
        if (part?.type === "tool" && part?.tool === "bash" && part?.state?.status === "completed") {
          const input = part.state?.input?.command
          if (input) terminalCommands.push(input)
        }
      }

      // Reset text buffer on idle (new turn)
      if (evt.type === "session.status" && evt.properties.sessionID === primarySession.sessionID) {
        if (evt.properties.status?.type === "idle") {
          textBuffer = ""
        }
      }
    }
  } catch {
    // Stream ended or aborted
  }
})()

// Accumulate audio chunks into complete utterances before forwarding.
// The voice session's input loop expects complete WAV files per queue item.
// We accumulate PCM until we have a meaningful amount of audio, then forward as WAV.
async function routeAudio(
  source: typeof primarySession.output,
  dest: typeof collabSession.input,
  sender: "primary" | "collaborator",
) {
  const recipient = sender === "primary" ? "collaborator" : "primary"
  let chunks: Uint8Array[] = []
  let totalLen = 0
  // PCM at 24kHz 16-bit mono = 48000 bytes/sec
  const MIN_BYTES_TO_SEND = 48000 * 2 // 2 seconds minimum utterance

  const flushToDestination = async () => {
    if (totalLen === 0) return
    const merged = new Uint8Array(totalLen)
    let off = 0
    for (const c of chunks) {
      merged.set(c, off)
      off += c.length
    }
    chunks = []
    totalLen = 0

    // Wrap as WAV and send to destination's input queue
    const wav = pcmToWav(merged, { sampleRate: 24000, channels: 1, bitDepth: 16 })
    dest.push(wav)

    // Also transcribe for logging
    let transcript = ""
    try {
      transcript = await stt(wav, { apiKey: config.ttsOptions?.apiKey })
    } catch {
      transcript = "[audio]"
    }
    voiceMessages.push({ sender, recipient, transcript, timestampMs: Date.now() })
    console.log(`${sender} -> ${recipient}: ${transcript.slice(0, 200)}`)
  }

  // Use a timer to flush accumulated audio after a silence gap
  let flushTimer: ReturnType<typeof setTimeout> | null = null
  const SILENCE_GAP_MS = 1500 // flush after 1.5s of no new audio

  for await (const pcm of source) {
    if (completed) break
    chunks.push(pcm)
    totalLen += pcm.length

    // Reset the silence timer
    if (flushTimer) clearTimeout(flushTimer)

    // If we have enough audio, flush immediately
    if (totalLen >= MIN_BYTES_TO_SEND) {
      await flushToDestination()
    } else {
      // Set timer to flush after silence gap
      flushTimer = setTimeout(() => {
        flushToDestination().catch(() => {})
      }, SILENCE_GAP_MS)
    }
  }

  // Flush remaining
  if (flushTimer) clearTimeout(flushTimer)
  await flushToDestination()
}

// Route audio between sessions
const primaryToCollab = routeAudio(primarySession.output, collabSession.input, "primary")
const collabToPrimary = routeAudio(collabSession.output, primarySession.input, "collaborator")

// Send the initial instruction via text prompt, but DON'T mark completed when it returns.
// The agent will likely ask the collaborator a question, and we need the voice routing
// loop to handle the multi-turn conversation.
console.log("Sending instruction to primary agent...")
console.log(`Model: ${config.model.providerID}/${config.model.modelID}`)

// Send the initial instruction as a text prompt. After this, the voice routing
// handles multi-turn conversation automatically (primary speaks → collab hears →
// collab responds → primary hears → primary continues).
const promptDone = primaryClient.session.prompt({
  sessionID: primarySession.sessionID,
  agent: "voice-build",
  parts: [{ type: "text", text: config.instruction }],
  ...(config.model ? { model: config.model } : {}),
  system: primarySystem,
}).then((result) => {
  console.log("Initial prompt completed", result?.error ? `with error: ${JSON.stringify(result.error)}` : "successfully")
}).catch((e: any) => {
  console.error("Initial prompt error:", e?.message ?? e)
  if (!error) error = `Prompt error: ${e?.message ?? e}`
  completed = true
})

voiceMessages.push({
  sender: "collaborator",
  recipient: "primary",
  transcript: config.instruction,
  timestampMs: Date.now(),
})

// Wait for completion or timeout
const timeoutPromise = new Promise<void>((resolve) => {
  setTimeout(() => {
    if (!completed) {
      console.log(`Timeout after ${maxTimeout}ms`)
      error = `Timeout after ${maxTimeout}ms`
      completed = true
    }
    resolve()
  }, maxTimeout)
})

// Wait for TASK_COMPLETE detection or timeout.
// The voice routing loop handles multi-turn conversation automatically.
await Promise.race([
  sseMonitor,
  timeoutPromise,
])

// Give a moment for any in-flight audio to finish
await Bun.sleep(2000)

// Clean up
console.log("Closing sessions...")
primarySession.close()
collabSession.close()
primaryEventCtrl.abort()

try {
  await Promise.race([
    Promise.all([primarySession.done, collabSession.done]),
    Bun.sleep(5000), // don't hang on cleanup
  ])
} catch {
  // Cleanup errors are fine
}

// Try to get token usage from session messages
try {
  const msgs = await primaryClient.session.message({ sessionID: primarySession.sessionID })
  if (msgs.data) {
    for (const msg of msgs.data as any[]) {
      const tokens = msg?.info?.tokens
      if (tokens) {
        totalInputTokens += tokens.input ?? 0
        totalOutputTokens += tokens.output ?? 0
      }
    }
  }
} catch (e) {
  console.log("Token counting failed:", (e as any)?.message ?? e)
}

// Write result
const result: TrialResult = {
  completed: completed && !error,
  totalInputTokens,
  totalOutputTokens,
  voiceMessages,
  terminalCommands,
  error,
}

await Bun.write(outputPath, JSON.stringify(result, null, 2))
console.log(`Result written to ${outputPath}`)
console.log(`Completed: ${result.completed}, Commands: ${terminalCommands.length}, Voice messages: ${voiceMessages.length}`)
