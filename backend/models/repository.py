from __future__ import annotations

from functools import lru_cache
from typing import Any
import unicodedata
import math

import pandas as pd

from backend.models.static_data import (
    fc26_dataset_exists,
    fc26_dataset_path,
    generate_provisional_squads,
    load_static_datasets,
)
from backend.models.team_strength import calculate_team_profiles


def _normalize_name(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value or "")
    ascii_only = "".join(char for char in normalized if not unicodedata.combining(char))
    return "".join(char.lower() for char in ascii_only if char.isalnum())


def _slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value or "")
    ascii_only = "".join(char for char in normalized if not unicodedata.combining(char))
    return "-".join(part for part in "".join(char.lower() if char.isalnum() else " " for char in ascii_only).split())


def _sanitize_json(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _sanitize_json(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_sanitize_json(item) for item in value]
    if isinstance(value, float) and math.isnan(value):
        return None
    return value


def _with_team_slug(frame: pd.DataFrame) -> pd.DataFrame:
    enriched = frame.copy()
    enriched["team_slug"] = enriched["team_name"].map(_slugify)
    return enriched


@lru_cache(maxsize=1)
def _base_context() -> dict[str, Any]:
    datasets = load_static_datasets()
    profiles = _with_team_slug(calculate_team_profiles(datasets.teams, datasets.players))
    return {
        "teams": profiles,
        "players": datasets.players,
        "groups": datasets.groups,
        "startingLineups": datasets.starting_lineups,
    }


def clear_context_cache() -> None:
    _base_context.cache_clear()


def regenerate_squads() -> dict[str, Any]:
    datasets = load_static_datasets()
    generate_provisional_squads(datasets.teams.to_dict(orient="records"))
    clear_context_cache()
    context = _base_context()
    return {
        "generatedPlayers": len(context["players"]),
        "teams": len(context["teams"]),
        "source": "fc26" if fc26_dataset_exists() else "estimated",
        "fc26Path": fc26_dataset_path(),
    }


def _recompute_with_injuries(injuries: dict[str, list[str]]) -> dict[str, Any]:
    datasets = load_static_datasets()
    players = datasets.players.copy()
    for team_name, removed_players in injuries.items():
        players = players[
            ~(
                (players["national_team"] == team_name)
                & (players["short_name"].isin(removed_players))
            )
        ]
    profiles = _with_team_slug(calculate_team_profiles(datasets.teams, players))
    return {
        "teams": profiles,
        "players": players,
        "groups": datasets.groups,
        "startingLineups": datasets.starting_lineups,
    }


def load_context(injuries: dict[str, list[str]] | None = None) -> dict[str, Any]:
    if not injuries:
        return _base_context()
    return _recompute_with_injuries(injuries)


def groups_payload() -> list[dict[str, Any]]:
    return _base_context()["groups"]


def team_summary_records(injuries: dict[str, list[str]] | None = None) -> list[dict[str, Any]]:
    teams = load_context(injuries)["teams"].sort_values(["overall_strength", "fifa_rank"], ascending=[False, True])
    return teams.to_dict(orient="records")


def team_detail(team_ref: int | str, injuries: dict[str, list[str]] | None = None) -> dict[str, Any]:
    context = load_context(injuries)
    teams = context["teams"]
    players = context["players"]
    lineups = context["startingLineups"]
    if isinstance(team_ref, int) or str(team_ref).isdigit():
        team_rows = teams[teams["team_id"] == int(team_ref)]
    else:
        team_rows = teams[teams["team_slug"] == _slugify(str(team_ref))]
    if team_rows.empty:
        raise KeyError(f"Unknown team reference: {team_ref}")
    team = team_rows.iloc[0].to_dict()
    squad = players[players["national_team"] == team["team_name"]].sort_values(
        ["overall", "position", "short_name"],
        ascending=[False, True, True],
    )
    player_lookup = {}
    for player in squad.to_dict(orient="records"):
        for key in (player.get("short_name"), player.get("long_name")):
            if key:
                player_lookup[_normalize_name(key)] = player
    lineup_record = next((row for row in lineups if row["team_name"] == team["team_name"]), None)
    starting_lineup = {"formation": "4-3-3", "players": []}
    if lineup_record:
        starting_lineup = {
            "formation": lineup_record["formation"],
            "players": [
                {
                    **player_row,
                    **(player_lookup.get(_normalize_name(player_row["name"])) or {}),
                }
                for player_row in lineup_record["players"]
            ],
        }
    key_players = squad.head(6).to_dict(orient="records")
    available_count = int(squad["is_available"].sum()) if "is_available" in squad else len(squad)
    estimated_count = int(squad["is_estimated"].sum()) if "is_estimated" in squad else 0
    return {
        "team": _sanitize_json(team),
        "squad": _sanitize_json(squad.to_dict(orient="records")),
        "keyPlayers": _sanitize_json(key_players),
        "squadMeta": {
            "players": len(squad),
            "available": available_count,
            "estimated": estimated_count,
        },
        "startingLineup": _sanitize_json(starting_lineup),
        "ratingBreakdown": _sanitize_json({
            "squad": team["squad_rating"],
            "attack": team["attack_rating"],
            "midfield": team["midfield_rating"],
            "defense": team["defense_rating"],
            "goalkeeper": team["goalkeeper_rating"],
            "form": team["form_score"],
            "ranking": team["ranking_score"],
        }),
    }
