export function RiskBadge({ category }) {
  const cls = category?.toLowerCase().replace(' ', '-') || 'low'
  return <span className={`badge badge-${cls}`}>{category}</span>
}

export function formatCurrency(n) {
  return new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(n)
}
