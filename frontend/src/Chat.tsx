import { useAuth } from '@clerk/clerk-react'
import { useEffect, useRef, useState } from 'react'
import {
  base64AudioToObjectUrl,
  endSession,
  listScenarios,
  sendMessage,
  sendVoiceMessage,
  startSession,
  type ConversationSession,
  type Scenario,
} from './lib/api'
import { WavRecorder } from './lib/wavRecorder'

function PronunciationBadge({ scores }: { scores: NonNullable<ConversationSession['messages'][number]['pronunciation_scores']> }) {
  return (
    <span style={{ fontSize: '0.8em', color: '#555', marginLeft: '0.5rem' }}>
      (pronúncia: {Math.round(scores.pronunciation)}/100 · fluência: {Math.round(scores.fluency)}/100)
    </span>
  )
}

export function Chat({ onSessionEnded }: { onSessionEnded?: () => void }) {
  const { getToken } = useAuth()
  const [scenarios, setScenarios] = useState<Scenario[]>([])
  const [session, setSession] = useState<ConversationSession | null>(null)
  const [draft, setDraft] = useState('')
  const [busy, setBusy] = useState(false)
  const [recording, setRecording] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const recorderRef = useRef<WavRecorder | null>(null)

  useEffect(() => {
    getToken().then((token) => {
      if (!token) return
      listScenarios(token).then(setScenarios).catch(() => setError('Não foi possível carregar os cenários.'))
    })
  }, [getToken])

  async function handleStart(scenario: Scenario, modality: 'text' | 'voice') {
    setError(null)
    setBusy(true)
    try {
      const token = await getToken()
      if (!token) return
      const newSession = await startSession(token, scenario.id, modality)
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

  async function handleStartRecording() {
    setError(null)
    try {
      recorderRef.current = await WavRecorder.start()
      setRecording(true)
    } catch {
      setError('Não foi possível acessar o microfone.')
    }
  }

  async function handleStopRecording() {
    if (!session || !recorderRef.current) return
    setRecording(false)
    setBusy(true)
    try {
      const audioBlob = await recorderRef.current.stop()
      recorderRef.current = null

      const token = await getToken()
      if (!token) return
      const { student_message, bot_message, bot_audio_base64 } = await sendVoiceMessage(
        token,
        session.id,
        audioBlob,
      )
      setSession({ ...session, messages: [...session.messages, student_message, bot_message] })

      const audioUrl = base64AudioToObjectUrl(bot_audio_base64)
      new Audio(audioUrl).play().catch(() => {
        /* autoplay can be blocked by the browser — the student can still read the reply */
      })
    } catch {
      setError('Não foi possível processar o áudio.')
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
      onSessionEnded?.()
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
            <button type="button" disabled={busy} onClick={() => handleStart(scenario, 'text')}>
              Iniciar por texto
            </button>{' '}
            <button type="button" disabled={busy} onClick={() => handleStart(scenario, 'voice')}>
              Iniciar por voz
            </button>
          </div>
        ))}
        {error && <p>❌ {error}</p>}
      </div>
    )
  }

  const isActive = session.status === 'active'
  const isVoice = session.modality === 'voice'

  return (
    <div>
      <h2>Conversa {isActive ? '' : '(encerrada)'}</h2>
      <div style={{ border: '1px solid #ccc', padding: '1rem', maxWidth: '32rem' }}>
        {session.messages.map((m) => (
          <p key={m.id}>
            <strong>{m.author === 'bot' ? 'Bot' : 'Você'}:</strong> {m.text}
            {m.pronunciation_scores && <PronunciationBadge scores={m.pronunciation_scores} />}
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
          {isVoice && !recording && (
            <button type="button" disabled={busy} onClick={handleStartRecording}>
              🎤 Gravar
            </button>
          )}
          {isVoice && recording && (
            <button type="button" onClick={handleStopRecording}>
              ⏹ Parar e enviar
            </button>
          )}
          <button type="button" disabled={busy} onClick={handleEnd}>
            Encerrar
          </button>
        </div>
      )}

      {error && <p>❌ {error}</p>}
    </div>
  )
}
