# World Cup 2026 Monte Carlo Simulation Web App

Interactive football simulation project built with a React frontend and Flask backend. This version is intentionally static-data-first: no API keys, no live feeds, just a configurable tournament engine powered by rankings, squad ratings, and form signals.

## What It Does

- Simulates a simplified 16-team World Cup thousands of times
- Calculates probabilities for each team reaching the quarter-finals, semi-finals, final, and winning the tournament
- Generates Poisson-based scorelines for matches
- Estimates goal scorers from player ratings, production, minutes, and position
- Lets you remove players in the Injury Lab and immediately recalculate outcomes

## Stack

- Frontend: React + Vite
- Backend: Flask
- Modeling: pandas, NumPy, SciPy
- Data: local CSV files in [`data/`](/Users/avaanshnanda/Desktop/World%20Cup%202026/data)

## Project Layout

- [`frontend/`](/Users/avaanshnanda/Desktop/World%20Cup%202026/frontend) immersive simulation UI
- [`backend/app.py`](/Users/avaanshnanda/Desktop/World%20Cup%202026/backend/app.py:1) Flask API routes
- [`backend/models/`](/Users/avaanshnanda/Desktop/World%20Cup%202026/backend/models) static data loading and team strength calculation
- [`backend/simulation/engine.py`](/Users/avaanshnanda/Desktop/World%20Cup%202026/backend/simulation/engine.py:1) match and tournament simulator
- [`backend/model_config.py`](/Users/avaanshnanda/Desktop/World%20Cup%202026/backend/model_config.py:1) simulation weights and tunable parameters
- [`data/teams.csv`](/Users/avaanshnanda/Desktop/World%20Cup%202026/data/teams.csv:1) teams and base rankings
- [`data/players.csv`](/Users/avaanshnanda/Desktop/World%20Cup%202026/data/players.csv:1) squad-level player dataset
- [`data/world_cup_structure.csv`](/Users/avaanshnanda/Desktop/World%20Cup%202026/data/world_cup_structure.csv:1) group-stage structure for v1

## Current Tournament Format

Version 1 uses a simplified 16-team format to prove out the simulation engine quickly:

- 4 groups of 4
- Top 2 advance from each group
- Quarter-finals, semi-finals, final

The project brief is set up to expand this into the full 2026 format later.

## Team Strength Model

The backend computes separate attack and defense values from weighted components:

- FIFA/world ranking baseline: 25%
- Squad quality: 35%
- Attacking production: 15%
- Defensive quality: 15%
- Recent form: 10%

These starter weights live in [`backend/model_config.py`](/Users/avaanshnanda/Desktop/World%20Cup%202026/backend/model_config.py:1) so we can tune them without changing frontend code.

## API Routes

- `GET /api/health`
- `GET /api/teams`
- `GET /api/team/<team_id>`
- `POST /api/simulate`
- `POST /api/simulate-match`
- `POST /api/injuries`

## Quick Start

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r ../requirements.txt
cd ..
backend/.venv/bin/python app.py
```

Backend runs on `http://127.0.0.1:5001`.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend runs on `http://127.0.0.1:5173`.

## Verified

The current codebase has been smoke-tested for:

- frontend production build with `npm run build`
- Flask route registration
- `GET /api/health`
- `GET /api/teams`
- `GET /api/team/1`
- `POST /api/simulate`
- `POST /api/simulate-match`
- `POST /api/injuries`

## Next Steps

- Expand from 16 teams to the full 2026 World Cup format
- Improve bracket rendering with round-specific visuals
- Add richer top-scorer logic and per-player tournament stats
- Add more realistic tie-breaking and knockout variance
- Optionally layer in refreshed live data later without changing the frontend contract
