import { useMemo, useState } from 'react'
import TripForm from './components/TripForm'
import RouteSummary from './components/RouteSummary'
import CheckpointList from './components/CheckpointList'
import ForecastSlider from './components/ForecastSlider'
import RouteMap from './components/RouteMap'
import { planTrip } from './api'
import './App.css'

export default function App() {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState(null)
  const [selectedId, setSelectedId] = useState(null)
  const [forecastHour, setForecastHour] = useState(0)
  const [showHeatmap, setShowHeatmap] = useState(true)

  const selectedRoute = useMemo(() => {
    if (!result) return null
    return result.routes.find((r) => r.id === selectedId) || result.routes[0]
  }, [result, selectedId])

  async function handlePlan(payload) {
    setLoading(true)
    setError('')
    try {
      const data = await planTrip(payload)
      setResult(data)
      setSelectedId(data.recommendation?.recommended_route_id || data.routes[0]?.id)
      setForecastHour(0)
    } catch (err) {
      setError(err.message || 'Failed to plan trip')
      setResult(null)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="app">
      <header className="topbar">
        <div>
          <p className="eyebrow">Full Stack · Weather-Aware</p>
          <h1>Truck Routing</h1>
        </div>
        <p className="tagline">
          Safest path from weather risk, load weight, and travel time.
        </p>
      </header>

      <div className="layout">
        <aside className="sidebar">
          <TripForm onSubmit={handlePlan} loading={loading} />
          {error && <p className="error">{error}</p>}
          <RouteSummary
            result={result}
            selectedId={selectedId}
            onSelect={setSelectedId}
          />
          <CheckpointList route={selectedRoute} />
        </aside>

        <main className="main">
          <div className="map-toolbar">
            <label className="toggle">
              <input
                type="checkbox"
                checked={showHeatmap}
                onChange={(e) => setShowHeatmap(e.target.checked)}
              />
              Show weather heatmap
            </label>
            {result && (
              <ForecastSlider
                hour={forecastHour}
                onChange={setForecastHour}
                maxHours={result.heatmap?.hours || 48}
              />
            )}
          </div>
          <RouteMap
            result={result}
            selectedId={selectedId}
            forecastHour={forecastHour}
            showHeatmap={showHeatmap}
          />
        </main>
      </div>
    </div>
  )
}
