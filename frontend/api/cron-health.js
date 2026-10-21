/**
 * Vercel Cron — pings Django /api/health/ to reduce cold starts.
 * Hobby: daily via vercel.json. Prefer GitHub Actions every 5 min.
 *
 * Optional env: BACKEND_HEALTH_URL, VITE_API_BASE_URL, CRON_SECRET
 */
const DEFAULT_HEALTH =
  'https://truck-weather-route-backend.vercel.app/api/health/'

export default async function handler(req, res) {
  if (req.method !== 'GET') {
    res.setHeader('Allow', 'GET')
    return res.status(405).json({ error: 'Method not allowed' })
  }

  const cronSecret = process.env.CRON_SECRET
  if (cronSecret) {
    const auth = req.headers.authorization || ''
    if (auth !== `Bearer ${cronSecret}`) {
      return res.status(401).json({ ok: false, error: 'Unauthorized' })
    }
  }

  const healthUrl =
    process.env.BACKEND_HEALTH_URL ||
    (process.env.VITE_API_BASE_URL
      ? `${process.env.VITE_API_BASE_URL.replace(/\/$/, '')}/health/`
      : DEFAULT_HEALTH)

  const started = Date.now()
  // Retry once — cron itself can hit a cold start
  for (let attempt = 0; attempt < 2; attempt++) {
    try {
      const upstream = await fetch(healthUrl, {
        method: 'GET',
        headers: { Accept: 'application/json' },
        cache: 'no-store',
      })
      const text = await upstream.text()
      let body
      try {
        body = JSON.parse(text)
      } catch {
        body = { raw: text.slice(0, 200) }
      }

      if (!upstream.ok && attempt === 0) continue

      return res.status(upstream.ok ? 200 : 502).json({
        ok: upstream.ok,
        checkpoint: 'cron-health',
        interval: 'daily-vercel-or-5m-github-actions',
        checkedAt: new Date().toISOString(),
        latencyMs: Date.now() - started,
        upstreamStatus: upstream.status,
        upstreamUrl: healthUrl,
        upstream: body,
      })
    } catch (err) {
      if (attempt === 0) continue
      return res.status(502).json({
        ok: false,
        checkpoint: 'cron-health',
        checkedAt: new Date().toISOString(),
        latencyMs: Date.now() - started,
        upstreamUrl: healthUrl,
        error: err.message || String(err),
      })
    }
  }
}
