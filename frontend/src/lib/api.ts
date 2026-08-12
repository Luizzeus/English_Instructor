const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api'

export interface Student {
  id: number
  name: string
  current_cefr_level: string
  bot_tone_preference: string
  default_session_minutes: number
  created_at: string
}

export interface Scenario {
  id: number
  name: string
  description: string
  bot_persona: string
  target_cefr_level: string
  tags: string[]
}

export interface PronunciationScores {
  accuracy: number
  fluency: number
  completeness: number
  pronunciation: number
}

export interface Message {
  id: number
  author: 'student' | 'bot'
  text: string
  created_at: string
  pronunciation_scores: PronunciationScores | null
}

export interface ConversationSession {
  id: number
  scenario_id: number
  modality: 'text' | 'voice'
  status: 'active' | 'completed' | 'abandoned'
  started_at: string
  ended_at: string | null
  messages: Message[]
}

async function authedFetch(path: string, token: string, init?: RequestInit): Promise<Response> {
  return fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      ...init?.headers,
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
  })
}

async function parseOrThrow<T>(res: Response, action: string): Promise<T> {
  if (!res.ok) throw new Error(`${action}: ${res.status}`)
  return res.json()
}

export async function syncStudent(token: string, name: string): Promise<Student> {
  const res = await authedFetch('/students/sync', token, {
    method: 'POST',
    body: JSON.stringify({ name }),
  })
  return parseOrThrow(res, 'Failed to sync student profile')
}

export async function getCurrentStudent(token: string): Promise<Student> {
  const res = await authedFetch('/students/me', token)
  return parseOrThrow(res, 'Failed to fetch student profile')
}

export async function listScenarios(token: string): Promise<Scenario[]> {
  const res = await authedFetch('/scenarios', token)
  return parseOrThrow(res, 'Failed to list scenarios')
}

export async function startSession(
  token: string,
  scenarioId: number,
  modality: 'text' | 'voice' = 'text',
): Promise<ConversationSession> {
  const res = await authedFetch('/sessions', token, {
    method: 'POST',
    body: JSON.stringify({ scenario_id: scenarioId, modality }),
  })
  return parseOrThrow(res, 'Failed to start session')
}

export async function sendMessage(
  token: string,
  sessionId: number,
  text: string,
): Promise<{ student_message: Message; bot_message: Message }> {
  const res = await authedFetch(`/sessions/${sessionId}/messages`, token, {
    method: 'POST',
    body: JSON.stringify({ text }),
  })
  return parseOrThrow(res, 'Failed to send message')
}

export async function endSession(token: string, sessionId: number): Promise<ConversationSession> {
  const res = await authedFetch(`/sessions/${sessionId}/end`, token, { method: 'POST' })
  return parseOrThrow(res, 'Failed to end session')
}

export interface SendVoiceMessageResult {
  student_message: Message
  bot_message: Message
  bot_audio_base64: string
}

export async function sendVoiceMessage(
  token: string,
  sessionId: number,
  audioBlob: Blob,
): Promise<SendVoiceMessageResult> {
  const formData = new FormData()
  formData.append('audio', audioBlob, 'recording.wav')

  // Deliberately not using authedFetch here: it forces Content-Type: application/json,
  // but multipart bodies need the browser to set Content-Type itself (with the boundary).
  const res = await fetch(`${API_BASE_URL}/sessions/${sessionId}/voice-messages`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}` },
    body: formData,
  })
  return parseOrThrow(res, 'Failed to send voice message')
}

export function base64AudioToObjectUrl(base64: string, mimeType = 'audio/wav'): string {
  const bytes = Uint8Array.from(atob(base64), (c) => c.charCodeAt(0))
  return URL.createObjectURL(new Blob([bytes], { type: mimeType }))
}

export { API_BASE_URL }
