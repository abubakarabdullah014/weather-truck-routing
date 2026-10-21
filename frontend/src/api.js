function normalizeApiBase(raw) {
  let base = String(raw || '').trim().replace(/\/+$/, '')
  if (!base) return base
  if (!base.endsWith('/api')) {
    base = `${base}/api`
  }
  return base
}

/** Stable production backend — never use old redirected *.vercel.app aliases. */
export const DEFAULT_PROD_API =
  'https://truck-weather-route-backend.vercel.app/api'

export const API_BASE = normalizeApiBase(
  import.meta.env.VITE_API_BASE_URL ||
    (import.meta.env.PROD ? DEFAULT_PROD_API : 'http://127.0.0.1:8000/api'),
)

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

export async function healthCheck() {
  const res = await fetch(`${API_BASE}/health/`, {
    method: 'GET',
    cache: 'no-store',
    headers: { Accept: 'application/json' },
  })
  if (!res.ok) throw new Error(`Health check failed (${res.status})`)
  return res.json()
}

/** One quick ping — never blocks the UI with long retry loops. */
export async function warmApi() {
  try {
    await healthCheck()
    return true
  } catch {
    return false
  }
}

async function fetchWithRetry(url, options, { retries = 1 } = {}) {
  let lastErr
  for (let attempt = 0; attempt <= retries; attempt++) {
    try {
      if (attempt > 0) await sleep(700)
      return await fetch(url, options)
    } catch (err) {
      lastErr = err
    }
  }
  throw new Error(
    `Cannot reach API at ${API_BASE}. (${lastErr?.message || 'Failed to fetch'})`,
  )
}

export async function planTrip(payload) {
  // Light wake (ignore failure — plan request itself wakes the function)
  await warmApi()

  const res = await fetchWithRetry(
    `${API_BASE}/plan/`,
    {
      method: 'POST',
      headers: {
        Accept: 'application/json',
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
      cache: 'no-store',
    },
    { retries: 1 },
  )

  const data = await res.json().catch(() => ({}))
  if (!res.ok) {
    throw new Error(
      data.error || data.detail || `Request failed (${res.status})`,
    )
  }
  return data
}
