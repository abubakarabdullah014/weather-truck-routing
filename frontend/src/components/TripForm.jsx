import { useState } from 'react'

function defaultDepartureLocal() {
  const d = new Date()
  d.setMinutes(d.getMinutes() - d.getTimezoneOffset())
  return d.toISOString().slice(0, 16)
}

export default function TripForm({ onSubmit, loading }) {
  const [origin, setOrigin] = useState('Chicago, IL')
  const [destination, setDestination] = useState('Detroit, MI')
  const [departure, setDeparture] = useState(defaultDepartureLocal)
  const [loadWeight, setLoadWeight] = useState(35000)
  const [interval, setIntervalMiles] = useState(25)

  function handleSubmit(e) {
    e.preventDefault()
    // datetime-local is local time — convert to ISO with offset
    const local = new Date(departure)
    onSubmit({
      origin,
      destination,
      departure: local.toISOString(),
      load_weight: Number(loadWeight),
      sample_interval_miles: Number(interval),
    })
  }

  return (
    <form className="trip-form" onSubmit={handleSubmit}>
      <h2>Trip details</h2>

      <label>
        Origin
        <input
          value={origin}
          onChange={(e) => setOrigin(e.target.value)}
          placeholder="City, address, or lat,lon"
          required
        />
      </label>

      <label>
        Destination
        <input
          value={destination}
          onChange={(e) => setDestination(e.target.value)}
          placeholder="City, address, or lat,lon"
          required
        />
      </label>

      <label>
        Departure
        <input
          type="datetime-local"
          value={departure}
          onChange={(e) => setDeparture(e.target.value)}
          required
        />
      </label>

      <label>
        Load weight (lb)
        <input
          type="number"
          min="0"
          step="100"
          value={loadWeight}
          onChange={(e) => setLoadWeight(e.target.value)}
          required
        />
      </label>

      <fieldset className="interval-field">
        <legend>Weather sample interval</legend>
        {[10, 25, 50].map((mi) => (
          <label key={mi} className="radio">
            <input
              type="radio"
              name="interval"
              value={mi}
              checked={Number(interval) === mi}
              onChange={() => setIntervalMiles(mi)}
            />
            Every {mi} mi
          </label>
        ))}
      </fieldset>

      <button type="submit" disabled={loading}>
        {loading ? 'Planning routes…' : 'Find safest routes'}
      </button>
    </form>
  )
}
