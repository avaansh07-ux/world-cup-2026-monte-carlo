from __future__ import annotations

import numpy as np
from flask import Flask, jsonify, request
from flask_cors import CORS

from backend.model_config import SIMULATION_CONFIG
from backend.models.repository import (
    clear_context_cache,
    groups_payload,
    load_context,
    regenerate_squads,
    team_detail,
    team_summary_records,
)
from backend.models.static_data import fc26_dataset_exists, fc26_dataset_path
from backend.simulation.engine import run_tournament_simulation, simulate_match


app = Flask(__name__)
CORS(app)


def _injury_map(payload: dict) -> dict[str, list[str]]:
    injuries = payload.get("injuries", [])
    mapped: dict[str, list[str]] = {}
    for item in injuries:
        mapped.setdefault(item["teamName"], []).append(item["playerName"])
    return mapped


@app.get("/api/health")
def api_health():
    return jsonify({"status": "ok"})


@app.get("/api/groups")
def api_groups():
    return jsonify({"groups": groups_payload()})


@app.get("/api/teams")
def api_teams():
    return jsonify(
        {
            "teams": team_summary_records(),
            "meta": {
                "dataSource": "Built from official groups, provisional squads, FC26 ratings, and tournament path simulations.",
                "format": "48-team official group layout",
                "defaultIterations": SIMULATION_CONFIG.default_iterations,
            },
        }
    )


@app.get("/api/team/<team_ref>")
def api_team(team_ref: str):
    try:
        return jsonify(team_detail(team_ref))
    except KeyError:
        return jsonify({"error": f"Unknown team: {team_ref}"}), 404


@app.post("/api/generate-squads")
def api_generate_squads():
    clear_context_cache()
    result = regenerate_squads()
    return jsonify(
        {
            "status": "ok",
            **result,
            "fc26Available": fc26_dataset_exists(),
            "fc26Path": fc26_dataset_path(),
        }
    )


@app.post("/api/simulate")
def api_simulate():
    payload = request.get_json(silent=True) or {}
    injuries = _injury_map(payload)
    iterations = min(int(payload.get("iterations", SIMULATION_CONFIG.default_iterations)), SIMULATION_CONFIG.max_iterations)
    context = load_context(injuries)
    result = run_tournament_simulation(
        context["teams"],
        context["groups"],
        context["players"],
        iterations,
    )
    return jsonify(result)


@app.post("/api/simulate-match")
def api_simulate_match():
    payload = request.get_json(silent=True) or {}
    team_a = int(payload["teamAId"])
    team_b = int(payload["teamBId"])
    context = load_context(_injury_map(payload))
    teams = context["teams"]
    rng = np.random.default_rng()
    result = simulate_match(
        teams[teams["team_id"] == team_a].iloc[0].to_dict(),
        teams[teams["team_id"] == team_b].iloc[0].to_dict(),
        context["players"],
        rng,
        knockout=bool(payload.get("knockout", False)),
    )
    return jsonify(result)


@app.post("/api/injuries")
def api_injuries():
    payload = request.get_json(silent=True) or {}
    injuries = _injury_map(payload)
    team_id = int(payload.get("teamId"))
    iterations = min(int(payload.get("iterations", 3000)), SIMULATION_CONFIG.max_iterations)
    context = load_context(injuries)
    detail = team_detail(team_id, injuries)
    simulation = run_tournament_simulation(
        context["teams"],
        context["groups"],
        context["players"],
        iterations,
    )
    return jsonify({"teamProfile": detail, "simulation": simulation})


if __name__ == "__main__":
    app.run(debug=True, port=5001)
