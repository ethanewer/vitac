export interface TrialConfig {
  primaryUrl: string
  collabUrl: string
  /** Built-in voice system name (e.g. "claude-opus-medium-voice"). */
  system: string
  /** Built-in voice system name for the collaborator. Defaults to system. */
  collabSystem?: string
  /** Path to a pre-generated WAV file used as the seed message. */
  seedAudioPath: string
  /** Which agent receives the seed audio: "primary" or "collaborator". */
  startAgent: "primary" | "collaborator"
  maxTimeoutMs?: number
  /** Additional system prompt appended to the primary agent's prompt. */
  primaryPrompt?: string
  /** Additional system prompt for the collaborator agent (e.g. domain knowledge). */
  collabPrompt?: string
  /** Original text instruction for the task (helps correct STT errors). */
  taskInstruction?: string
}

export interface VoiceMessageLog {
  sender: "primary" | "collaborator"
  recipient: "primary" | "collaborator"
  transcript: string
  timestampMs: number
}

/** A text segment emitted by the SDK's transcript queue. */
export interface TextSegment {
  speaker: "primary" | "collaborator"
  text: string
  timestampMs: number
}

export interface TrialResult {
  completed: boolean
  totalInputTokens: number
  totalOutputTokens: number
  voiceMessages: VoiceMessageLog[]
  /** Raw text transcript segments from both agents (ordered by time). */
  textSegments: TextSegment[]
  terminalCommands: string[]
  error?: string
}
