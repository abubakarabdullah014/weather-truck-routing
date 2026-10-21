import { useEffect, useMemo } from 'react'
import {
  MapContainer,
  TileLayer,
  Polyline,
  CircleMarker,
  Popup,
  useMap,
} from 'react-leaflet'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { RISK_COLORS, conditionsToRisk, formatEta } from '../risk'

const TILE_URL =
  import.meta.env.VITE_MAP_TILE_URL ||
  'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png'
const TILE_ATTR =
  import.meta.env.VITE_MAP_ATTRIBUTION || '© OpenStreetMap contributors'

const ROUTE_COLORS = ['#1a73e8', '#0f9d58', '#db4437']

function FitBounds({ route }) {
  const map = useMap()
  useEffect(() => {
    const pts = route?.coordinates || []
    if (pts.length < 2) return
    map.fitBounds(L.latLngBounds(pts), { padding: [40, 40] })
  }, [map, route])
  return null
}

function heatmapSampleAtHour(point, hourOffset, departureIso) {
  const hourly = point.hourly || []
  if (!hourly.length) return null
  const target = new Date(departureIso).getTime() + hourOffset * 3600 * 1000
  let best = hourly[0]
  let bestDiff = Infinity
  for (const h of hourly) {
    const raw = h.time.endsWith('Z') || h.time.includes('+') ? h.time : `${h.time}Z`
    const t = new Date(raw).getTime()
    if (Number.isNaN(t)) continue
    const diff = Math.abs(t - target)
    if (diff < bestDiff) {
      bestDiff = diff
      best = h
    }
  }
  return best
}

/** Visual strength 0–1 so calm hours still show slider movement. */
function weatherStrength(wind, rain, snow) {
  return Math.min(
    1,
    Math.max(wind / 40, rain / 0.35, snow / 1.5, 0.08),
  )
}

function haversineKm(lat1, lon1, lat2, lon2) {
  const r = 6371
  const p1 = (lat1 * Math.PI) / 180
  const p2 = (lat2 * Math.PI) / 180
  const dp = ((lat2 - lat1) * Math.PI) / 180
  const dl = ((lon2 - lon1) * Math.PI) / 180
  const a =
    Math.sin(dp / 2) ** 2 +
    Math.cos(p1) * Math.cos(p2) * Math.sin(dl / 2) ** 2
  return 2 * r * Math.asin(Math.sqrt(a))
}

/** Keep heatmap dots only along the selected route corridor. */
function nearSelectedRoute(lat, lon, coordinates, maxKm = 12) {
  if (!coordinates?.length) return false
  const step = Math.max(1, Math.floor(coordinates.length / 120))
  for (let i = 0; i < coordinates.length; i += step) {
    const [clat, clon] = coordinates[i]
    if (haversineKm(lat, lon, clat, clon) <= maxKm) return true
  }
  const [elat, elon] = coordinates[coordinates.length - 1]
  return haversineKm(lat, lon, elat, elon) <= maxKm
}

export default function RouteMap({
  result,
  selectedId,
  forecastHour,
  showHeatmap,
}) {
  const routes = result?.routes || []
  const selectedRoute = useMemo(
    () => routes.find((r) => r.id === selectedId) || routes[0] || null,
    [routes, selectedId],
  )
  const selectedIdx = selectedRoute
    ? Math.max(0, routes.findIndex((r) => r.id === selectedRoute.id))
    : 0
  const loadLb = result?.load_weight_lb || 0
  const center = useMemo(() => {
    if (result?.origin) return [result.origin.lat, result.origin.lon]
    return [39.5, -98.35]
  }, [result])

  const heatmapLayers = useMemo(() => {
    if (!showHeatmap || !result?.heatmap?.points || !selectedRoute) return []
    const coords = selectedRoute.coordinates || []
    return result.heatmap.points
      .filter((p) => nearSelectedRoute(p.lat, p.lon, coords))
      .map((p) => {
        const sample = heatmapSampleAtHour(p, forecastHour, result.departure)
        if (!sample) return null
        const risk = conditionsToRisk(
          sample.wind_mph,
          sample.rain_in_hr,
          sample.snow_in_hr,
          loadLb,
        )
        const strength = weatherStrength(
          sample.wind_mph,
          sample.rain_in_hr,
          sample.snow_in_hr,
        )
        return { lat: p.lat, lon: p.lon, risk, sample, strength }
      })
      .filter(Boolean)
  }, [result, forecastHour, showHeatmap, loadLb, selectedRoute])

  const heatmapStats = useMemo(() => {
    if (!heatmapLayers.length) return null
    const avgWind =
      heatmapLayers.reduce((s, p) => s + (p.sample.wind_mph || 0), 0) /
      heatmapLayers.length
    const risks = {}
    for (const p of heatmapLayers) {
      risks[p.risk] = (risks[p.risk] || 0) + 1
    }
    return { avgWind, risks, count: heatmapLayers.length }
  }, [heatmapLayers])

  return (
    <div className="map-wrap">
      <MapContainer center={center} zoom={6} scrollWheelZoom className="map">
        <TileLayer attribution={TILE_ATTR} url={TILE_URL} />
        <FitBounds route={selectedRoute} />

        {/* Heatmap under selected route — remount on hour so Leaflet redraws */}
        {heatmapLayers.map((p, i) => (
          <CircleMarker
            key={`hm-${forecastHour}-${i}-${p.risk}-${Math.round(p.strength * 100)}`}
            center={[p.lat, p.lon]}
            radius={10 + p.strength * 14}
            pathOptions={{
              color: RISK_COLORS[p.risk],
              fillColor: RISK_COLORS[p.risk],
              fillOpacity: 0.25 + p.strength * 0.45,
              weight: 1,
              opacity: 0.7,
            }}
          >
            <Popup>
              Corridor weather @ <strong>+{forecastHour}h</strong>
              <br />
              Risk: {p.risk}
              <br />
              Wind {p.sample.wind_mph} mph · Rain {p.sample.rain_in_hr} · Snow{' '}
              {p.sample.snow_in_hr}
            </Popup>
          </CircleMarker>
        ))}

        {/* Only the selected route line + checkpoint circles */}
        {selectedRoute && (
          <Polyline
            key={`route-${selectedRoute.id}`}
            positions={selectedRoute.coordinates}
            pathOptions={{
              color: ROUTE_COLORS[selectedIdx % ROUTE_COLORS.length],
              weight: 7,
              opacity: 0.95,
            }}
          />
        )}

        {selectedRoute &&
          (selectedRoute.checkpoints || []).map((cp, i) => (
            <CircleMarker
              key={`cp-${selectedRoute.id}-${i}`}
              center={[cp.lat, cp.lon]}
              radius={7}
              pathOptions={{
                color: '#111',
                weight: 1,
                fillColor: RISK_COLORS[cp.risk] || '#888',
                fillOpacity: 0.95,
              }}
            >
              <Popup>
                <strong>
                  {selectedRoute.label} · {cp.distance_miles} mi — {cp.risk}
                </strong>
                <br />
                ETA {formatEta(cp.eta)}
                <br />
                Wind {cp.wind_mph} mph
                <br />
                Rain {cp.rain_in_hr} in/h · Snow {cp.snow_in_hr} in/h
              </Popup>
            </CircleMarker>
          ))}

        {result?.origin && (
          <CircleMarker
            center={[result.origin.lat, result.origin.lon]}
            radius={9}
            pathOptions={{
              color: '#111',
              fillColor: '#fff',
              fillOpacity: 1,
              weight: 2,
            }}
          >
            <Popup>Origin: {result.origin.display_name}</Popup>
          </CircleMarker>
        )}
        {result?.destination && (
          <CircleMarker
            center={[result.destination.lat, result.destination.lon]}
            radius={9}
            pathOptions={{
              color: '#111',
              fillColor: '#222',
              fillOpacity: 1,
              weight: 2,
            }}
          >
            <Popup>Destination: {result.destination.display_name}</Popup>
          </CircleMarker>
        )}
      </MapContainer>

      <div className="map-legend">
        {Object.entries(RISK_COLORS).map(([name, color]) => (
          <span key={name}>
            <i style={{ background: color }} /> {name}
          </span>
        ))}
      </div>

      {showHeatmap && heatmapStats && (
        <div className="heatmap-hud">
          Forecast <strong>+{forecastHour}h</strong>
          {' · '}
          avg wind <strong>{heatmapStats.avgWind.toFixed(1)} mph</strong>
          {' · '}
          {heatmapStats.count} corridor points
        </div>
      )}
    </div>
  )
}
