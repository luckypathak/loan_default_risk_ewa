import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { api, getUser } from '../api/client'
import { RiskBadge, formatCurrency } from '../components/RiskBadge'

export default function BorrowerDetailPage() {
  const { id } = useParams()
  const user = getUser()
  const [data, setData] = useState(null)
  const [query, setQuery] = useState(`Why was borrower ${id} flagged?`)
  const [queryResult, setQueryResult] = useState(null)
  const [scenario, setScenario] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.borrower(id).then(setData).finally(() => setLoading(false))
  }, [id])

  const runQuery = async () => {
    const res = await api.query(id, query)
    setQueryResult(res)
  }

  const runScenario = async () => {
    const res = await api.scenario(id)
    setScenario(res)
  }

  if (loading) return <p>Loading…</p>
  if (!data) return <p>Not found</p>

  const { borrower, assessment, alert } = data
  const maxScore = Math.max(...(assessment.risk_trend?.map((t) => t.risk_score) || [1]), 1)

  return (
    <>
      <div className="page-header">
        <div>
          <Link to="/" style={{ color: 'var(--muted)', fontSize: '0.85rem' }}>← Dashboard</Link>
          <h2 style={{ marginTop: '0.5rem' }}>{borrower.name} ({borrower.borrower_id})</h2>
        </div>
        <RiskBadge category={assessment.risk_category} />
      </div>

      <div className="cards">
        <div className="card">
          <div className="label">Risk score</div>
          <div className="value">{assessment.risk_score}/100</div>
        </div>
        <div className="card">
          <div className="label">Days past due</div>
          <div className="value">{borrower.current_dpd}d</div>
        </div>
        <div className="card">
          <div className="label">Outstanding</div>
          <div className="value" style={{ fontSize: '1.1rem' }}>{formatCurrency(borrower.loan.outstanding_balance)}</div>
        </div>
        <div className="card">
          <div className="label">EMI</div>
          <div className="value" style={{ fontSize: '1.1rem' }}>{formatCurrency(borrower.loan.emi_amount)}</div>
        </div>
      </div>

      <div className="detail-grid">
        <div className="panel">
          <h3>AI Alert Explanation</h3>
          <p style={{ fontSize: '0.9rem', lineHeight: 1.6 }}>{alert.explanation}</p>
          <p style={{ marginTop: '0.75rem', fontSize: '0.75rem', color: 'var(--muted)' }}>
            Source: {alert.explanation_source}
          </p>
        </div>

        <div className="panel">
          <h3>Recommended actions</h3>
          <ul className="signal-list">
            {assessment.recommended_actions.map((a) => (
              <li key={a}>{a}</li>
            ))}
          </ul>
        </div>
      </div>

      <div className="panel">
        <h3>Risk signals ({assessment.signals.length})</h3>
        <ul className="signal-list">
          {assessment.signals.map((s, i) => (
            <li key={i}>
              <strong>+{s.points}</strong> — {s.label}
              <div style={{ color: 'var(--muted)', fontSize: '0.85rem' }}>{s.detail}</div>
            </li>
          ))}
        </ul>
        {assessment.data_gaps?.length > 0 && (
          <p style={{ marginTop: '1rem', fontSize: '0.85rem', color: 'var(--watch)' }}>
            Data gaps: {assessment.data_gaps.join('; ')}
          </p>
        )}
      </div>

      {assessment.risk_trend?.length > 0 && (
        <div className="panel">
          <h3>Risk trend over time</h3>
          <div className="trend-chart">
            {assessment.risk_trend.map((t) => (
              <div
                key={t.month}
                className="trend-bar"
                style={{
                  height: `${(t.risk_score / maxScore) * 100}%`,
                  background: t.risk_score >= 75 ? 'var(--critical)' : t.risk_score >= 50 ? 'var(--high)' : t.risk_score >= 25 ? 'var(--watch)' : 'var(--low)',
                }}
                title={`${t.month}: ${t.risk_score} (${t.category})`}
              >
                <span>{t.month?.slice(5)}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {user?.role !== 'borrower' && (
        <>
          <div className="panel">
            <h3>Analyst query</h3>
            <div className="form-group">
              <textarea rows={2} value={query} onChange={(e) => setQuery(e.target.value)} />
            </div>
            <button type="button" className="btn btn-sm" onClick={runQuery}>Ask (grounded)</button>
            {queryResult && (
              <div style={{ marginTop: '1rem', padding: '1rem', background: 'var(--bg)', borderRadius: 8 }}>
                <p style={{ fontSize: '0.9rem' }}>{queryResult.answer}</p>
                <p style={{ fontSize: '0.75rem', color: 'var(--muted)', marginTop: '0.5rem' }}>
                  Source: {queryResult.source}
                </p>
              </div>
            )}
          </div>

          <div className="panel">
            <h3>Scenario: What if next EMI is missed?</h3>
            <button type="button" className="btn btn-secondary btn-sm" onClick={runScenario}>
              Run simulation
            </button>
            {scenario && (
              <div style={{ marginTop: '1rem' }}>
                <p>
                  Score: <strong>{scenario.current.risk_score}</strong> → <strong>{scenario.simulated_missed_emi.risk_score}</strong>
                  {' '}(+{scenario.score_delta})
                </p>
                <p>Category: {scenario.category_change}</p>
              </div>
            )}
          </div>
        </>
      )}
    </>
  )
}
