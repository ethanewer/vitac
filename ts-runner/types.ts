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
}

export interface VoiceMessageLog {
  sender: "primary" | "collaborator"
  recipient: "primary" | "collaborator"
  transcript: string
  timestampMs: number
}

export interface TrialResult {
  completed: boolean
  totalInputTokens: number
  totalOutputTokens: number
  voiceMessages: VoiceMessageLog[]
  terminalCommands: string[]
  error?: string
}
