from __future__ import annotations

import json
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd


def _discover_root_dir() -> Path:
    current = Path(__file__).resolve()
    for candidate in current.parents:
        if (
            (candidate / "data" / "teams.json").exists()
            and (candidate / "data" / "groups.json").exists()
            and (candidate / "data" / "starting_lineups.json").exists()
            and (candidate / "config" / "model_weights.json").exists()
        ):
            return candidate
    return current.parents[2]


ROOT_DIR = _discover_root_dir()
DATA_DIR = ROOT_DIR / "data"
CONFIG_DIR = ROOT_DIR / "config"
FC26_DATASET = DATA_DIR / "FC26_20250921.csv"
PLAYERS_JSON = DATA_DIR / "players.json"
PLAYER_IMAGES_JSON = CONFIG_DIR / "player_images.json"
NATIONALITY_ALIASES = {
    "Bosnia and Herzegovina": ["Bosnia Herzegovina"],
    "Czechia": ["Czech Republic"],
    "Curacao": ["Curaçao", "Curacao"],
    "DR Congo": ["Congo DR", "DR Congo"],
    "Ivory Coast": ["Côte d'Ivoire", "Ivory Coast"],
    "Korea Republic": ["Korea Republic", "South Korea"],
    "Turkiye": ["Turkey", "Türkiye"],
    "United States": ["United States", "USA"],
    "Cape Verde": ["Cape Verde", "Cape Verde Islands"],
}


@dataclass
class StaticDatasets:
    teams: pd.DataFrame
    players: pd.DataFrame
    groups: list[dict[str, Any]]
    starting_lineups: list[dict[str, Any]]


def _read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)


def _normalize_name(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value or "")
    ascii_only = "".join(char for char in normalized if not unicodedata.combining(char))
    return "".join(char.lower() for char in ascii_only if char.isalnum())


def _image_lookup() -> dict[str, dict[str, str]]:
    if not PLAYER_IMAGES_JSON.exists():
        return {}
    raw = _read_json(PLAYER_IMAGES_JSON)
    lookup: dict[str, dict[str, str]] = {}
    for row in raw:
        keys = [
            row.get("player_name", ""),
            row.get("short_name", ""),
            row.get("long_name", ""),
        ]
        for key in keys:
            normalized = _normalize_name(key)
            if normalized:
                lookup[normalized] = row
    return lookup


def _attach_player_image(player: dict[str, Any], image_lookup: dict[str, dict[str, str]]) -> dict[str, Any]:
    keys = [
        player.get("short_name", ""),
        player.get("long_name", ""),
        player.get("player_name", ""),
    ]
    image_meta = None
    for key in keys:
        normalized = _normalize_name(key)
        if normalized and normalized in image_lookup:
            image_meta = image_lookup[normalized]
            break
    return {
        **player,
        "image_url": image_meta.get("image_url") if image_meta else None,
        "image_path": image_meta.get("image_path") if image_meta else None,
        "headshot_path": image_meta.get("headshot_path") if image_meta else None,
    }


def _normalize_position(position_text: str) -> str:
    primary = (position_text or "CM").split(",")[0].strip().upper()
    position_map = {
        "GK": "GK",
        "CB": "CB",
        "LB": "LB",
        "RB": "RB",
        "LWB": "LWB",
        "RWB": "RWB",
        "CDM": "CDM",
        "CM": "CM",
        "CAM": "CAM",
        "LM": "LM",
        "RM": "RM",
        "LW": "LW",
        "RW": "RW",
        "ST": "ST",
        "CF": "CF",
    }
    return position_map.get(primary, "CM")


def _int_or(value: Any, fallback: int) -> int:
    if pd.isna(value) or value is None:
        return fallback
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


def _placeholder_player(team: dict[str, Any], index: int, position: str, overall: int) -> dict[str, Any]:
    base_name = team["team_name"].replace(" ", "")
    return {
        "player_id": f'{team["team_id"]}-{index}',
        "short_name": f"{base_name[:10]} {index}",
        "long_name": f'{team["team_name"]} Player {index}',
        "national_team": team["team_name"],
        "club": "Estimated XI",
        "league": "International",
        "position": position,
        "overall": overall,
        "pace": max(35, min(92, overall + (6 if position in {"LW", "RW", "ST", "CF"} else 1))),
        "shooting": max(30, min(92, overall + (5 if position in {"LW", "RW", "ST", "CF", "CAM"} else -6))),
        "passing": max(32, min(91, overall + (4 if position in {"CM", "CDM", "CAM", "LM", "RM"} else -3))),
        "dribbling": max(34, min(92, overall + (4 if position in {"LW", "RW", "CAM", "CF"} else -2))),
        "defending": max(20, min(90, overall + (5 if position in {"CB", "LB", "RB", "LWB", "RWB", "CDM"} else -15))),
        "physic": max(38, min(92, overall + (3 if position in {"CB", "CDM", "ST", "GK"} else 0))),
        "is_goalkeeper": position == "GK",
        "is_available": True,
        "is_estimated": True,
        "club_name": "Estimated XI",
        "league_name": "International",
    }


def _build_estimated_squad(team: dict[str, Any]) -> list[dict[str, Any]]:
    base = int(round(team["base_rating"]))
    template = [
        "GK", "GK", "GK",
        "RB", "CB", "CB", "LB", "RWB", "LWB", "CB",
        "CDM", "CDM", "CM", "CM", "CAM", "LM", "RM",
        "LW", "RW", "ST", "ST", "CF", "CM",
    ]
    extras = ["CB", "CM", "ST"] if team["fifa_rank"] <= 20 else ["LB", "RM", "CF"]
    positions = template + extras
    squad = []
    for index, position in enumerate(positions[:26], start=1):
        if position == "GK":
            overall = max(60, base - 1 + (3 - index))
        elif position in {"CB", "LB", "RB", "LWB", "RWB"}:
            overall = max(58, base - 3 + (index % 4))
        elif position in {"CDM", "CM", "CAM", "LM", "RM"}:
            overall = max(59, base - 2 + (index % 5))
        else:
            overall = max(60, base - 1 + (index % 5))
        squad.append(_placeholder_player(team, index, position, int(overall)))
    return squad


def generate_provisional_squads(teams: list[dict[str, Any]]) -> list[dict[str, Any]]:
    image_lookup = _image_lookup()
    if FC26_DATASET.exists():
        fc26 = pd.read_csv(FC26_DATASET, low_memory=False)
        fc26["nationality_key"] = fc26["nationality_name"].fillna("").str.casefold()
        players = []
        top_leagues = {"Premier League", "La Liga", "Bundesliga", "Serie A", "Ligue 1"}
        quotas = {"GK": 3, "DEF": 8, "MID": 8, "ATT": 4}

        def bucket(position: str) -> str:
            if position == "GK":
                return "GK"
            if position in {"CB", "LB", "RB", "LWB", "RWB"}:
                return "DEF"
            if position in {"CDM", "CM", "CAM", "LM", "RM"}:
                return "MID"
            return "ATT"

        for team in teams:
            aliases = NATIONALITY_ALIASES.get(team["team_name"], []) + [team["team_name"]]
            alias_keys = {alias.casefold() for alias in aliases}
            squad_frame = fc26[fc26["nationality_key"].isin(alias_keys)].copy()
            squad_frame["position"] = squad_frame["player_positions"].fillna("").map(_normalize_position)
            squad_frame["league_bonus"] = squad_frame["league_name"].isin(top_leagues).astype(int)
            squad_frame = squad_frame.sort_values(
                ["overall", "league_bonus", "pace", "passing", "defending"],
                ascending=False,
            )

            chosen_rows = []
            used_ids: set[Any] = set()
            for quota_position, quota_count in quotas.items():
                bucket_rows = squad_frame[squad_frame["position"].map(bucket) == quota_position].head(quota_count)
                for _, row in bucket_rows.iterrows():
                    row_id = row.get("long_name") or row.get("short_name")
                    if row_id in used_ids:
                        continue
                    used_ids.add(row_id)
                    chosen_rows.append(row)

            target_size = 26 if len(squad_frame) >= 26 else 23
            for _, row in squad_frame.iterrows():
                if len(chosen_rows) >= target_size:
                    break
                row_id = row.get("long_name") or row.get("short_name")
                if row_id in used_ids:
                    continue
                used_ids.add(row_id)
                chosen_rows.append(row)

            normalized = []
            for idx, row in enumerate(chosen_rows, start=1):
                normalized.append(
                    _attach_player_image(
                        {
                        "player_id": f'{team["team_id"]}-{idx}',
                        "short_name": row.get("short_name") or row.get("long_name") or f'{team["team_name"]} {idx}',
                        "long_name": row.get("long_name") or row.get("short_name") or f'{team["team_name"]} Player {idx}',
                        "national_team": team["team_name"],
                        "club": row.get("club_name") or "Unknown Club",
                        "league": row.get("league_name") or "Unknown League",
                        "position": row.get("position") or "CM",
                        "overall": _int_or(row.get("overall"), int(team["base_rating"])),
                        "pace": _int_or(row.get("pace"), 60),
                        "shooting": _int_or(row.get("shooting"), 55),
                        "passing": _int_or(row.get("passing"), 55),
                        "dribbling": _int_or(row.get("dribbling"), 55),
                        "defending": _int_or(row.get("defending"), 45),
                        "physic": _int_or(row.get("physic"), 60),
                        "is_goalkeeper": (row.get("position") == "GK"),
                        "is_available": True,
                        "is_estimated": False,
                        },
                        image_lookup,
                    )
                )

            goalkeeper_count = sum(1 for player in normalized if player["is_goalkeeper"])
            next_index = len(normalized) + 1
            while goalkeeper_count < 3:
                normalized.append(_placeholder_player(team, next_index, "GK", max(61, int(team["base_rating"]) - 3)))
                goalkeeper_count += 1
                next_index += 1
            while len(normalized) < 23:
                normalized.append(_placeholder_player(team, next_index, "CM", max(58, int(team["base_rating"]) - 6)))
                next_index += 1
            final_size = min(26, max(23, target_size))
            goalkeepers = [player for player in normalized if player["is_goalkeeper"]]
            outfielders = [player for player in normalized if not player["is_goalkeeper"]]
            balanced = goalkeepers[: min(len(goalkeepers), 4)] + outfielders[: final_size - min(len(goalkeepers), 4)]
            while len(balanced) < final_size:
                balanced.append(_placeholder_player(team, len(balanced) + 1, "CM", max(58, int(team["base_rating"]) - 6)))
            players.extend(balanced[:final_size])
        _write_json(PLAYERS_JSON, players)
        return players

    players = []
    for team in teams:
        players.extend(_attach_player_image(player, image_lookup) for player in _build_estimated_squad(team))
    _write_json(PLAYERS_JSON, players)
    return players


def load_static_datasets() -> StaticDatasets:
    teams = _read_json(DATA_DIR / "teams.json")
    groups = _read_json(DATA_DIR / "groups.json")
    if PLAYERS_JSON.exists():
        players = _read_json(PLAYERS_JSON)
        image_lookup = _image_lookup()
        players = [_attach_player_image(player, image_lookup) for player in players]
    else:
        players = generate_provisional_squads(teams)
    return StaticDatasets(
        teams=pd.DataFrame(teams),
        players=pd.DataFrame(players),
        groups=groups,
        starting_lineups=_read_json(DATA_DIR / "starting_lineups.json"),
    )


def load_model_weights() -> dict[str, float]:
    return _read_json(CONFIG_DIR / "model_weights.json")


def fc26_dataset_path() -> str:
    return str(FC26_DATASET)


def fc26_dataset_exists() -> bool:
    return FC26_DATASET.exists()
