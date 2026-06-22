import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { getUser, logout } from '../api/client'

export default function Layout() {
  const user = getUser()
  const navigate = useNavigate()

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <h1>Loan Risk<br />Early Warning</h1>
        <nav>
          <NavLink to="/" end>Dashboard</NavLink>
          {(user?.role === 'manager' || user?.role === 'analyst') && (
            <NavLink to="/portfolio">Portfolio</NavLink>
          )}
        </nav>
        <div className="user-pill">
          <div>{user?.name}</div>
          <div className="role">{user?.role}</div>
        </div>
        <button type="button" className="nav-link" onClick={handleLogout}>
          Sign out
        </button>
      </aside>
      <main className="main">
        <Outlet />
      </main>
    </div>
  )
}
