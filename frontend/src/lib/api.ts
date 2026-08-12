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

export interface Message {
  id: number
  author: 'student' | 'bot'
  text: string
  created_at: string
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

export async function startSession(token: string, scenarioId: number): Promise<ConversationSession> {
  const res = await authedFetch('/sessions', token, {
    method: 'POST',
    body: JSON.stringify({ scenario_id: scenarioId }),
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

export { API_BASE_URL }
