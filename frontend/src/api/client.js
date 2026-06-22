const API = '/api'

export function getToken() {
  return localStorage.getItem('ewa_token')
}

export function getUser() {
  const u = localStorage.getItem('ewa_user')
  return u ? JSON.parse(u) : null
}

export function logout() {
  localStorage.removeItem('ewa_token')
  localStorage.removeItem('ewa_user')
}

async function request(path, options = {}) {
  const token = getToken()
  const res = await fetch(`${API}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  })
  if (res.status === 401) {
    logout()
    window.location.href = '/login'
    throw new Error('Unauthorized')
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || res.statusText)
  }
  return res.json()
}

export const api = {
  login: (username, password) =>
    request('/auth/login', { method: 'POST', body: JSON.stringify({ username, password }) }),
  borrowers: () => request('/borrowers'),
  borrower: (id) => request(`/borrowers/${id}`),
  query: (id, question) =>
    request(`/borrowers/${id}/query`, { method: 'POST', body: JSON.stringify({ question }) }),
  scenario: (id) => request(`/borrowers/${id}/scenario/missed-emi`),
  portfolio: () => request('/portfolio/summary'),
  thresholds: () => request('/risk/thresholds'),
}
