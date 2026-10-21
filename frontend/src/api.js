const API_BASE = (
  import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api'
).replace(/\/$/, '')

function assertApiConfigured() {
  const onVercel =
    typeof window !== 'undefined' &&
    window.location.hostname.includes('vercel.app')
  const pointsLocal =
    API_BASE.includes('127.0.0.1') || API_BASE.includes('localhost')
  if (onVercel && pointsLocal) {
    throw new Error(
      'Frontend is still calling localhost. In Vercel → weather-truck (FE) → Settings → Environment Variables, set VITE_API_BASE_URL=https://YOUR-BACKEND.vercel.app/api then Redeploy.',
    )
  }
}

export async function planTrip(payload) {
  assertApiConfigured()
  const res = await fetch(`${API_BASE}/plan/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  const data = await res.json().catch(() => ({}))
  if (!res.ok) {
    throw new Error(data.error || `Request failed (${res.status})`)
  }
  return data
}

export async function healthCheck() {
  const res = await fetch(`${API_BASE}/health/`)
  return res.json()
}
