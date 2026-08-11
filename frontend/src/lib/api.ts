const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api'

export interface Student {
  id: number
  name: string
  current_cefr_level: string
  bot_tone_preference: string
  default_session_minutes: number
  created_at: string
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

export async function syncStudent(token: string, name: string): Promise<Student> {
  const res = await authedFetch('/students/sync', token, {
    method: 'POST',
    body: JSON.stringify({ name }),
  })
  if (!res.ok) throw new Error(`Failed to sync student profile: ${res.status}`)
  return res.json()
}

export async function getCurrentStudent(token: string): Promise<Student> {
  const res = await authedFetch('/students/me', token)
  if (!res.ok) throw new Error(`Failed to fetch student profile: ${res.status}`)
  return res.json()
}

export { API_BASE_URL }
