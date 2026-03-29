export interface TrialConfig {
  primaryUrl: string
  collabUrl: string
  instruction: string
  collaboratorContext: string
  model: { providerID: string; modelID: string }
  collabModel?: { providerID: string; modelID: string }
  nativeAudioInput?: boolean
  nativeAudioOutput?: boolean
  voice?: string
  sttOptions?: { model?: string; apiKey?: string; baseUrl?: string }
  ttsOptions?: { model?: string; apiKey?: string; baseUrl?: string; voice?: string }
  maxTimeoutMs?: number
  reasoningEffort?: string
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
