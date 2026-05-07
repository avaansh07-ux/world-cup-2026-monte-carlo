from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from statistics import mean
from typing import Any

try:
    from ..config import settings
    from ..data.sample_teams import SAMPLE_TEAMS
    from .api_football import APIFootballClient
    from .cache import cache_is_fresh, read_json, write_json
except ImportError:
    from config import settings
    from data.sample_teams import SAMPLE_TEAMS
    from services.api_football import APIFootballClient
    from services.cache import cache_is_fresh, read_json, write_json


client = APIFootballClient()
LIVE_FIXTURE_SEASON = 2024


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


def _sample_payload() -> dict[str, Any]:
    return {
        "teams": [_normalize_team(team) for team in _sample_catalog()],
        "meta": {
            "source": "sample",
            "season": None,
            "cached": False,
            "generatedAt": datetime.now(timezone.utc).isoformat(),
            "note": "Curated demo data bundled with the app.",
        },
    }


def _pick_national_team(response: dict[str, Any], name: str) -> dict[str, Any]:
    for item in response.get("response", []):
        team = item.get("team", {})
        if team.get("national") and team.get("name", "").lower() == name.lower():
            return team
    raise KeyError(f"National team not found for {name}")


def _resolve_team_id(seed: dict[str, Any]) -> int:
    if seed.get("api_team_id"):
        return int(seed["api_team_id"])
    team_response = client.get("/teams", {"search": seed["name"]})
    national_team = _pick_national_team(team_response, seed["name"])
    return int(national_team["id"])


def _fixture_strengths(fixtures: list[dict[str, Any]], team_id: int) -> dict[str, float]:
    completed = []
    for fixture in fixtures:
        goals = fixture.get("goals", {})
        home = fixture.get("teams", {}).get("home", {})
        away = fixture.get("teams", {}).get("away", {})
        if goals.get("home") is None or goals.get("away") is None:
            continue

        is_home = int(home["id"]) == int(team_id)
        goals_for = goals["home"] if is_home else goals["away"]
        goals_against = goals["away"] if is_home else goals["home"]
        completed.append(
            {
                "goals_for": goals_for,
                "goals_against": goals_against,
                "points": 3 if goals_for > goals_against else 1 if goals_for == goals_against else 0,
            }
        )

    if not completed:
        return {"attack": 1.1, "defense": 1.0, "form": 1.0}

    matches = len(completed)
    goals_for_avg = sum(item["goals_for"] for item in completed) / matches
    goals_against_avg = sum(item["goals_against"] for item in completed) / matches
    points_per_match = sum(item["points"] for item in completed) / matches

    return {
        "attack": round(max(0.75, goals_for_avg), 3),
        "defense": round(max(0.45, goals_against_avg + 0.35), 3),
        "form": round(min(1.2, max(0.88, 0.88 + (points_per_match / 3) * 0.32)), 3),
    }


def _live_payload() -> dict[str, Any]:
    cache_path = settings.cache_dir / "teams.live.json"
    if cache_is_fresh(cache_path, settings.cache_ttl_hours):
        payload = read_json(cache_path)
        payload["meta"]["cached"] = True
        return payload

    teams: list[dict[str, Any]] = []
    for seed in _sample_catalog():
        team_id = _resolve_team_id(seed)
        fixture_response = client.get(
            "/fixtures",
            {"team": team_id, "season": LIVE_FIXTURE_SEASON, "status": "FT"},
        )
        strengths = _fixture_strengths(fixture_response.get("response", []), team_id)
        teams.append(
            _normalize_team(
                {
                    **seed,
                    "id": team_id,
                    "attack": strengths["attack"],
                    "defense": strengths["defense"],
                    "form": strengths["form"],
                }
            )
        )

    payload = {
        "teams": teams,
        "meta": {
            "source": "live",
            "season": LIVE_FIXTURE_SEASON,
            "cached": False,
            "generatedAt": datetime.now(timezone.utc).isoformat(),
            "note": "Live national-team data from API-Football. Your current API plan exposes fixtures through the 2024 season.",
        },
    }
    write_json(cache_path, payload)
    return payload


def load_teams_payload() -> dict[str, Any]:
    if settings.team_data_source != "live":
        return _sample_payload()
    try:
        return _live_payload()
    except Exception as exc:
        payload = _sample_payload()
        payload["meta"]["fallbackReason"] = str(exc)
        payload["meta"]["note"] = "Fell back to bundled sample data because the live fetch failed."
        return payload


def load_teams() -> list[dict[str, Any]]:
    return load_teams_payload()["teams"]


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
