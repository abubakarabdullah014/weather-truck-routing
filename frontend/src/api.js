function normalizeApiBase(raw) {
  let base = String(raw || '').trim().replace(/\/+$/, '')
  if (!base) return base
  if (!base.endsWith('/api')) {
    base = `${base}/api`
  }
  return base
}

// Production default = stable backend domain (avoid old redirected URLs — fetch fails on 307)
export const API_BASE = normalizeApiBase(
  import.meta.env.VITE_API_BASE_URL ||
    (import.meta.env.PROD
      ? 'https://truck-weather-route-backend.vercel.app/api'
      : 'http://127.0.0.1:8000/api'),
)

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

/** Wake the serverless backend (cold starts often cause the first fetch to fail). */
export async function healthCheck() {
  const res = await fetch(`${API_BASE}/health/`, { cache: 'no-store' })
  if (!res.ok) throw new Error(`Health check failed (${res.status})`)
  return res.json()
}

export async function warmApi() {
  try {
    await healthCheck()
    return true
  } catch {
    return false
  }
}

async function fetchWithRetry(url, options, { retries = 2, label = 'API' } = {}) {
  let lastErr
  for (let attempt = 0; attempt <= retries; attempt++) {
    try {
      if (attempt > 0) {
        // Wake cold Vercel function, then retry
        await warmApi()
        await sleep(800 * attempt)
      }
      return await fetch(url, options)
    } catch (err) {
      lastErr = err
    }
  }
  throw new Error(
    `Cannot reach ${label} at ${API_BASE}. Backend may be waking up — wait 10s and retry. (${lastErr?.message || 'Failed to fetch'})`,
  )
}

export async function planTrip(payload) {
  // Prefetch health so OPTIONS+POST don't hit a cold start together
  await warmApi()

  const res = await fetchWithRetry(
    `${API_BASE}/plan/`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    },
    { retries: 2, label: 'API' },
  )

  const data = await res.json().catch(() => ({}))
  if (!res.ok) {
    throw new Error(data.error || data.detail || `Request failed (${res.status})`)
  }
  return data
}
