# Assessment checklist (grader map)

This document maps the assignment requirements to the implementation.

## Inputs (UI)

| Input | Where |
|-------|--------|
| Origin & destination | `frontend/src/components/TripForm.jsx` → `POST /api/plan/` |
| Departure date/time | `datetime-local` → ISO-8601 with timezone |
| Load weight (lb) | Sent as `load_weight`; used in risk + heatmap |

## Routes, weather, risk & recommendation (40%)

| Requirement | Implementation |
|-------------|----------------|
| Up to **3 route options** via routing API | `backend/routes/services/routing.py` — OpenRouteService (HGV) alternatives, OSRM alternatives, then **via-point corridor detours** to fill distinct options to 3 |
| Sample every **10 / 25 / 50** miles | Trip form radios + `_sample_along_route` |
| Weather at **ETA** per checkpoint | `eta_offset_s` × departure → Open-Meteo hourly bucket (`weather_at_eta`) |
| Wind / Rain / Snow thresholds | `backend/routes/services/risk.py` (+ unit tests) |
| Load rules (≥55; 45–54+>30k; 35–44+>40k) | `apply_load_rules` in `risk.py` (+ unit tests) |
| Recommend: Severe → High → avg risk → time | `backend/routes/services/recommendation.py` (+ unit tests) |

## UI, map & heatmap (40%)

| Requirement | Implementation |
|-------------|----------------|
| All routes on map | `RouteMap.jsx` polylines (color-coded) |
| Checkpoints, risk, ETAs | Markers for **all** routes (selected emphasized); popups; sidebar table |
| Route summaries | `RouteSummary.jsx` — miles by risk band, avg/max, Best badge |
| Corridor heatmap + **0–48h** slider | `build_corridor_heatmap` + `ForecastSlider`; colors use **same risk + load rules** |

## Code quality (15%)

- Env-driven secrets/URLs (`.env.example`, no secrets in git)
- Separated services: geocode / routing / weather / risk / recommendation / pipeline
- Django REST + React (Vite) + Leaflet
- Unit tests: `python manage.py test routes`

## Docs & walkthrough (5%)

- `README.md` — setup, env vars, API, deploy
- This file — requirement mapping
- Loom: demo inputs → 3 routes → checkpoints/risk → recommendation reasons → heatmap slider

## Demo tip for max score

Use a mid-length US OD pair (e.g. Chicago → Detroit or Dallas → Houston), load **35,000 lb**, sample **25 mi**, departure within the next few hours so the forecast window is populated.
