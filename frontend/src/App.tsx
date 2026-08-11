import { useEffect, useState } from 'react'
import './App.css'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api'

type HealthStatus = 'checking' | 'ok' | 'error'

function App() {
  const [status, setStatus] = useState<HealthStatus>('checking')

  useEffect(() => {
    fetch(`${API_BASE_URL}/health`)
      .then((res) => (res.ok ? setStatus('ok') : setStatus('error')))
      .catch(() => setStatus('error'))
  }, [])

  return (
    <main style={{ fontFamily: 'sans-serif', padding: '2rem' }}>
      <h1>English Instructor — scaffold</h1>
      <p>
        Backend ({API_BASE_URL}):{' '}
        {status === 'checking' && 'verificando...'}
        {status === 'ok' && '✅ conectado'}
        {status === 'error' && '❌ sem resposta (backend está rodando?)'}
      </p>
    </main>
  )
}

export default App
