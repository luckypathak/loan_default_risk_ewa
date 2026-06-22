import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import { RiskBadge, formatCurrency } from '../components/RiskBadge'

export default function DashboardPage() {
  const [borrowers, setBorrowers] = useState([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState('all')
  const navigate = useNavigate()

  useEffect(() => {
    api.borrowers().then((d) => setBorrowers(d.borrowers)).finally(() => setLoading(false))
  }, [])

  const filtered =
    filter === 'all' ? borrowers : borrowers.filter((b) => b.risk_category === filter)

  const counts = borrowers.reduce((acc, b) => {
    acc[b.risk_category] = (acc[b.risk_category] || 0) + 1
    return acc
  }, {})

  if (loading) return <p>Loading alerts…</p>

  return (
    <>
      <div className="page-header">
        <div>
          <h2>Risk Dashboard</h2>
          <p style={{ color: 'var(--muted)', marginTop: '0.25rem' }}>
            Borrowers ranked by 30-day delinquency risk
          </p>
        </div>
        <select value={filter} onChange={(e) => setFilter(e.target.value)} className="form-group" style={{ width: 'auto' }}>
          <option value="all">All categories</option>
          <option value="Critical">Critical</option>
          <option value="High Risk">High Risk</option>
          <option value="Watchlist">Watchlist</option>
          <option value="Low">Low</option>
        </select>
      </div>

      <div className="cards">
        {['Critical', 'High Risk', 'Watchlist', 'Low'].map((cat) => (
          <div key={cat} className="card">
            <div className="label">{cat}</div>
            <div className="value">{counts[cat] || 0}</div>
          </div>
        ))}
      </div>

      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>Name</th>
              <th>Score</th>
              <th>Category</th>
              <th>DPD</th>
              <th>EMI</th>
              <th>Outstanding</th>
              <th>Top signal</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((b) => (
              <tr key={b.borrower_id} onClick={() => navigate(`/borrower/${b.borrower_id}`)}>
                <td>{b.borrower_id}</td>
                <td>{b.borrower_name}</td>
                <td><strong>{b.risk_score}</strong></td>
                <td><RiskBadge category={b.risk_category} /></td>
                <td>{b.loan_summary?.current_dpd ?? '—'}d</td>
                <td>{formatCurrency(b.loan_summary?.emi_amount)}</td>
                <td>{formatCurrency(b.loan_summary?.outstanding_balance)}</td>
                <td style={{ color: 'var(--muted)', fontSize: '0.85rem' }}>
                  {b.signals?.[0]?.label || '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  )
}
