import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api/client'

export default function LoginPage() {
  const [username, setUsername] = useState('analyst1')
  const [password, setPassword] = useState('analyst1')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const data = await api.login(username, password)
      localStorage.setItem('ewa_token', data.token)
      localStorage.setItem('ewa_user', JSON.stringify(data.user))
      navigate('/')
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="login-page">
      <div className="login-card">
        <h1>Loan Default Risk EWA</h1>
        <p>Early warning system for proactive collections</p>
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label>Username</label>
            <input value={username} onChange={(e) => setUsername(e.target.value)} required />
          </div>
          <div className="form-group">
            <label>Password</label>
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
          </div>
          {error && <p className="error">{error}</p>}
          <button type="submit" className="btn" style={{ width: '100%' }} disabled={loading}>
            {loading ? 'Signing in…' : 'Sign in'}
          </button>
        </form>
        <div className="demo-accounts">
          <p><strong>Demo accounts</strong></p>
          <p>Analyst: <code>analyst1</code> / <code>analyst1</code></p>
          <p>Manager: <code>manager1</code> / <code>manager1</code></p>
          <p>Borrower: <code>B101</code> / <code>borrower</code></p>
        </div>
      </div>
    </div>
  )
}
