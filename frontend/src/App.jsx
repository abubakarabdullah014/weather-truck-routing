import { useEffect, useMemo, useState } from 'react'
import TripForm from './components/TripForm'
import RouteSummary from './components/RouteSummary'
import CheckpointList from './components/CheckpointList'
import ForecastSlider from './components/ForecastSlider'
import RouteMap from './components/RouteMap'
import { planTrip, warmApi } from './api'
import './App.css'

export default function App() {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState(null)
  const [selectedId, setSelectedId] = useState(null)
  const [forecastHour, setForecastHour] = useState(0)
  const [showHeatmap, setShowHeatmap] = useState(true)
  const [apiStatus, setApiStatus] = useState('connecting') // connecting | ready | offline
  const [everReady, setEverReady] = useState(false)

  // Wake backend on load + keep it warm while the tab is open
  useEffect(() => {
    let cancelled = false

    async function ping() {
      const ok = await warmApi()
      if (cancelled) return
      if (ok) {
        setApiStatus('ready')
        setEverReady(true)
      } else {
        setApiStatus('offline')
      }
    }

    ping()
    const id = setInterval(ping, 4 * 60 * 1000)
    const onVisible = () => {
      if (document.visibilityState === 'visible') ping()
    }
    document.addEventListener('visibilitychange', onVisible)

    return () => {
      cancelled = true
      clearInterval(id)
      document.removeEventListener('visibilitychange', onVisible)
    }
  }, [])

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
      setApiStatus('ready')
      setEverReady(true)
    } catch (err) {
      setError(err.message || 'Failed to plan trip')
      setResult(null)
      setApiStatus('offline')
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
          <p
            className={
              apiStatus === 'ready'
                ? 'api-status api-status--ok'
                : apiStatus === 'offline'
                  ? 'api-status api-status--bad'
                  : 'api-status'
            }
            role="status"
          >
            {apiStatus === 'ready' && 'API connected'}
            {apiStatus === 'connecting' && 'Waking API…'}
            {apiStatus === 'offline' && 'API offline — retry in a moment'}
          </p>
          <TripForm
            onSubmit={handlePlan}
            loading={loading || (apiStatus === 'connecting' && !everReady)}
          />
          {loading && (
            <p className="loading-banner">
              Building up to 3 routes, sampling weather at ETAs, scoring risk…
              First request after idle can take ~30s while the server wakes.
            </p>
          )}
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
