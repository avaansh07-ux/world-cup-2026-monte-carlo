from __future__ import annotations

from functools import lru_cache
from typing import Any
import unicodedata
import math
import re

import pandas as pd

from backend.models.static_data import (
    FC26_DATASET,
    NATIONALITY_ALIASES,
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


def _tokenize_name(value: str) -> list[str]:
    normalized = unicodedata.normalize("NFKD", value or "")
    ascii_only = "".join(char for char in normalized if not unicodedata.combining(char))
    return [part for part in re.split(r"[^a-z0-9]+", ascii_only.lower()) if part]


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


def _match_player_record(players: list[dict[str, Any]], candidate: str) -> dict[str, Any] | None:
    target = _normalize_name(candidate)
    target_tokens = set(_tokenize_name(candidate))
    best_match = None
    best_score = 0.0

    for player in players:
        for field in ("short_name", "long_name", "player_name", "name"):
            value = player.get(field)
            if not value:
                continue
            normalized = _normalize_name(value)
            if not normalized:
                continue
            if normalized == target:
                return player
            if target and (target in normalized or normalized in target):
                score = 0.92
            else:
                value_tokens = set(_tokenize_name(value))
                if not target_tokens or not value_tokens:
                    continue
                overlap = len(target_tokens & value_tokens)
                if overlap == 0:
                    continue
                score = overlap / len(target_tokens)
            if score > best_score:
                best_score = score
                best_match = player

    return best_match if best_score >= 0.5 else None


def _with_team_slug(frame: pd.DataFrame) -> pd.DataFrame:
    enriched = frame.copy()
    enriched["team_slug"] = enriched["team_name"].map(_slugify)
    return enriched


def _normalize_position(position_text: str) -> str:
    primary = str(position_text or "CM").split(",")[0].strip().upper()
    return primary or "CM"


def _position_group(position: str) -> str:
    normalized = _normalize_position(position)
    if normalized == "GK":
        return "GK"
    if normalized in {"CB", "LB", "RB", "LWB", "RWB", "LCB", "RCB"}:
        return "DEF"
    if normalized in {"CDM", "CM", "CAM", "LM", "RM"}:
        return "MID"
    return "ATT"


@lru_cache(maxsize=1)
def _fc26_frame() -> pd.DataFrame:
    if not FC26_DATASET.exists():
        return pd.DataFrame()
    frame = pd.read_csv(FC26_DATASET, low_memory=False)
    frame["nationality_key"] = frame["nationality_name"].fillna("").str.casefold()
    return frame


def _fc26_records_for_team(team_name: str) -> list[dict[str, Any]]:
    frame = _fc26_frame()
    if frame.empty:
        return []
    aliases = NATIONALITY_ALIASES.get(team_name, []) + [team_name]
    alias_keys = {alias.casefold() for alias in aliases}
    squad_frame = frame[frame["nationality_key"].isin(alias_keys)].copy()
    records: list[dict[str, Any]] = []
    for _, row in squad_frame.iterrows():
        records.append(
            {
                "short_name": row.get("short_name"),
                "long_name": row.get("long_name"),
                "player_name": row.get("long_name") or row.get("short_name"),
                "national_team": team_name,
                "club": row.get("club_name") or "Unknown Club",
                "league": row.get("league_name") or "Unknown League",
                "position": _normalize_position(row.get("player_positions")),
                "overall": int(row.get("overall")) if pd.notna(row.get("overall")) else None,
                "pace": int(row.get("pace")) if pd.notna(row.get("pace")) else None,
                "shooting": int(row.get("shooting")) if pd.notna(row.get("shooting")) else None,
                "passing": int(row.get("passing")) if pd.notna(row.get("passing")) else None,
                "dribbling": int(row.get("dribbling")) if pd.notna(row.get("dribbling")) else None,
                "defending": int(row.get("defending")) if pd.notna(row.get("defending")) else None,
                "physic": int(row.get("physic")) if pd.notna(row.get("physic")) else None,
                "is_goalkeeper": _normalize_position(row.get("player_positions")) == "GK",
                "is_available": True,
                "is_estimated": False,
            }
        )
    return records


def _position_average_fallback(
    team_name: str,
    position: str,
    team: dict[str, Any],
    squad_records: list[dict[str, Any]],
    fallback_records: list[dict[str, Any]],
) -> dict[str, Any]:
    pool = [record for record in [*squad_records, *fallback_records] if record]
    group = _position_group(position)
    grouped = [record for record in pool if _position_group(record.get("position", position)) == group]
    source = grouped or pool

    def _avg(key: str, default: float) -> int:
        values = [record.get(key) for record in source if record.get(key) is not None]
        if values:
            return int(round(sum(values) / len(values)))
        return int(round(default))

    base = float(team.get("base_rating", 75))
    position_defaults = {
        "GK": {"overall": base - 1, "pace": 60, "shooting": 55, "passing": 55, "dribbling": 55, "defending": 45, "physic": 60},
        "DEF": {"overall": base - 2, "pace": 72, "shooting": 52, "passing": 67, "dribbling": 69, "defending": 77, "physic": 78},
        "MID": {"overall": base - 1, "pace": 74, "shooting": 72, "passing": 78, "dribbling": 79, "defending": 67, "physic": 74},
        "ATT": {"overall": base, "pace": 80, "shooting": 79, "passing": 74, "dribbling": 81, "defending": 45, "physic": 72},
    }[group]

    return {
        "player_name": None,
        "national_team": team_name,
        "club": "Projected XI",
        "league": "International",
        "position": _normalize_position(position),
        "overall": _avg("overall", position_defaults["overall"]),
        "pace": _avg("pace", position_defaults["pace"]),
        "shooting": _avg("shooting", position_defaults["shooting"]),
        "passing": _avg("passing", position_defaults["passing"]),
        "dribbling": _avg("dribbling", position_defaults["dribbling"]),
        "defending": _avg("defending", position_defaults["defending"]),
        "physic": _avg("physic", position_defaults["physic"]),
        "is_goalkeeper": group == "GK",
        "is_available": True,
        "is_estimated": False,
    }


def _hydrate_lineup_player(
    player_row: dict[str, Any],
    team: dict[str, Any],
    squad_records: list[dict[str, Any]],
    fallback_records: list[dict[str, Any]],
) -> dict[str, Any]:
    matched = (
        _match_player_record(squad_records, player_row["name"])
        or _match_player_record(fallback_records, player_row["name"])
        or {}
    )
    fallback = _position_average_fallback(
        team["team_name"],
        player_row.get("position", "CM"),
        team,
        squad_records,
        fallback_records,
    )
    enriched = {
        **fallback,
        **matched,
        **player_row,
    }
    for stat_key in ("overall", "pace", "shooting", "passing", "dribbling", "defending", "physic"):
        if enriched.get(stat_key) is None:
            enriched[stat_key] = fallback.get(stat_key)
    if not enriched.get("club"):
        enriched["club"] = fallback["club"]
    if not enriched.get("league"):
        enriched["league"] = fallback["league"]
    enriched["position"] = player_row.get("position", enriched.get("position"))
    enriched["is_goalkeeper"] = _position_group(enriched["position"]) == "GK"
    return enriched


def _average_stat(players: list[dict[str, Any]], key: str) -> float | None:
    values = [player.get(key) for player in players if player.get(key) is not None]
    if not values:
        return None
    return float(sum(values) / len(values))


def _lineup_rating_breakdown(
    team: dict[str, Any],
    lineup_players: list[dict[str, Any]],
) -> dict[str, Any]:
    grouped = {
        "GK": [player for player in lineup_players if _position_group(player.get("position", "CM")) == "GK"],
        "DEF": [player for player in lineup_players if _position_group(player.get("position", "CM")) == "DEF"],
        "MID": [player for player in lineup_players if _position_group(player.get("position", "CM")) == "MID"],
        "ATT": [player for player in lineup_players if _position_group(player.get("position", "CM")) == "ATT"],
    }
    return {
        "squad": _average_stat(lineup_players, "overall") or team["squad_rating"],
        "attack": _average_stat(grouped["ATT"], "overall") or team["attack_rating"],
        "midfield": _average_stat(grouped["MID"], "overall") or team["midfield_rating"],
        "defense": _average_stat(grouped["DEF"], "overall") or team["defense_rating"],
        "goalkeeper": _average_stat(grouped["GK"], "overall") or team["goalkeeper_rating"],
        "form": team["form_score"],
        "ranking": team["ranking_score"],
    }


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
    squad_records = squad.to_dict(orient="records")
    fallback_records = _fc26_records_for_team(team["team_name"])
    lineup_record = next((row for row in lineups if row["team_name"] == team["team_name"]), None)
    starting_lineup = {"formation": "4-3-3", "players": []}
    if lineup_record:
        starting_lineup = {
            "formation": lineup_record["formation"],
            "players": [
                _hydrate_lineup_player(player_row, team, squad_records, fallback_records)
                for player_row in lineup_record["players"]
            ],
        }
    rating_breakdown = _lineup_rating_breakdown(team, starting_lineup["players"])
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
        "ratingBreakdown": _sanitize_json(rating_breakdown),
    }
