export const RISK_COLORS = {
  Low: '#2ecc71',
  Moderate: '#f1c40f',
  High: '#e67e22',
  Severe: '#e74c3c',
  'No Travel': '#6c3483',
}

export const RISK_SCORE = {
  Low: 1,
  Moderate: 2,
  High: 3,
  Severe: 4,
  'No Travel': 5,
}

export function formatDuration(seconds) {
  if (!seconds && seconds !== 0) return '—'
  const h = Math.floor(seconds / 3600)
  const m = Math.round((seconds % 3600) / 60)
  if (h <= 0) return `${m} min`
  return `${h} h ${m} min`
}

export function formatEta(iso) {
  if (!iso) return '—'
  try {
    return new Date(iso).toLocaleString(undefined, {
      month: 'short',
      day: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
    })
  } catch {
    return iso
  }
}

/** Classify a heatmap hour sample into a risk color using wind/rain/snow only. */
export function conditionsToRisk(wind, rain, snow) {
  const windR =
    wind < 25 ? 'Low' : wind < 35 ? 'Moderate' : wind < 45 ? 'High' : wind < 55 ? 'Severe' : 'No Travel'
  const rainR =
    rain < 0.1 ? 'Low' : rain <= 0.25 ? 'Moderate' : rain <= 0.5 ? 'High' : rain <= 1 ? 'Severe' : 'No Travel'
  const snowR =
    snow < 0.5 ? 'Low' : snow <= 1 ? 'Moderate' : snow <= 2 ? 'High' : snow <= 3 ? 'Severe' : 'No Travel'
  const levels = [windR, rainR, snowR]
  return levels.reduce((a, b) => (RISK_SCORE[b] > RISK_SCORE[a] ? b : a), 'Low')
}
