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

function classifyWind(mph) {
  if (mph < 25) return 'Low'
  if (mph < 35) return 'Moderate'
  if (mph < 45) return 'High'
  if (mph < 55) return 'Severe'
  return 'No Travel'
}

function classifyRain(inHr) {
  if (inHr < 0.1) return 'Low'
  if (inHr <= 0.25) return 'Moderate'
  if (inHr <= 0.5) return 'High'
  if (inHr <= 1) return 'Severe'
  return 'No Travel'
}

function classifySnow(inHr) {
  if (inHr < 0.5) return 'Low'
  if (inHr <= 1) return 'Moderate'
  if (inHr <= 2) return 'High'
  if (inHr <= 3) return 'Severe'
  return 'No Travel'
}

function applyLoadRules(windMph, loadLb, base) {
  if (windMph >= 55) return 'No Travel'
  if (windMph >= 45 && windMph < 55 && loadLb > 30000) return 'No Travel'
  if (windMph >= 35 && windMph < 45 && loadLb > 40000) {
    return RISK_SCORE[base] < RISK_SCORE.Severe ? 'Severe' : base
  }
  return base
}

/**
 * Classify weather (+ optional load) into risk — same rules as backend.
 */
export function conditionsToRisk(wind, rain, snow, loadLb = 0) {
  const windR = classifyWind(wind)
  const rainR = classifyRain(rain)
  const snowR = classifySnow(snow)
  const combined = [windR, rainR, snowR].reduce(
    (a, b) => (RISK_SCORE[b] > RISK_SCORE[a] ? b : a),
    'Low',
  )
  return applyLoadRules(wind, Number(loadLb) || 0, combined)
}
