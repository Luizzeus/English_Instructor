import { useAuth } from '@clerk/clerk-react'
import { useEffect, useState } from 'react'
import {
  endSession,
  listScenarios,
  sendMessage,
  startSession,
  type ConversationSession,
  type Scenario,
} from './lib/api'

export function Chat() {
  const { getToken } = useAuth()
  const [scenarios, setScenarios] = useState<Scenario[]>([])
  const [session, setSession] = useState<ConversationSession | null>(null)
  const [draft, setDraft] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    getToken().then((token) => {
      if (!token) return
      listScenarios(token).then(setScenarios).catch(() => setError('Não foi possível carregar os cenários.'))
    })
  }, [getToken])

  async function handleStart(scenario: Scenario) {
    setError(null)
    setBusy(true)
    try {
      const token = await getToken()
      if (!token) return
      const newSession = await startSession(token, scenario.id)
      setSession(newSession)
    } catch {
      setError('Não foi possível iniciar a sessão.')
    } finally {
      setBusy(false)
    }
  }

  async function handleSend() {
    if (!session || !draft.trim()) return
    setError(null)
    setBusy(true)
    const text = draft
    setDraft('')
    try {
      const token = await getToken()
      if (!token) return
      const { student_message, bot_message } = await sendMessage(token, session.id, text)
      setSession({ ...session, messages: [...session.messages, student_message, bot_message] })
    } catch {
      setError('Não foi possível enviar a mensagem.')
    } finally {
      setBusy(false)
    }
  }

  async function handleEnd() {
    if (!session) return
    setBusy(true)
    try {
      const token = await getToken()
      if (!token) return
      const ended = await endSession(token, session.id)
      setSession(ended)
    } catch {
      setError('Não foi possível encerrar a sessão.')
    } finally {
      setBusy(false)
    }
  }

  if (!session) {
    return (
      <div>
        <h2>Escolha um cenário</h2>
        {scenarios.length === 0 && <p>carregando cenários...</p>}
        {scenarios.map((scenario) => (
          <div key={scenario.id} style={{ marginBottom: '1rem' }}>
            <strong>{scenario.name}</strong>
            <p>{scenario.description}</p>
            <button type="button" disabled={busy} onClick={() => handleStart(scenario)}>
              Iniciar conversa
            </button>
          </div>
        ))}
        {error && <p>❌ {error}</p>}
      </div>
    )
  }

  const isActive = session.status === 'active'

  return (
    <div>
      <h2>Conversa {isActive ? '' : '(encerrada)'}</h2>
      <div style={{ border: '1px solid #ccc', padding: '1rem', maxWidth: '32rem' }}>
        {session.messages.map((m) => (
          <p key={m.id}>
            <strong>{m.author === 'bot' ? 'Bot' : 'Você'}:</strong> {m.text}
          </p>
        ))}
      </div>

      {isActive && (
        <div style={{ marginTop: '0.5rem', display: 'flex', gap: '0.5rem', maxWidth: '32rem' }}>
          <input
            style={{ flex: 1 }}
            value={draft}
            disabled={busy}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSend()}
            placeholder="Escreva sua resposta em inglês..."
          />
          <button type="button" disabled={busy || !draft.trim()} onClick={handleSend}>
            Enviar
          </button>
          <button type="button" disabled={busy} onClick={handleEnd}>
            Encerrar
          </button>
        </div>
      )}

      {error && <p>❌ {error}</p>}
    </div>
  )
}
