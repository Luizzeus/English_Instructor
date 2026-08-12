import { useState } from 'react'
import { login, register, type Student } from './lib/api'

export function AuthForm({ onAuthenticated }: { onAuthenticated: (token: string, student: Student) => void }) {
  const [mode, setMode] = useState<'login' | 'register'>('login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [name, setName] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setBusy(true)
    try {
      const result =
        mode === 'login' ? await login(email, password) : await register(email, password, name)
      onAuthenticated(result.access_token, result.student)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Algo deu errado.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} style={{ maxWidth: '20rem' }}>
      <h2>{mode === 'login' ? 'Entrar' : 'Criar conta'}</h2>

      {mode === 'register' && (
        <div style={{ marginBottom: '0.5rem' }}>
          <input
            type="text"
            placeholder="Nome"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
            style={{ width: '100%' }}
          />
        </div>
      )}

      <div style={{ marginBottom: '0.5rem' }}>
        <input
          type="email"
          placeholder="Email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          style={{ width: '100%' }}
        />
      </div>

      <div style={{ marginBottom: '0.5rem' }}>
        <input
          type="password"
          placeholder="Senha"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          minLength={8}
          style={{ width: '100%' }}
        />
      </div>

      <button type="submit" disabled={busy}>
        {mode === 'login' ? 'Entrar' : 'Criar conta'}
      </button>{' '}
      <button type="button" disabled={busy} onClick={() => setMode(mode === 'login' ? 'register' : 'login')}>
        {mode === 'login' ? 'Criar uma conta' : 'Já tenho conta'}
      </button>

      {error && <p>❌ {error}</p>}
    </form>
  )
}
