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

/**
 * Keep pinging until the serverless function is awake.
 * Cold starts + flaky DNS are the usual "Failed to fetch" causes.
 */
export async function ensureWarm({ attempts = 6, delayMs = 1500 } = {}) {
  let lastErr
  for (let i = 0; i < attempts; i++) {
    try {
      await healthCheck()
      return true
    } catch (err) {
      lastErr = err
      await sleep(delayMs * (i + 1))
    }
  }
  throw lastErr || new Error('API warmup failed')
}

export async function warmApi() {
  try {
    await ensureWarm({ attempts: 4, delayMs: 1200 })
    return true
  } catch {
    return false
  }
}

async function fetchWithRetry(url, options, { retries = 3 } = {}) {
  let lastErr
  for (let attempt = 0; attempt <= retries; attempt++) {
    try {
      if (attempt > 0) {
        await ensureWarm({ attempts: 3, delayMs: 1000 }).catch(() => {})
        await sleep(1000 * attempt)
      }
      const res = await fetch(url, options)
      return res
    } catch (err) {
      lastErr = err
    }
  }
  throw new Error(
    `Cannot reach API at ${API_BASE}. Check your internet, wait a few seconds, then try again. (${lastErr?.message || 'Failed to fetch'})`,
  )
}

export async function planTrip(payload) {
  // Always wake first so CORS preflight + POST don't share one cold start
  await ensureWarm({ attempts: 5, delayMs: 1200 })

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
    { retries: 3 },
  )

  const data = await res.json().catch(() => ({}))
  if (!res.ok) {
    throw new Error(
      data.error || data.detail || `Request failed (${res.status})`,
    )
  }
  return data
}
