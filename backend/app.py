from __future__ import annotations

from copy import deepcopy

from flask import Flask, jsonify, request
from flask_cors import CORS

from services.data_pipeline import apply_injury, get_team, load_teams
from simulation.tournament import simulate_tournament


app = Flask(__name__)
CORS(app)


@app.get("/health")
def healthcheck():
    return jsonify({"status": "ok"})


@app.get("/teams")
def teams():
    return jsonify({"teams": load_teams()})


@app.get("/team-stats/<int:team_id>")
def team_stats(team_id: int):
    return jsonify({"team": get_team(team_id)})


@app.post("/injury")
def injury():
    payload = request.get_json(silent=True) or {}
    team_id = payload.get("teamId")
    player_name = payload.get("playerName")
    if not team_id or not player_name:
        return jsonify({"error": "teamId and playerName are required"}), 400

    team = get_team(int(team_id))
    adjusted = apply_injury(team, player_name)
    return jsonify({"team": adjusted})


@app.post("/simulate")
def simulate():
    payload = request.get_json(silent=True) or {}
    iterations = int(payload.get("iterations", 10000))
    selected_team_id = payload.get("selectedTeamId")
    injuries = payload.get("injuries", [])

    teams = [deepcopy(team) for team in load_teams()]

    if selected_team_id:
        featured_team = next(
            (team for team in teams if int(team["id"]) == int(selected_team_id)),
            None,
        )
        if featured_team and featured_team["form"] < 1.2:
            featured_team["form"] = round(featured_team["form"] + 0.03, 3)

    for injury_event in injuries:
        for index, team in enumerate(teams):
            if int(team["id"]) == int(injury_event["teamId"]):
                teams[index] = apply_injury(team, injury_event["playerName"])

    return jsonify(simulate_tournament(teams, iterations))


if __name__ == "__main__":
    app.run(debug=True, port=5001)
