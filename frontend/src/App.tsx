import { SignedIn, SignedOut, SignInButton, UserButton, useAuth, useUser } from '@clerk/clerk-react'
import { useEffect, useState } from 'react'
import './App.css'
import { API_BASE_URL, syncStudent, type Student } from './lib/api'

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

function StudentProfile() {
  const { getToken } = useAuth()
  const { user } = useUser()
  const [student, setStudent] = useState<Student | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!user) return

    let cancelled = false

    async function loadProfile() {
      const token = await getToken()
      if (!token) return
      try {
        const synced = await syncStudent(token, user!.fullName ?? user!.username ?? 'Student')
        if (!cancelled) setStudent(synced)
      } catch {
        if (!cancelled) setError('Não foi possível sincronizar o perfil com o backend.')
      }
    }

    loadProfile()
    return () => {
      cancelled = true
    }
  }, [user, getToken])

  if (error) return <p>❌ {error}</p>
  if (!student) return <p>sincronizando perfil...</p>

  return (
    <div>
      <p>✅ Perfil sincronizado: {student.name}</p>
      <p>Nível CEFR atual: {student.current_cefr_level}</p>
    </div>
  )
}

function App() {
  const backendStatus = useBackendHealth()

  return (
    <main style={{ fontFamily: 'sans-serif', padding: '2rem' }}>
      <h1>English Instructor — scaffold</h1>

      <p>
        Backend ({API_BASE_URL}):{' '}
        {backendStatus === 'checking' && 'verificando...'}
        {backendStatus === 'ok' && '✅ conectado'}
        {backendStatus === 'error' && '❌ sem resposta (backend está rodando?)'}
      </p>

      <SignedOut>
        <SignInButton mode="modal" />
      </SignedOut>

      <SignedIn>
        <UserButton />
        <StudentProfile />
      </SignedIn>
    </main>
  )
}

export default App
