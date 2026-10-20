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

function FitBounds({ routes }) {
  const map = useMap()
  useEffect(() => {
    const pts = []
    for (const r of routes || []) {
      for (const c of r.coordinates || []) pts.push(c)
    }
    if (pts.length < 2) return
    map.fitBounds(L.latLngBounds(pts), { padding: [40, 40] })
  }, [map, routes])
  return null
}

function heatmapSampleAtHour(point, hourOffset, departureIso) {
  const hourly = point.hourly || []
  if (!hourly.length) return null
  const target = new Date(departureIso).getTime() + hourOffset * 3600 * 1000
  let best = hourly[0]
  let bestDiff = Infinity
  for (const h of hourly) {
    const t = new Date(h.time + (h.time.endsWith('Z') ? '' : 'Z')).getTime()
    const diff = Math.abs(t - target)
    if (diff < bestDiff) {
      bestDiff = diff
      best = h
    }
  }
  return best
}

export default function RouteMap({
  result,
  selectedId,
  forecastHour,
  showHeatmap,
}) {
  const routes = result?.routes || []
  const center = useMemo(() => {
    if (result?.origin) return [result.origin.lat, result.origin.lon]
    return [39.5, -98.35]
  }, [result])

  const heatmapLayers = useMemo(() => {
    if (!showHeatmap || !result?.heatmap?.points) return []
    return result.heatmap.points
      .map((p) => {
        const sample = heatmapSampleAtHour(p, forecastHour, result.departure)
        if (!sample) return null
        const risk = conditionsToRisk(
          sample.wind_mph,
          sample.rain_in_hr,
          sample.snow_in_hr,
        )
        return { lat: p.lat, lon: p.lon, risk, sample }
      })
      .filter(Boolean)
  }, [result, forecastHour, showHeatmap])

  return (
    <div className="map-wrap">
      <MapContainer
        center={center}
        zoom={6}
        scrollWheelZoom
        className="map"
      >
        <TileLayer attribution={TILE_ATTR} url={TILE_URL} />
        <FitBounds routes={routes} />

        {heatmapLayers.map((p, i) => (
          <CircleMarker
            key={`hm-${i}`}
            center={[p.lat, p.lon]}
            radius={14}
            pathOptions={{
              color: RISK_COLORS[p.risk],
              fillColor: RISK_COLORS[p.risk],
              fillOpacity: 0.35,
              weight: 0,
            }}
          >
            <Popup>
              Heatmap @ +{forecastHour}h
              <br />
              Risk: {p.risk}
              <br />
              Wind {p.sample.wind_mph} mph · Rain {p.sample.rain_in_hr} · Snow{' '}
              {p.sample.snow_in_hr}
            </Popup>
          </CircleMarker>
        ))}

        {routes.map((route, idx) => {
          const isSelected = route.id === selectedId
          const isBest = route.recommended
          return (
            <Polyline
              key={`route-${route.id}`}
              positions={route.coordinates}
              pathOptions={{
                color: ROUTE_COLORS[idx % ROUTE_COLORS.length],
                weight: isSelected ? 7 : 4,
                opacity: isSelected ? 0.95 : 0.45,
                dashArray: isBest && !isSelected ? '8 10' : undefined,
              }}
            />
          )
        })}

        {routes
          .filter((r) => r.id === selectedId)
          .flatMap((route) =>
            (route.checkpoints || []).map((cp, i) => (
              <CircleMarker
                key={`cp-${route.id}-${i}`}
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
                    {cp.distance_miles} mi — {cp.risk}
                  </strong>
                  <br />
                  ETA {formatEta(cp.eta)}
                  <br />
                  Wind {cp.wind_mph} mph
                  <br />
                  Rain {cp.rain_in_hr} in/h · Snow {cp.snow_in_hr} in/h
                </Popup>
              </CircleMarker>
            )),
          )}

        {result?.origin && (
          <CircleMarker
            center={[result.origin.lat, result.origin.lon]}
            radius={9}
            pathOptions={{ color: '#111', fillColor: '#fff', fillOpacity: 1, weight: 2 }}
          >
            <Popup>Origin: {result.origin.display_name}</Popup>
          </CircleMarker>
        )}
        {result?.destination && (
          <CircleMarker
            center={[result.destination.lat, result.destination.lon]}
            radius={9}
            pathOptions={{ color: '#111', fillColor: '#222', fillOpacity: 1, weight: 2 }}
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
    </div>
  )
}
