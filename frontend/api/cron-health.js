/**
 * Vercel Cron target — pings the Django /api/health/ endpoint.
 * Scheduled every 5 minutes via vercel.json.
 *
 * Env (set in Vercel project settings):
 *   BACKEND_HEALTH_URL  e.g. https://your-api.onrender.com/api/health/
 *   CRON_SECRET         shared secret (Vercel sends Authorization: Bearer <CRON_SECRET>)
 */
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
      : null)

  if (!healthUrl) {
    return res.status(500).json({
      ok: false,
      error: 'BACKEND_HEALTH_URL (or VITE_API_BASE_URL) is not configured',
    })
  }

  const started = Date.now()
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

    return res.status(upstream.ok ? 200 : 502).json({
      ok: upstream.ok,
      checkpoint: 'cron-health',
      interval: '5m',
      checkedAt: new Date().toISOString(),
      latencyMs: Date.now() - started,
      upstreamStatus: upstream.status,
      upstreamUrl: healthUrl,
      upstream: body,
    })
  } catch (err) {
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
