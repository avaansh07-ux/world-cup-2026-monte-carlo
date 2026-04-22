# World Cup 2026 Monte Carlo Simulation Web App

Starter full-stack project for simulating the FIFA World Cup 2026 with a Flask backend and React frontend.

## Stack

- Backend: Flask, NumPy, pandas, SciPy
- Frontend: React + Vite
- Deployment: Frontend prepared for Vercel, backend kept separate

## Project Structure

- `backend/` Flask API, data pipeline, caching, and simulation logic
- `frontend/` React client for running simulations and exploring outcomes

## Quick Start

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## Environment Variables

Create `backend/.env` from `backend/.env.example`.

- `API_FOOTBALL_KEY`: API-Sports key
- `API_FOOTBALL_BASE_URL`: defaults to `https://v3.football.api-sports.io`
- `CACHE_TTL_HOURS`: cache freshness window
- `TEAM_DATA_SOURCE`: `sample` or `live`

## Notes

- The backend never exposes the API key to the frontend.
- The starter app ships with curated sample team/player data so the UI works immediately before live API integration is enabled.
- Cache files are stored under `backend/data/cache/`.
