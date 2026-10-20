export default function ForecastSlider({ hour, onChange, maxHours = 48 }) {
  return (
    <div className="forecast-slider">
      <div className="slider-head">
        <span>Weather heatmap forecast</span>
        <strong>
          +{hour}h <span className="muted">/ {maxHours}h</span>
        </strong>
      </div>
      <input
        type="range"
        min={0}
        max={maxHours}
        step={1}
        value={hour}
        onChange={(e) => onChange(Number(e.target.value))}
      />
      <div className="slider-labels">
        <span>Now</span>
        <span>+24h</span>
        <span>+48h</span>
      </div>
    </div>
  )
}
