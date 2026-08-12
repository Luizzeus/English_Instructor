import { useEffect, useState } from 'react'
import './App.css'
import { AuthForm } from './AuthForm'
import { Chat } from './Chat'
import {
  API_BASE_URL,
  clearStoredToken,
  getCurrentStudent,
  getStoredToken,
  setStoredToken,
  type Student,
} from './lib/api'
import { Metrics } from './Metrics'

type HealthStatus = 'checking' | 'ok' | 'error'

function useBackendHealth(): HealthStatus {
  const [status, setStatus] = useState<HealthStatus>('checking')

  useEffect(() => {
    fetch(`${API_BASE_URL}/health`)
      .then((res) => setStatus(res.ok ? 'ok' : 'error'))
      .catch(() => setStatus('error'))
  }, [])

  return status
}

function App() {
  const backendStatus = useBackendHealth()
  const [token, setToken] = useState<string | null>(() => getStoredToken())
  const [student, setStudent] = useState<Student | null>(null)
  const [authError, setAuthError] = useState<string | null>(null)
  const [metricsRefreshKey, setMetricsRefreshKey] = useState(0)

  useEffect(() => {
    if (!token) {
      setStudent(null)
      return
    }
    getCurrentStudent(token)
      .then(setStudent)
      .catch(() => {
        clearStoredToken()
        setToken(null)
        setAuthError('Sua sessão expirou — entre novamente.')
      })
  }, [token])

  function handleAuthenticated(newToken: string, newStudent: Student) {
    setStoredToken(newToken)
    setToken(newToken)
    setStudent(newStudent)
    setAuthError(null)
  }

  function handleLogout() {
    clearStoredToken()
    setToken(null)
    setStudent(null)
  }

  return (
    <main style={{ fontFamily: 'sans-serif', padding: '2rem' }}>
      <h1>English Instructor — scaffold</h1>

      <p>
        Backend ({API_BASE_URL}):{' '}
        {backendStatus === 'checking' && 'verificando...'}
        {backendStatus === 'ok' && '✅ conectado'}
        {backendStatus === 'error' && '❌ sem resposta (backend está rodando?)'}
      </p>

      {authError && <p>❌ {authError}</p>}

      {!token || !student ? (
        <AuthForm onAuthenticated={handleAuthenticated} />
      ) : (
        <div>
          <p>
            ✅ Logado como {student.name} ({student.email}){' '}
            <button type="button" onClick={handleLogout}>
              Sair
            </button>
          </p>
          <p>Nível CEFR atual: {student.current_cefr_level}</p>
          <Chat token={token} onSessionEnded={() => setMetricsRefreshKey((k) => k + 1)} />
          <h2>Evolução</h2>
          <Metrics token={token} refreshKey={metricsRefreshKey} />
        </div>
      )}
    </main>
  )
}

export default App
