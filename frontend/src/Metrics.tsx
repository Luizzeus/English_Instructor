import { useEffect, useState } from 'react'
import { listMetrics, type MetricSnapshot } from './lib/api'

const cellStyle = { border: '1px solid #ccc', padding: '0.4rem 0.6rem', textAlign: 'left' as const }

export function Metrics({ token, refreshKey }: { token: string; refreshKey: number }) {
  const [snapshots, setSnapshots] = useState<MetricSnapshot[]>([])
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    listMetrics(token)
      .then(setSnapshots)
      .catch(() => setError('Não foi possível carregar as métricas.'))
  }, [token, refreshKey])

  if (error) return <p>❌ {error}</p>

  if (snapshots.length === 0) {
    return <p>Nenhuma sessão encerrada ainda — as métricas aparecem aqui depois que você terminar uma conversa.</p>
  }

  return (
    <div style={{ overflowX: 'auto', maxWidth: '40rem' }}>
      <table style={{ borderCollapse: 'collapse', width: '100%' }}>
        <thead>
          <tr>
            <th style={cellStyle}>Data</th>
            <th style={cellStyle}>Vocabulário ativo</th>
            <th style={cellStyle}>Erros / 100 palavras</th>
            <th style={cellStyle}>Palavras/min</th>
            <th style={cellStyle}>Complexidade média</th>
            <th style={cellStyle}>Nível CEFR</th>
          </tr>
        </thead>
        <tbody>
          {snapshots.map((s) => (
            <tr key={s.id}>
              <td style={cellStyle}>{new Date(s.recorded_at).toLocaleDateString()}</td>
              <td style={cellStyle}>{s.active_vocabulary_count}</td>
              <td style={cellStyle}>{s.grammar_errors_per_100_words.toFixed(1)}</td>
              <td style={cellStyle}>{s.words_per_minute ? s.words_per_minute.toFixed(0) : '—'}</td>
              <td style={cellStyle}>{s.avg_syntactic_complexity.toFixed(1)}</td>
              <td style={cellStyle}>{s.estimated_cefr_level}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
