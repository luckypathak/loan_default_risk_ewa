import { useEffect, useState } from 'react'
import { api } from '../api/client'
import { formatCurrency } from '../components/RiskBadge'

export default function PortfolioPage() {
  const [summary, setSummary] = useState(null)

  useEffect(() => {
    api.portfolio().then(setSummary)
  }, [])

  if (!summary) return <p>Loading portfolio…</p>

  return (
    <>
      <div className="page-header">
        <h2>Portfolio Risk Summary</h2>
      </div>

      <div className="cards">
        <div className="card">
          <div className="label">Total borrowers</div>
          <div className="value">{summary.total_borrowers}</div>
        </div>
        <div className="card">
          <div className="label">At-risk (High + Critical)</div>
          <div className="value" style={{ color: 'var(--critical)' }}>{summary.at_risk_count}</div>
        </div>
        <div className="card">
          <div className="label">At-risk %</div>
          <div className="value">{summary.at_risk_pct}%</div>
        </div>
        <div className="card">
          <div className="label">Avg risk score</div>
          <div className="value">{summary.avg_risk_score}</div>
        </div>
        <div className="card">
          <div className="label">Total exposure</div>
          <div className="value" style={{ fontSize: '1.1rem' }}>{formatCurrency(summary.total_outstanding_exposure)}</div>
        </div>
      </div>

      <div className="panel">
        <h3>Distribution by category</h3>
        <div className="cards" style={{ marginTop: '0.5rem' }}>
          {Object.entries(summary.by_risk_category).map(([cat, count]) => (
            <div key={cat} className="card">
              <div className="label">{cat}</div>
              <div className="value">{count}</div>
            </div>
          ))}
        </div>
      </div>
    </>
  )
}
