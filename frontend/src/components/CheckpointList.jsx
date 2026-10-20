import { RISK_COLORS, formatEta } from '../risk'

export default function CheckpointList({ route }) {
  if (!route) return null
  const cps = route.checkpoints || []

  return (
    <section className="checkpoint-list">
      <h2>
        Checkpoints — {route.label}
        <span className="muted"> ({cps.length})</span>
      </h2>
      <div className="cp-table-wrap">
        <table>
          <thead>
            <tr>
              <th>Mi</th>
              <th>ETA</th>
              <th>Risk</th>
              <th>Wind</th>
              <th>Rain</th>
              <th>Snow</th>
            </tr>
          </thead>
          <tbody>
            {cps.map((cp, i) => (
              <tr key={`${cp.distance_miles}-${i}`}>
                <td>{cp.distance_miles}</td>
                <td>{formatEta(cp.eta)}</td>
                <td>
                  <span
                    className="risk-pill"
                    style={{ background: RISK_COLORS[cp.risk] || '#999' }}
                  >
                    {cp.risk}
                  </span>
                </td>
                <td>{cp.wind_mph} mph</td>
                <td>{cp.rain_in_hr} in/h</td>
                <td>{cp.snow_in_hr} in/h</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}
