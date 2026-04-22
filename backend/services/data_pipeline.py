from __future__ import annotations

from copy import deepcopy
from statistics import mean
from typing import Any

from config import settings
from data.sample_teams import SAMPLE_TEAMS
from services.api_football import APIFootballClient
from services.cache import cache_is_fresh, read_json, write_json


client = APIFootballClient()


def _sample_catalog() -> list[dict[str, Any]]:
    return deepcopy(SAMPLE_TEAMS)


def _normalize_team(team: dict[str, Any]) -> dict[str, Any]:
    players = team.get("players", [])
    average_rating = mean(player["rating"] for player in players) if players else team["rating"]
    return {
        **team,
        "strength_index": round(team["attack"] * team["form"] * (average_rating / 85), 3),
        "average_player_rating": round(average_rating, 2),
    }


def load_teams() -> list[dict[str, Any]]:
    if settings.team_data_source != "live":
        return [_normalize_team(team) for team in _sample_catalog()]

    cache_path = settings.cache_dir / "teams.live.json"
    if cache_is_fresh(cache_path, settings.cache_ttl_hours):
        return read_json(cache_path)

    leagues = [39, 140, 78, 61]
    teams: list[dict[str, Any]] = []

    for league in leagues:
        response = client.get("/teams", {"league": league, "season": 2023})
        for item in response.get("response", []):
            team_data = item.get("team", {})
            teams.append(
                {
                    "id": team_data["id"],
                    "name": team_data["name"],
                    "group": "TBD",
                    "confederation": "TBD",
                    "attack": 1.0,
                    "defense": 1.0,
                    "form": 1.0,
                    "rating": 80.0,
                    "players": [],
                }
            )

    payload = [_normalize_team(team) for team in teams]
    write_json(cache_path, payload)
    return payload


def get_team(team_id: int) -> dict[str, Any]:
    for team in load_teams():
        if int(team["id"]) == int(team_id):
            return team
    raise KeyError(f"Unknown team id: {team_id}")


def apply_injury(team: dict[str, Any], player_name: str) -> dict[str, Any]:
    injured = deepcopy(team)
    injured["players"] = [
        player for player in injured.get("players", []) if player["name"] != player_name
    ]

    if injured["players"]:
        injured["rating"] = round(
            mean(player["rating"] for player in injured["players"]), 2
        )
    else:
        injured["rating"] = max(team["rating"] - 3, 70)

    injured["attack"] = round(max(team["attack"] - 0.05, 0.8), 3)
    injured["form"] = round(max(team["form"] - 0.04, 0.85), 3)
    return _normalize_team(injured)
