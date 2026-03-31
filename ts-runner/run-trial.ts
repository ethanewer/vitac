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

import { mkdir } from "node:fs/promises"
import { createOpencodeClient } from "@opencode-ai/sdk/v2/client"
import { createVoiceSession, pcmToWav, stt } from "@opencode-ai/sdk/v2/voice"
import type { VoiceSystemName } from "@opencode-ai/sdk/v2/voice"
import type { TrialConfig, TrialResult, TextSegment, VoiceMessageLog } from "./types.js"

const configPath = Bun.argv[2]
const outputPath = Bun.argv[3]

if (!configPath || !outputPath) {
  console.error("Usage: bun run run-trial.ts <config.json> <output.json>")
  process.exit(1)
}

const config: TrialConfig = JSON.parse(await Bun.file(configPath).text())

// Create directory for saving audio WAV files alongside the result JSON
const audioDir = outputPath.replace(/\.json$/, "_audio")
await mkdir(audioDir, { recursive: true })
let audioCounter = 0

const maxTimeout = config.maxTimeoutMs ?? 540_000
const voiceMessages: VoiceMessageLog[] = []
const textSegments: TextSegment[] = []
const terminalCommands: string[] = []
let totalInputTokens = 0
let totalOutputTokens = 0
let completedToolCalls = 0 // Track all completed tool calls (bash, read, write, edit, etc.)

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

const batchTurns = config.batchTurns ?? false

console.log("Creating voice sessions...")
console.log(`System: ${systemName}`)
console.log(`Collaborator system: ${collabSystemName}`)
console.log(`Batch turns: ${batchTurns}`)

// Primary prompt: guides the agent to use tools and collaborate via voice
const primaryPrompt = [
  `You are on a voice call with a collaborator who has domain knowledge about the task.`,
  `Listen to what they say and use your tools (bash, edit, write, etc.) to complete the task.`,
  `When you need information from the collaborator, ask them directly by speaking.`,
  `Focus on executing commands and making progress — do not just think out loud.`,
  `When the task is fully done and you have verified the result, include the exact phrase "TASK_COMPLETE" in your response.`,
  config.taskInstruction
    ? `\nThe following is the exact text of the task instruction (use this for precise file paths and details that may be garbled in voice):\n${config.taskInstruction}`
    : "",
  config.primaryPrompt ?? "",
].filter(Boolean).join("\n")

// Collaborator prompt: provides domain knowledge so it can answer questions
const collabPrompt = config.collabPrompt
  ? [
      `You are a collaborator on a voice call with an engineer who is completing a task.`,
      `You have the following domain knowledge that the engineer needs:\n${config.collabPrompt}`,
      `When the engineer asks you questions, answer them directly and concisely using this knowledge.`,
      `You do NOT have access to tools — your role is purely advisory.`,
    ].join("\n")
  : undefined

// Create voice sessions — agents keep their built-in system prompts intact
const primarySession = await createVoiceSession(primaryClient, {
  system: systemName,
  prompt: primaryPrompt,
  permission: "dangerous",
  toolStatus: false,
  batchTurns,
  // Disable the interactive question tool — in voice mode the agent should
  // ask questions by speaking, not through an interactive prompt.
  tools: { question: false },
})

// Collaborator: domain knowledge prompt + all tools denied (advisory role only)
const collabSession = await createVoiceSession(collabClient, {
  system: collabSystemName,
  prompt: collabPrompt,
  permission: [{ permission: "*", pattern: "*", action: "deny" as const }],
  toolStatus: false,
  batchTurns,
})

console.log(`Primary session: ${primarySession.sessionID}`)
console.log(`Collaborator session: ${collabSession.sessionID}`)

// Track completion
let completed = false
let error: string | undefined

// Collect text transcripts from both sessions' transcript queues
async function collectTranscripts(
  transcriptQueue: typeof primarySession.transcript,
  speaker: "primary" | "collaborator",
) {
  for await (const text of transcriptQueue) {
    if (completed) break
    textSegments.push({ speaker, text, timestampMs: Date.now() })
    console.log(`[transcript] ${speaker}: ${text.slice(0, 200)}`)
  }
}

const primaryTranscriptLoop = collectTranscripts(primarySession.transcript, "primary")
const collabTranscriptLoop = collectTranscripts(collabSession.transcript, "collaborator")

// Monitor primary SSE events for completion detection and terminal commands
const primaryEventCtrl = new AbortController()
const primaryEvents = await primaryClient.event.subscribe({}, { signal: primaryEventCtrl.signal })

// Also monitor collaborator events for debugging
const collabEventCtrl = new AbortController()
const collabEvents = await collabClient.event.subscribe({}, { signal: collabEventCtrl.signal })

const collabEventMonitor = (async () => {
  try {
    for await (const event of collabEvents.stream) {
      if (completed) break
      const evt = event as any
      // Log all collaborator events for debugging
      if (evt.properties?.sessionID === collabSession.sessionID) {
        if (evt.type === "session.status") {
          console.log(`[collab-event] ${evt.type}: ${evt.properties.status?.type}`)
          if (evt.properties.status?.type === "idle") signalIdle("collaborator")
        } else if (evt.type === "message.part.delta" && evt.properties.field === "text") {
          // don't log every delta, too noisy
        } else {
          console.log(`[collab-event] ${evt.type}`)
        }
      }
    }
  } catch {
    // Stream ended or aborted
  }
})()

const sseMonitor = (async () => {
  let textBuffer = ""
  try {
    for await (const event of primaryEvents.stream) {
      if (completed) break
      const evt = event as any

      // Log all primary session events for debugging
      if (evt.properties?.sessionID === primarySession.sessionID) {
        if (evt.type === "session.status") {
          console.log(`[primary-event] ${evt.type}: ${evt.properties.status?.type}`)
        } else if (evt.type === "session.error") {
          console.log(`[primary-event] ${evt.type}: ${JSON.stringify(evt.properties)}`)
        } else if (evt.type === "message.part.delta" && evt.properties.field === "text") {
          // don't log every text delta, too noisy
        } else if (evt.type === "message.part.delta") {
          console.log(`[primary-event] ${evt.type} field=${evt.properties.field}`)
        } else {
          console.log(`[primary-event] ${evt.type}`)
        }
      }

      // Track text output for completion detection
      if (evt.type === "message.part.delta" && evt.properties.sessionID === primarySession.sessionID) {
        if (evt.properties.field === "text") {
          textBuffer += evt.properties.delta
          if (textBuffer.includes("TASK_COMPLETE") && completedToolCalls > 0) {
            console.log("Detected TASK_COMPLETE (after " + completedToolCalls + " tool calls, " + terminalCommands.length + " bash commands)")
            completed = true
            break
          }
        }
      }

      // Track terminal commands and all tool completions
      if (evt.type === "message.part.updated" && evt.properties.sessionID === primarySession.sessionID) {
        const part = evt.properties.part
        if (part?.type === "tool") {
          console.log(`[primary-tool] ${part.tool} status=${part.state?.status}`)
          if (part?.state?.status === "completed") {
            completedToolCalls++
            if (part?.tool === "bash") {
              const input = part.state?.input?.command
              if (input) terminalCommands.push(input)
            }
          }
        }
      }

      // Reset text buffer on idle (new turn) and signal turn boundary
      if (evt.type === "session.status" && evt.properties.sessionID === primarySession.sessionID) {
        if (evt.properties.status?.type === "idle") {
          textBuffer = ""
          signalIdle("primary")
        }
      }
    }
  } catch {
    // Stream ended or aborted
  }
})()

// Turn-boundary signaling for batchTurns mode.
// SSE monitors set these flags when the source agent goes idle.
let primaryIdleFired = false
let collabIdleFired = false

function signalIdle(agent: "primary" | "collaborator") {
  if (agent === "primary") primaryIdleFired = true
  else collabIdleFired = true
}

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

    // Save audio to disk
    const idx = String(audioCounter++).padStart(3, "0")
    const audioFilename = `${idx}_${sender}_to_${recipient}.wav`
    await Bun.write(`${audioDir}/${audioFilename}`, wav)

    // Also transcribe for logging
    let transcript = ""
    try {
      transcript = await stt(wav)
    } catch {
      transcript = "[audio]"
    }
    voiceMessages.push({ sender, recipient, transcript, timestampMs: Date.now(), audioFilename })
    console.log(`${sender} -> ${recipient}: ${transcript.slice(0, 200)}`)
  }

  if (batchTurns) {
    // Turn-boundary mode: accumulate all PCM and flush once the TTS stream
    // for a turn finishes.  The idle event fires when the LLM turn ends,
    // but the SDK's batched TTS hasn't finished streaming yet (it starts on
    // idle).  So we wait for idle AND a silence gap: once idle has fired and
    // no new PCM arrives for 2 seconds, we know TTS is done.
    let flushTimer: ReturnType<typeof setTimeout> | null = null
    const POST_IDLE_FLUSH_MS = 2000

    for await (const pcm of source) {
      if (completed) break
      chunks.push(pcm)
      totalLen += pcm.length

      // Clear any pending flush timer — new audio arrived
      if (flushTimer) clearTimeout(flushTimer)

      // Check if idle has been signaled for this sender
      const idle = sender === "primary" ? primaryIdleFired : collabIdleFired
      if (idle && totalLen > 0) {
        // Idle already fired; TTS is streaming. Set a timer to flush once
        // chunks stop arriving (TTS stream finished).
        flushTimer = setTimeout(() => {
          // Reset the idle flag for the next turn
          if (sender === "primary") primaryIdleFired = false
          else collabIdleFired = false
          flushToDestination().catch(() => {})
        }, POST_IDLE_FLUSH_MS)
      }
    }

    if (flushTimer) clearTimeout(flushTimer)
    await flushToDestination()
  } else {
    // Streaming mode (original): flush on silence gap or size threshold.
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
const seedAudioFilename = `${String(audioCounter++).padStart(3, "0")}_seed_to_${seedRecipient}.wav`
await Bun.write(`${audioDir}/${seedAudioFilename}`, seedWav)

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
  audioFilename: seedAudioFilename,
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
collabEventCtrl.abort()

try {
  await Promise.race([
    Promise.all([primarySession.done, collabSession.done]),
    Bun.sleep(5000),
  ])
} catch {
  // Cleanup errors are fine
}

// Try to get token usage and dump session messages for debugging
try {
  const msgs = await primaryClient.session.message({ sessionID: primarySession.sessionID })
  if (msgs.data) {
    console.log(`\n=== Primary session messages (${(msgs.data as any[]).length}) ===`)
    for (const msg of msgs.data as any[]) {
      const role = msg?.role ?? "unknown"
      const parts = msg?.parts ?? []
      const partSummary = parts.map((p: any) => {
        if (p.type === "text") return `text(${(p.text ?? "").slice(0, 100)}...)`
        if (p.type === "tool") return `tool(${p.tool}:${p.state?.status ?? "?"})`
        if (p.type === "file") return `file(${p.mime})`
        return p.type
      }).join(", ")
      console.log(`  [${role}] ${partSummary}`)
      const tokens = msg?.info?.tokens
      if (tokens) {
        totalInputTokens += tokens.input ?? 0
        totalOutputTokens += tokens.output ?? 0
      }
    }
    console.log(`=== End messages ===\n`)
  }
} catch (e) {
  console.log("Token counting failed:", (e as any)?.message ?? e)
}

// Also dump collaborator session messages
try {
  const msgs = await collabClient.session.message({ sessionID: collabSession.sessionID })
  if (msgs.data) {
    console.log(`\n=== Collaborator session messages (${(msgs.data as any[]).length}) ===`)
    for (const msg of msgs.data as any[]) {
      const role = msg?.role ?? "unknown"
      const parts = msg?.parts ?? []
      const partSummary = parts.map((p: any) => {
        if (p.type === "text") return `text(${(p.text ?? "").slice(0, 100)}...)`
        if (p.type === "tool") return `tool(${p.tool}:${p.state?.status ?? "?"})`
        if (p.type === "file") return `file(${p.mime})`
        return p.type
      }).join(", ")
      console.log(`  [${role}] ${partSummary}`)
    }
    console.log(`=== End messages ===\n`)
  }
} catch (e) {
  console.log("Collaborator message dump failed:", (e as any)?.message ?? e)
}

// Write result
const result: TrialResult = {
  completed: completed && !error,
  totalInputTokens,
  totalOutputTokens,
  voiceMessages,
  textSegments,
  terminalCommands,
  error,
}

await Bun.write(outputPath, JSON.stringify(result, null, 2))
console.log(`Result written to ${outputPath}`)
console.log(`Completed: ${result.completed}, Commands: ${terminalCommands.length}, Voice messages: ${voiceMessages.length}`)
