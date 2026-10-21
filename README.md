# Weather-Aware Truck Routing

React + Django app that recommends the safest truck route using live weather, load weight, and travel time.

## Features

- Geocode origin & destination
- Generate **3 distinct route options** (OpenRouteService + OSRM + via-point corridors when needed)
- Sample weather every **10 / 25 / 50 miles** at the truck’s ETA for each checkpoint
- Classify risk (Wind / Rain / Snow) + load-weight overrides
- Recommend the best route: fewest Severe → High → lowest avg risk → shortest time
- Interactive map with route polylines, checkpoint risk markers, and a **0–48h weather heatmap slider**

## Stack

| Layer | Tech |
|-------|------|
| Frontend | React (Vite), Leaflet / react-leaflet |
| Backend | Django + Django REST Framework |
| Routing | [OpenRouteService](https://openrouteservice.org/) (optional OSRM fallback) |
| Geocoding | Nominatim (OpenStreetMap) |
| Weather | [Open-Meteo](https://open-meteo.com/) hourly forecast |

## Quick start

### 1. Backend

```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate
# macOS/Linux
# source venv/bin/activate

pip install -r requirements.txt
copy .env.example .env   # or: cp .env.example .env
# Edit .env — set ORS_API_KEY and DJANGO_SECRET_KEY

python manage.py migrate
python manage.py runserver 8000
```

### 2. Frontend

```bash
cd frontend
copy .env.example .env   # or: cp .env.example .env
npm install
npm run dev
```

Open http://localhost:5173

## Environment variables

### Backend (`backend/.env`)

| Variable | Purpose |
|----------|---------|
| `DJANGO_SECRET_KEY` | Django secret |
| `DJANGO_DEBUG` | `True` / `False` |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated hosts |
| `CORS_ALLOWED_ORIGINS` | Frontend origins |
| `ORS_API_KEY` | OpenRouteService API key |
| `ORS_BASE_URL` | ORS API base URL |
| `OSRM_BASE_URL` | OSRM fallback base URL |
| `NOMINATIM_BASE_URL` | Geocoder base URL |
| `GEOCODER_USER_AGENT` | Required User-Agent for Nominatim |
| `OPEN_METEO_BASE_URL` | Weather API URL |
| `DEFAULT_SAMPLE_INTERVAL_MILES` | Default `25` |

### Frontend (`frontend/.env`)

| Variable | Purpose |
|----------|---------|
| `VITE_API_BASE_URL` | Backend API root (`http://127.0.0.1:8000/api`) |
| `VITE_MAP_TILE_URL` | Leaflet tile template |
| `VITE_MAP_ATTRIBUTION` | Map attribution string |

Get a free ORS key: https://openrouteservice.org/dev/#/signup

## API

`POST /api/plan/`

```json
{
  "origin": "Chicago, IL",
  "destination": "Detroit, MI",
  "departure": "2026-10-21T14:00:00.000Z",
  "load_weight": 35000,
  "sample_interval_miles": 25
}
```

Returns geocoded endpoints, up to 3 routes with checkpoints (weather + risk + ETA), recommendation, and corridor heatmap hourly series.

`GET /api/health/` — liveness check.

## Risk rules

| Condition | Low | Moderate | High | Severe | No Travel |
|-----------|-----|----------|------|--------|-----------|
| Wind | &lt;25 mph | 25–34 | 35–44 | 45–54 | ≥55 |
| Rain | &lt;0.10 in/hr | 0.10–0.25 | 0.25–0.50 | 0.50–1.00 | &gt;1.00 |
| Snow | &lt;0.5 in/hr | 0.5–1.0 | 1.0–2.0 | 2.0–3.0 | &gt;3.0 |

**Load rules**

- ≥55 mph → No Travel (any load)
- 45–54 mph + &gt;30,000 lb → No Travel
- 35–44 mph + &gt;40,000 lb → Severe

## Project layout

```
weather-truck-routing/
  backend/           Django API + risk/routing/weather services
  frontend/          React map UI
  README.md
```

## Deploy frontend on Vercel (+ health keepalive)

Django cannot run on Vercel. Host the **API** on Render/Railway/Fly, and the **React app** on Vercel.

### 1. Deploy the Django API (e.g. Render)

- Root / start: `gunicorn config.wsgi:application`
- Set env from `backend/.env.example` (`ORS_API_KEY`, `DJANGO_SECRET_KEY`, `DJANGO_DEBUG=False`, etc.)
- Add your Vercel URL to `CORS_ALLOWED_ORIGINS` and `DJANGO_ALLOWED_HOSTS`
- Confirm: `GET https://YOUR-API/api/health/` → `{"status":"ok",...}`

### 2. Deploy the frontend on Vercel

1. Import the GitHub repo in [Vercel](https://vercel.com)
2. **Root Directory:** `frontend`
3. Framework: Vite (auto)
4. Environment variables:

| Name | Example |
|------|---------|
| `VITE_API_BASE_URL` | `https://YOUR-API.onrender.com/api` |
| `BACKEND_HEALTH_URL` | `https://YOUR-API.onrender.com/api/health/` |
| `CRON_SECRET` | long random string |

5. Deploy

**Hobby plan:** `vercel.json` uses a **daily** cron (allowed on free):

```json
{ "path": "/api/cron-health", "schedule": "0 12 * * *" }
```

### 3. Every-5-minute keepalive (free) — GitHub Actions

Vercel Hobby cannot run `*/5 * * * *`. Use the included workflow instead:

1. Repo → **Settings → Secrets and variables → Actions**
2. New secret: `BACKEND_HEALTH_URL` = `https://YOUR-API/api/health/`
3. Workflow: `.github/workflows/health-ping.yml` (already set to `*/5 * * * *`)
4. Optionally run it once via **Actions → Health checkpoint → Run workflow**

Manual Vercel check:

```text
GET https://YOUR-APP.vercel.app/api/cron-health
Authorization: Bearer <CRON_SECRET>
```

## Loom walkthrough

Record a 5–10 minute walkthrough covering: inputs → 3 routes → checkpoint weather/risk → recommendation rationale → heatmap slider.
