#!/usr/bin/env bun
/**
 * Voice trial runner: creates voice sessions on primary + collaborator OpenCode
 * servers using built-in voice system presets, seeds the conversation with a
 * pre-generated audio instruction, routes audio between agents, detects
 * completion, and writes result JSON.
 *
 * No custom system prompts are injected — both agents use their built-in
 * system prompts from the voice system preset.  The only input is the seed
 * audio pushed to one agent's input queue.
 *
 * Usage: bun run ts-runner/run-trial.ts <config.json> <output.json>
 */

import { createOpencodeClient } from "@opencode-ai/sdk/v2/client"
import { createVoiceSession, pcmToWav, stt } from "@opencode-ai/sdk/v2/voice"
import type { VoiceSystemName } from "@opencode-ai/sdk/v2/voice"
import type { TrialConfig, TrialResult, VoiceMessageLog } from "./types.js"

const configPath = Bun.argv[2]
const outputPath = Bun.argv[3]

if (!configPath || !outputPath) {
  console.error("Usage: bun run run-trial.ts <config.json> <output.json>")
  process.exit(1)
}

const config: TrialConfig = JSON.parse(await Bun.file(configPath).text())

const maxTimeout = config.maxTimeoutMs ?? 540_000
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

const systemName = config.system as VoiceSystemName
const collabSystemName = (config.collabSystem ?? config.system) as VoiceSystemName

console.log("Creating voice sessions...")
console.log(`System: ${systemName}`)
console.log(`Collaborator system: ${collabSystemName}`)

// Minimal additive prompt for the primary — only adds the completion signal
// convention.  Everything else comes from the agent's built-in system prompt.
const primaryPrompt = `When the task is fully done and you have verified the result, include the exact phrase "TASK_COMPLETE" in your response.`

// Create voice sessions — agents keep their built-in system prompts intact
const primarySession = await createVoiceSession(primaryClient, {
  system: systemName,
  prompt: primaryPrompt,
  permission: "dangerous",
  toolStatus: false,
})

// Collaborator: no custom prompt, built-in agent prompt only
const collabSession = await createVoiceSession(collabClient, {
  system: collabSystemName,
  permission: [{ permission: "*", pattern: "*", action: "deny" as const }],
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
      transcript = await stt(wav)
    } catch {
      transcript = "[audio]"
    }
    voiceMessages.push({ sender, recipient, transcript, timestampMs: Date.now() })
    console.log(`${sender} -> ${recipient}: ${transcript.slice(0, 200)}`)
  }

  // Use a timer to flush accumulated audio after a silence gap
  let flushTimer: ReturnType<typeof setTimeout> | null = null
  const SILENCE_GAP_MS = 1500

  for await (const pcm of source) {
    if (completed) break
    chunks.push(pcm)
    totalLen += pcm.length

    if (flushTimer) clearTimeout(flushTimer)

    if (totalLen >= MIN_BYTES_TO_SEND) {
      await flushToDestination()
    } else {
      flushTimer = setTimeout(() => {
        flushToDestination().catch(() => {})
      }, SILENCE_GAP_MS)
    }
  }

  if (flushTimer) clearTimeout(flushTimer)
  await flushToDestination()
}

// Route audio between sessions
const primaryToCollab = routeAudio(primarySession.output, collabSession.input, "primary")
const collabToPrimary = routeAudio(collabSession.output, primarySession.input, "collaborator")

// Load pre-generated seed audio and push it to the starting agent
console.log(`Loading seed audio from ${config.seedAudioPath} ...`)
const seedWav = new Uint8Array(await Bun.file(config.seedAudioPath).arrayBuffer())
console.log(`Seed audio: ${(seedWav.length / 1024).toFixed(0)} KB, start agent: ${config.startAgent}`)

const startInput = config.startAgent === "primary" ? primarySession.input : collabSession.input
startInput.push(seedWav)

// Log the seed as a voice message
const seedRecipient = config.startAgent
const seedSender = config.startAgent === "primary" ? "collaborator" : "primary"
let seedTranscript = ""
try {
  seedTranscript = await stt(seedWav)
} catch {
  seedTranscript = "[seed audio]"
}
voiceMessages.push({
  sender: seedSender,
  recipient: seedRecipient,
  transcript: seedTranscript,
  timestampMs: Date.now(),
})
console.log(`seed -> ${seedRecipient}: ${seedTranscript.slice(0, 200)}`)

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
    Bun.sleep(5000),
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
