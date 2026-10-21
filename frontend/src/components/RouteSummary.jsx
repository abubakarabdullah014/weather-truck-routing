import { formatDuration } from '../risk'
import { RISK_COLORS } from '../risk'

export default function RouteSummary({ result, selectedId, onSelect }) {
  if (!result) return null
  const { routes, recommendation } = result
  const recommendedId = recommendation?.recommended_route_id

  return (
    <section className="route-summary">
      <h2>Routes</h2>
      {recommendation && (
        <div className="recommend-banner">
          <strong>Recommended: Route {recommendedId}</strong>
          <p className="rank-note">
            Ranked by: fewest Severe miles → fewest High miles → lowest avg risk →
            shortest time
          </p>
          <ul>
            {recommendation.reasons.map((r) => (
              <li key={r}>{r}</li>
            ))}
          </ul>
          {routes.length < 3 && (
            <p className="rank-note">
              Showing {routes.length} distinct corridor option
              {routes.length === 1 ? '' : 's'} for this OD pair.
            </p>
          )}
        </div>
      )}

      <div className="route-cards">
        {routes.map((route) => {
          const s = route.summary || {}
          const active = route.id === selectedId
          const isBest = route.id === recommendedId
          return (
            <button
              key={route.id}
              type="button"
              className={`route-card ${active ? 'active' : ''} ${isBest ? 'best' : ''}`}
              onClick={() => onSelect(route.id)}
            >
              <header>
                <span>{route.label}</span>
                {isBest && <span className="badge">Best</span>}
              </header>
              <p>
                {route.distance_miles} mi · {formatDuration(route.duration_s)}
              </p>
              <div className="risk-bars">
                <RiskChip label="Severe" miles={s.severe_miles} color={RISK_COLORS.Severe} />
                <RiskChip label="High" miles={s.high_miles} color={RISK_COLORS.High} />
                <RiskChip label="Mod" miles={s.moderate_miles} color={RISK_COLORS.Moderate} />
                <RiskChip label="Low" miles={s.low_miles} color={RISK_COLORS.Low} />
              </div>
              <p className="avg">
                Avg risk {s.avg_risk} · Max {s.max_risk}
                {s.has_no_travel ? ' · No Travel segments' : ''}
              </p>
            </button>
          )
        })}
      </div>
    </section>
  )
}

function RiskChip({ label, miles, color }) {
  return (
    <span className="risk-chip" style={{ borderColor: color }}>
      <i style={{ background: color }} />
      {label} {Number(miles || 0).toFixed(0)} mi
    </span>
  )
}
