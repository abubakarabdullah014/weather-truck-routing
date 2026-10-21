function normalizeApiBase(raw) {
  let base = String(raw || '').trim().replace(/\/+$/, '')
  if (!base) return base
  if (!base.endsWith('/api')) {
    base = `${base}/api`
  }
  return base
}

// IMPORTANT: Vercel builds from Git; gitignored .env is NOT used unless you set
 // Project → Environment Variables. PROD fallback guarantees the live site works.
const API_BASE = normalizeApiBase(
  import.meta.env.VITE_API_BASE_URL ||
    (import.meta.env.PROD
      ? 'https://backend-ten-gilt-82.vercel.app/api'
      : 'http://127.0.0.1:8000/api'),
)

export async function planTrip(payload) {
  let res
  try {
    res = await fetch(`${API_BASE}/plan/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
  } catch (err) {
    throw new Error(
      `Cannot reach API at ${API_BASE}. (${err.message})`,
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
