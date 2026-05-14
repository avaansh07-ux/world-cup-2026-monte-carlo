# World Cup 2026 Monte Carlo Simulator

Interactive React + Flask web app for simulating the 2026 FIFA World Cup with a static-data-first pipeline, projected starting XIs, FC26 player ratings, cinematic bracket views, and tournament awards.

## Overview

This project models the full 48-team 2026 World Cup format:

- 12 groups of 4
- top 2 from each group advance automatically
- 8 best third-place teams advance
- Round of 32 through the Final

The simulator is built for fast Monte Carlo runs while still returning a detailed display bracket, scorelines, scorer output, comparison tools, and post-tournament awards.

## Current Features

- Full 48-team tournament simulation
- Team probabilities for:
  - Round of 32
  - Round of 16
  - Quarter-finals
  - Semi-finals
  - Final
  - Champion
- Predicted bracket path with match cards and scorelines
- Team Lineup tab with hardcoded projected XIs from `data/starting_lineups.json`
- Squad Comparison tab with head-to-head odds and lineup/rating comparison
- X-Factors tab with custom player cards, images, and FC26-style stat blocks
- World Cup Awards section after each simulation:
  - Golden Ball
  - Silver Ball
  - Bronze Ball
  - Golden Boot
  - Silver Boot
  - Bronze Boot
  - Golden Glove
  - Best Young Player
  - All-Star Team
- Host nations and host cities presentation
- Group cards with average world ranking

## Data Model

The app is intentionally local-data-driven. No live API is required for the core simulator.

Primary files:

- `data/teams.json`  
  Canonical 48-team dataset with rankings and strength inputs.

- `data/groups.json`  
  Official-style 12-group tournament layout.

- `data/starting_lineups.json`  
  Source of truth for projected starting XIs and manually edited lineup overalls.

- `data/x_factor_ratings.json`  
  Overrides for key player showcase ratings in X-Factors and lineup x-factor sections.

- `data/FC26_20250921.csv`  
  FC26 player dataset used for ratings, attributes, and enrichment.

- `config/player_images.json`  
  Player image mapping support.

## Frontend

Stack:

- React
- Vite
- CSS

Primary experience:

- `Overview`
- `Groups`
- `Team Lineup`
- `Squad Comparison`
- `Predicted Bracket Path`
- `X-Factors`

The UI is intentionally football-first rather than dashboard-first: bold hero treatment, white match panels, dark/gold player cards, and pitch-style lineup rendering.

## Backend

Stack:

- Flask
- pandas
- NumPy
- SciPy

Core responsibilities:

- load and normalize static tournament/team/player data
- compute team and lineup strength values
- run fast Monte Carlo tournament simulations
- generate one representative detailed bracket for UI display
- simulate head-to-head team comparison
- produce awards and top scorer outputs

## Simulation Notes

The backend runs bulk Monte Carlo simulations for probabilities, then generates a single display bracket for the UI.

- Bulk run:
  - tracks advancement counters
  - avoids heavy per-match object construction
  - keeps performance fast for 250 / 1,000 / 5,000 / 10,000 runs

- Display bracket:
  - includes scorelines
  - includes knockout path rendering
  - is selected to be representative of the aggregate probability output

The knockout stage is modeled to be close to the 2026 fixed-path format, including winner/runner-up structure and third-place placement logic. It is not intended to be a random redraw after the group stage.

## API Routes

- `GET /api/health`
- `GET /api/groups`
- `GET /api/teams`
- `GET /api/team/<team_id>`
- `POST /api/generate-squads`
- `POST /api/simulate`
- `POST /api/simulate-match`
- `POST /api/injuries`
- `POST /api/compare-teams`

## Local Development

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

## Project Structure

- `frontend/`  
  React application, tabs, layout, visual styling, and client API calls.

- `backend/app.py`  
  Flask API routes.

- `backend/models/`  
  Data loading, team summaries, team detail payloads, and cached context.

- `backend/simulation/engine.py`  
  Tournament simulation engine, bracket generation, comparison logic, awards logic.

- `backend/model_config.py`  
  Tunable simulation settings and weights.

- `data/`  
  Tournament structure, teams, player data, lineups, and x-factor overrides.

- `config/`  
  Supporting config such as model weights and image mapping.

## Status

This repository is no longer a 16-team prototype. It currently operates as a full 48-team World Cup simulator with custom UI flows and static local data.

## Deployment

Production deployment:

- [world-cup-2026-monte-carlo.vercel.app](https://world-cup-2026-monte-carlo.vercel.app)

## About

Interactive Monte Carlo simulator for the 2026 FIFA World Cup, built with Flask and React.
