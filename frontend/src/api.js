function normalizeApiBase(raw) {
  let base = (raw || 'http://127.0.0.1:8000/api').trim().replace(/\/+$/, '')
  // Accept either "...vercel.app" or "...vercel.app/api"
  if (!base.endsWith('/api')) {
    base = `${base}/api`
  }
  return base
}

const API_BASE = normalizeApiBase(import.meta.env.VITE_API_BASE_URL)

function assertApiConfigured() {
  const onVercel =
    typeof window !== 'undefined' &&
    window.location.hostname.includes('vercel.app')
  const pointsLocal =
    API_BASE.includes('127.0.0.1') || API_BASE.includes('localhost')
  if (onVercel && pointsLocal) {
    throw new Error(
      'Frontend is still calling localhost. In Vercel → Frontend → Env, set VITE_API_BASE_URL=https://backend-ten-gilt-82.vercel.app/api then Redeploy.',
    )
  }
}

export async function planTrip(payload) {
  assertApiConfigured()
  let res
  try {
    res = await fetch(`${API_BASE}/plan/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
  } catch (err) {
    throw new Error(
      `Cannot reach API at ${API_BASE}. Is the backend running? (${err.message})`,
    )
  }
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
