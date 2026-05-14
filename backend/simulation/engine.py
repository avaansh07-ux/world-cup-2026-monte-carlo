from __future__ import annotations

from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path
from typing import Any
from uuid import uuid4

import numpy as np
import pandas as pd

try:
    from backend.model_config import SIMULATION_CONFIG
except ModuleNotFoundError:
    from model_config import SIMULATION_CONFIG

YOUNG_PLAYER_CANDIDATES = {
    "Lamine Yamal": {"team": "Spain", "position": "Forward", "birthYear": 2007},
    "Désiré Doué": {"team": "France", "position": "Forward", "birthYear": 2005},
    "Kendry Páez": {"team": "Ecuador", "position": "Forward", "birthYear": 2007},
    "Kenan Yıldız": {"team": "Turkiye", "position": "Forward", "birthYear": 2005},
    "Arda Güler": {"team": "Turkiye", "position": "Midfielder", "birthYear": 2005},
    "Antonio Nusa": {"team": "Norway", "position": "Forward", "birthYear": 2005},
    "Dário Essugo": {"team": "Portugal", "position": "Midfielder", "birthYear": 2005},
}

YOUNG_PLAYER_CUTOFF_YEAR = 2005
_BIRTH_YEAR_LOOKUP: dict[str, int] | None = None

THIRD_PLACE_ELIGIBILITY: dict[str, tuple[str, ...]] = {
    "A": ("C", "E", "F", "H", "I"),
    "B": ("E", "F", "G", "I", "J"),
    "D": ("B", "E", "F", "I", "J"),
    "E": ("A", "B", "C", "D", "F"),
    "G": ("A", "E", "H", "I", "J"),
    "I": ("C", "D", "F", "G", "H"),
    "K": ("D", "E", "I", "J", "L"),
    "L": ("E", "H", "I", "J", "K"),
}

ROUND_OF_32_MATCHES: tuple[tuple[tuple[str, int], tuple[str, int | str]], ...] = (
    (("A", 2), ("B", 2)),          # Match 73
    (("E", 1), ("3P", "E")),       # Match 74
    (("F", 1), ("C", 2)),          # Match 75
    (("C", 1), ("F", 2)),          # Match 76
    (("I", 1), ("3P", "I")),       # Match 77
    (("E", 2), ("I", 2)),          # Match 78
    (("A", 1), ("3P", "A")),       # Match 79
    (("L", 1), ("3P", "L")),       # Match 80
    (("D", 1), ("3P", "D")),       # Match 81
    (("G", 1), ("3P", "G")),       # Match 82
    (("K", 2), ("L", 2)),          # Match 83
    (("H", 1), ("J", 2)),          # Match 84
    (("B", 1), ("3P", "B")),       # Match 85
    (("J", 1), ("H", 2)),          # Match 86
    (("K", 1), ("3P", "K")),       # Match 87
    (("D", 2), ("G", 2)),          # Match 88
)

ROUND_OF_16_REORDER = (0, 2, 1, 4, 3, 5, 6, 7, 10, 11, 8, 9, 13, 15, 12, 14)


def _normalize_name(value: str | None) -> str:
    return "".join(ch for ch in str(value or "").lower() if ch.isalnum())


def _birth_year_lookup() -> dict[str, int]:
    global _BIRTH_YEAR_LOOKUP
    if _BIRTH_YEAR_LOOKUP is not None:
        return _BIRTH_YEAR_LOOKUP

    lookup: dict[str, int] = {}
    csv_path = Path(__file__).resolve().parents[2] / "data" / "FC26_20250921.csv"
    if csv_path.exists():
        try:
            birth_df = pd.read_csv(csv_path, usecols=["short_name", "long_name", "dob"])
            for row in birth_df.to_dict(orient="records"):
                dob = str(row.get("dob") or "")
                if len(dob) >= 4 and dob[:4].isdigit():
                    birth_year = int(dob[:4])
                    for name_key in (row.get("short_name"), row.get("long_name")):
                        normalized = _normalize_name(name_key)
                        if normalized and normalized not in lookup:
                            lookup[normalized] = birth_year
        except Exception:
            lookup = {}

    _BIRTH_YEAR_LOOKUP = lookup
    return _BIRTH_YEAR_LOOKUP


def _scorer_weights(players: pd.DataFrame) -> pd.Series:
    position_bonus = players["position"].map(
        {
            "ST": 2.1,
            "CF": 1.9,
            "LW": 1.45,
            "RW": 1.45,
            "CAM": 0.9,
            "LM": 0.7,
            "RM": 0.7,
            "CM": 0.4,
            "CDM": 0.18,
            "LB": 0.08,
            "RB": 0.08,
            "LWB": 0.12,
            "RWB": 0.12,
            "CB": 0.03,
            "LCB": 0.03,
            "RCB": 0.03,
            "GK": 0.005,
        }
    ).fillna(0.22)
    weights = (
        players["shooting"] * SIMULATION_CONFIG.scorer_weight_shooting
        + players["overall"] * SIMULATION_CONFIG.scorer_weight_overall
        + players["pace"] * 0.04
        + players["passing"] * 0.02
        + position_bonus * 24 * SIMULATION_CONFIG.scorer_weight_position
    )
    return weights.clip(lower=0.01)


def _assist_weights(players: pd.DataFrame) -> pd.Series:
    position_bonus = players["position"].map(
        {
            "CAM": 1.7,
            "CM": 1.2,
            "RW": 1.15,
            "LW": 1.15,
            "RM": 1.05,
            "LM": 1.05,
            "CF": 1.0,
            "ST": 0.9,
            "CDM": 0.8,
            "RB": 0.65,
            "LB": 0.65,
            "RWB": 0.72,
            "LWB": 0.72,
            "CB": 0.2,
            "LCB": 0.2,
            "RCB": 0.2,
            "GK": 0.01,
        }
    ).fillna(0.35)
    weights = (
        players["passing"] * 0.08
        + players["dribbling"] * 0.03
        + players["overall"] * 0.015
        + position_bonus * 16
    )
    return weights.clip(lower=0.01)


def expected_goals(team: dict[str, Any], opponent: dict[str, Any], rng: np.random.Generator) -> float:
    variance = rng.normal(1.0, SIMULATION_CONFIG.variance)
    strength_edge = team["overall_strength"] - opponent["overall_strength"]
    mean = (
        team["attack_strength"] * 0.98
        + (team["attack_rating"] / 100) * 0.56
        + (team["squad_rating"] / 100) * 0.38
        + team["overall_strength"] * 0.8
        + strength_edge * 0.82
        - opponent["defense_strength"] * 0.74
        - opponent["overall_strength"] * 0.24
        + SIMULATION_CONFIG.home_advantage
    )
    return max(0.15, mean * variance)


def simulate_match(
    team_a: dict[str, Any],
    team_b: dict[str, Any],
    players_df: pd.DataFrame,
    rng: np.random.Generator,
    knockout: bool = False,
) -> dict[str, Any]:
    lambda_a = expected_goals(team_a, team_b, rng)
    lambda_b = expected_goals(team_b, team_a, rng)
    regular_a = int(rng.poisson(lambda_a))
    regular_b = int(rng.poisson(lambda_b))
    goals_a = regular_a
    goals_b = regular_b
    penalties = None

    if knockout and goals_a == goals_b:
        edge = team_a["overall_strength"] - team_b["overall_strength"]
        goals_a += int(rng.binomial(1, min(0.58, max(0.22, 0.36 + edge * 0.6))))
        goals_b += int(rng.binomial(1, min(0.58, max(0.22, 0.33 - edge * 0.6))))
        if goals_a == goals_b:
            penalty_edge = team_a["overall_strength"] - team_b["overall_strength"]
            base_a = min(5, max(3, round(4 + penalty_edge * 3)))
            base_b = min(5, max(3, round(4 - penalty_edge * 3)))
            penalties = {
                team_a["team_name"]: base_a,
                team_b["team_name"]: base_b,
            }
            while penalties[team_a["team_name"]] == penalties[team_b["team_name"]]:
                penalties[team_b["team_name"]] = int(rng.integers(3, 6))

    scorers = []
    goal_events = []
    for team_name, goal_count in ((team_a["team_name"], goals_a), (team_b["team_name"], goals_b)):
        team_players = players_df[(players_df["national_team"] == team_name) & (players_df["is_available"] == True)]
        if team_players.empty or goal_count == 0:
            continue
        scorer_weights = _scorer_weights(team_players)
        assist_weights = _assist_weights(team_players)
        player_names = team_players["short_name"].tolist()
        sampled_scorers = rng.choice(
            player_names,
            size=goal_count,
            replace=True,
            p=(scorer_weights / scorer_weights.sum()),
        )
        for scorer_name in sampled_scorers.tolist():
            assister_name = None
            if len(player_names) > 1 and rng.random() >= 0.18:
                assist_pool = team_players[team_players["short_name"] != scorer_name]
                if not assist_pool.empty:
                    pool_weights = assist_weights.loc[assist_pool.index]
                    assister_name = rng.choice(
                        assist_pool["short_name"].tolist(),
                        p=(pool_weights / pool_weights.sum()),
                    ).item()
            scorers.append(scorer_name)
            goal_events.append({"team": team_name, "scorer": scorer_name, "assister": assister_name})

    winner = None
    if goals_a > goals_b:
        winner = team_a["team_name"]
    elif goals_b > goals_a:
        winner = team_b["team_name"]
    elif penalties:
        winner = max(penalties, key=penalties.get)

    return {
        "homeTeam": team_a["team_name"],
        "awayTeam": team_b["team_name"],
        "homeGoals": goals_a,
        "awayGoals": goals_b,
        "winner": winner,
        "penalties": penalties,
        "scorers": scorers,
        "goalEvents": goal_events,
        "regularTime": {"homeGoals": regular_a, "awayGoals": regular_b},
    }


def compare_teams(
    team_a: dict[str, Any],
    team_b: dict[str, Any],
    players_df: pd.DataFrame,
    iterations: int,
) -> dict[str, Any]:
    rng = np.random.default_rng()
    group_results = Counter()
    knockout_results = Counter()
    group_scorelines = Counter()
    knockout_scorelines = Counter()

    for _ in range(iterations):
        group_match = simulate_match(team_a, team_b, players_df, rng, knockout=False)
        if group_match["homeGoals"] > group_match["awayGoals"]:
            group_results["teamAWin"] += 1
        elif group_match["awayGoals"] > group_match["homeGoals"]:
            group_results["teamBWin"] += 1
        else:
            group_results["draw"] += 1
        group_scorelines[f'{group_match["homeGoals"]}-{group_match["awayGoals"]}'] += 1

        knockout_match = simulate_match(team_a, team_b, players_df, rng, knockout=True)
        if knockout_match["winner"] == team_a["team_name"]:
            knockout_results["teamAWin"] += 1
        else:
            knockout_results["teamBWin"] += 1
        knockout_scorelines[f'{knockout_match["homeGoals"]}-{knockout_match["awayGoals"]}'] += 1

    top_group = group_scorelines.most_common(1)[0][0] if group_scorelines else None
    top_knockout = knockout_scorelines.most_common(1)[0][0] if knockout_scorelines else None

    return {
        "iterations": iterations,
        "groupStage": {
            "teamAWinProbability": round(group_results["teamAWin"] / iterations, 4),
            "drawProbability": round(group_results["draw"] / iterations, 4),
            "teamBWinProbability": round(group_results["teamBWin"] / iterations, 4),
            "mostLikelyScoreline": top_group,
        },
        "knockoutStage": {
            "teamAWinProbability": round(knockout_results["teamAWin"] / iterations, 4),
            "teamBWinProbability": round(knockout_results["teamBWin"] / iterations, 4),
            "mostLikelyScoreline": top_knockout,
        },
    }


def _team_sort_key(row: dict[str, Any], rng: np.random.Generator) -> tuple[float, float, float, float]:
    return (
        row["points"],
        row["goal_difference"],
        row["goals_for"],
        rng.random(),
    )


def _group_table(group_teams: list[dict[str, Any]], players_df: pd.DataFrame, rng: np.random.Generator) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    table = {
        team["team_name"]: {
            "team": team,
            "points": 0,
            "goal_difference": 0,
            "goals_for": 0,
            "goals_against": 0,
        }
        for team in group_teams
    }
    match_log = []
    for home, away in combinations(group_teams, 2):
        result = simulate_match(home, away, players_df, rng, knockout=False)
        match_log.append(result)
        home_goals = result["homeGoals"]
        away_goals = result["awayGoals"]
        table[home["team_name"]]["goal_difference"] += home_goals - away_goals
        table[away["team_name"]]["goal_difference"] += away_goals - home_goals
        table[home["team_name"]]["goals_for"] += home_goals
        table[away["team_name"]]["goals_for"] += away_goals
        table[home["team_name"]]["goals_against"] += away_goals
        table[away["team_name"]]["goals_against"] += home_goals
        if home_goals > away_goals:
            table[home["team_name"]]["points"] += 3
        elif away_goals > home_goals:
            table[away["team_name"]]["points"] += 3
        else:
            table[home["team_name"]]["points"] += 1
            table[away["team_name"]]["points"] += 1
    ordered = sorted(table.values(), key=lambda row: _team_sort_key(row, rng), reverse=True)
    return ordered, match_log


def _assign_third_place_groups(
    third_place_groups: list[str],
) -> dict[str, str]:
    winner_groups = [group for group, _ in THIRD_PLACE_ELIGIBILITY.items()]
    options = {
        winner_group: [group for group in third_place_groups if group in THIRD_PLACE_ELIGIBILITY[winner_group]]
        for winner_group in winner_groups
    }
    assignment: dict[str, str] = {}
    used: set[str] = set()

    def solve(remaining_winners: list[str]) -> bool:
        if not remaining_winners:
            return True
        winner_group = min(remaining_winners, key=lambda group: len([option for option in options[group] if option not in used]))
        remaining_after = [group for group in remaining_winners if group != winner_group]
        for third_group in sorted(options[winner_group]):
            if third_group in used:
                continue
            assignment[winner_group] = third_group
            used.add(third_group)
            if solve(remaining_after):
                return True
            used.remove(third_group)
            assignment.pop(winner_group, None)
        return False

    if not solve(winner_groups):
        raise ValueError(f"Unable to assign third-place groups for combination: {sorted(third_place_groups)}")
    return assignment


def _build_round_of_32_from_group_rows(group_results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    placements: dict[str, dict[int, dict[str, Any]]] = defaultdict(dict)
    third_place_rows = []
    for row in group_results:
        placements[row["group"]][row["placement"]] = row["team"]
        if row["placement"] == 3:
            third_place_rows.append(row)

    best_third_place_groups = [
        row["group"]
        for row in sorted(
            third_place_rows,
            key=lambda row: (row["points"], row["goal_difference"], row["goals_for"], -row["team"]["fifa_rank"]),
            reverse=True,
        )[:8]
    ]
    third_assignment = _assign_third_place_groups(best_third_place_groups)

    bracket: list[dict[str, Any]] = []
    for left_slot, right_slot in ROUND_OF_32_MATCHES:
        for group_name, placement in (left_slot, right_slot):
            if group_name == "3P":
                winner_group = str(placement)
                third_group = third_assignment[winner_group]
                bracket.append(placements[third_group][3])
            else:
                bracket.append(placements[group_name][int(placement)])
    return bracket


def _seed_knockout(group_results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return _build_round_of_32_from_group_rows(group_results)


def _play_knockout_round(
    teams: list[dict[str, Any]],
    players_df: pd.DataFrame,
    rng: np.random.Generator,
    round_name: str,
    scorer_counter: Counter[tuple[str, str]],
    assist_counter: Counter[tuple[str, str]],
    minutes_counter: Counter[tuple[str, str]],
    team_match_counter: Counter[str],
    lineup_lookup: dict[str, list[str]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    winners = []
    losers = []
    bracket_rows = []
    for home, away in zip(teams[::2], teams[1::2]):
        result = simulate_match(home, away, players_df, rng, knockout=True)
        match_minutes = 120 if result["regularTime"]["homeGoals"] == result["regularTime"]["awayGoals"] else 90
        team_match_counter[home["team_name"]] += 1
        team_match_counter[away["team_name"]] += 1
        for team_name in (home["team_name"], away["team_name"]):
            for player_name in lineup_lookup.get(team_name, []):
                minutes_counter[(team_name, player_name)] += match_minutes
        winner = home if result["winner"] == home["team_name"] else away
        loser = away if winner is home else home
        winners.append(winner)
        losers.append(loser)
        bracket_rows.append({"round": round_name, **result})
        for event in result.get("goalEvents", []):
            scorer_counter[(event["team"], event["scorer"])] += 1
            if event.get("assister"):
                assist_counter[(event["team"], event["assister"])] += 1
    return winners, losers, bracket_rows


def _expected_goals_fast(
    attack_strength: float,
    attack_rating: float,
    squad_rating: float,
    overall_strength: float,
    opponent_defense_strength: float,
    opponent_overall_strength: float,
    rng: np.random.Generator,
) -> float:
    variance = rng.normal(1.0, SIMULATION_CONFIG.variance)
    strength_edge = overall_strength - opponent_overall_strength
    mean = (
        attack_strength * 0.98
        + (attack_rating / 100) * 0.56
        + (squad_rating / 100) * 0.38
        + overall_strength * 0.8
        + strength_edge * 0.82
        - opponent_defense_strength * 0.74
        - opponent_overall_strength * 0.24
        + SIMULATION_CONFIG.home_advantage
    )
    return max(0.15, mean * variance)


def _simulate_match_fast(
    team_a_idx: int,
    team_b_idx: int,
    attack_strengths: np.ndarray,
    attack_ratings: np.ndarray,
    squad_ratings: np.ndarray,
    overall_strengths: np.ndarray,
    defense_strengths: np.ndarray,
    rng: np.random.Generator,
    knockout: bool = False,
) -> tuple[int, int, int]:
    lambda_a = _expected_goals_fast(
        float(attack_strengths[team_a_idx]),
        float(attack_ratings[team_a_idx]),
        float(squad_ratings[team_a_idx]),
        float(overall_strengths[team_a_idx]),
        float(defense_strengths[team_b_idx]),
        float(overall_strengths[team_b_idx]),
        rng,
    )
    lambda_b = _expected_goals_fast(
        float(attack_strengths[team_b_idx]),
        float(attack_ratings[team_b_idx]),
        float(squad_ratings[team_b_idx]),
        float(overall_strengths[team_b_idx]),
        float(defense_strengths[team_a_idx]),
        float(overall_strengths[team_a_idx]),
        rng,
    )
    goals_a = int(rng.poisson(lambda_a))
    goals_b = int(rng.poisson(lambda_b))

    if knockout and goals_a == goals_b:
        edge = float(overall_strengths[team_a_idx] - overall_strengths[team_b_idx])
        goals_a += int(rng.binomial(1, min(0.58, max(0.22, 0.36 + edge * 0.6))))
        goals_b += int(rng.binomial(1, min(0.58, max(0.22, 0.33 - edge * 0.6))))
        if goals_a == goals_b:
            winner_idx = team_a_idx if rng.random() < (0.5 + edge * 0.22) else team_b_idx
            return goals_a, goals_b, winner_idx

    if goals_a > goals_b:
        return goals_a, goals_b, team_a_idx
    if goals_b > goals_a:
        return goals_a, goals_b, team_b_idx
    return goals_a, goals_b, team_a_idx if rng.random() >= 0.5 else team_b_idx


def _sort_group_rows(
    indices: list[int],
    points: np.ndarray,
    goal_difference: np.ndarray,
    goals_for: np.ndarray,
    fifa_ranks: np.ndarray,
    rng: np.random.Generator,
) -> list[int]:
    return sorted(
        indices,
        key=lambda idx: (
            int(points[idx]),
            int(goal_difference[idx]),
            int(goals_for[idx]),
            -int(fifa_ranks[idx]),
            float(rng.random()),
        ),
        reverse=True,
    )


def _build_round_of_32_indices(group_rows: list[tuple[int, int, int, int, int, str]], fifa_ranks: np.ndarray) -> list[int]:
    placements: dict[str, dict[int, int]] = defaultdict(dict)
    third_place_rows: list[tuple[int, int, int, int, int, str]] = []

    for idx, placement, points, goal_difference, goals_for, group_name in group_rows:
        placements[group_name][placement] = idx
        if placement == 3:
            third_place_rows.append((idx, placement, points, goal_difference, goals_for, group_name))

    best_third_place_groups = [
        row[5]
        for row in sorted(
            third_place_rows,
            key=lambda row: (row[2], row[3], row[4], -int(fifa_ranks[row[0]])),
            reverse=True,
        )[:8]
    ]
    third_assignment = _assign_third_place_groups(best_third_place_groups)

    bracket: list[int] = []
    for left_slot, right_slot in ROUND_OF_32_MATCHES:
        for group_name, placement in (left_slot, right_slot):
            if group_name == "3P":
                winner_group = str(placement)
                third_group = third_assignment[winner_group]
                bracket.append(placements[third_group][3])
            else:
                bracket.append(placements[group_name][int(placement)])
    return bracket


def _generate_sample_bracket(
    teams_df: pd.DataFrame,
    groups_payload: list[dict[str, Any]],
    players_df: pd.DataFrame,
    starting_lineups: list[dict[str, Any]],
    rng: np.random.Generator,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    team_lookup = {row["team_name"]: row for row in teams_df.to_dict(orient="records")}
    alias_lookup: dict[str, str] = {}
    for row in players_df[["short_name", "long_name"]].drop_duplicates("short_name").to_dict(orient="records"):
        short_name = row.get("short_name")
        if not short_name:
            continue
        for alias in (row.get("short_name"), row.get("long_name")):
            normalized = _normalize_name(alias)
            if normalized and normalized not in alias_lookup:
                alias_lookup[normalized] = short_name
    scorer_counter: Counter[tuple[str, str]] = Counter()
    assist_counter: Counter[tuple[str, str]] = Counter()
    minutes_counter: Counter[tuple[str, str]] = Counter()
    team_match_counter: Counter[str] = Counter()
    lineup_lookup = {
        entry["team_name"]: [
            alias_lookup.get(_normalize_name(player.get("name")), player.get("name"))
            for player in entry.get("players", [])
            if player.get("name")
        ]
        for entry in starting_lineups
    }
    current_bracket: list[dict[str, Any]] = []
    current_groups: list[dict[str, Any]] = []
    group_results: list[dict[str, Any]] = []

    for group in groups_payload:
        group_name = group["group"]
        group_teams = [team_lookup[name] for name in group["teams"]]
        table, match_log = _group_table(group_teams, players_df, rng)
        current_groups.append(
            {
                "group": group_name,
                "table": [
                    {
                        "team": row["team"]["team_name"],
                        "points": row["points"],
                        "goalDifference": row["goal_difference"],
                        "goalsFor": row["goals_for"],
                    }
                    for row in table
                ],
            }
        )
        for match in match_log:
            team_match_counter[match.get("homeTeam")] += 1
            team_match_counter[match.get("awayTeam")] += 1
            for team_name in (match.get("homeTeam"), match.get("awayTeam")):
                for player_name in lineup_lookup.get(team_name, []):
                    minutes_counter[(team_name, player_name)] += 90
            for event in match.get("goalEvents", []):
                scorer_counter[(event["team"], event["scorer"])] += 1
                if event.get("assister"):
                    assist_counter[(event["team"], event["assister"])] += 1
        for placement, row in enumerate(table, start=1):
            group_results.append({**row, "group": group_name, "placement": placement})

    round_of_32 = _seed_knockout(group_results)
    round_of_32_winners, _, bracket_rows = _play_knockout_round(round_of_32, players_df, rng, "Round of 32", scorer_counter, assist_counter, minutes_counter, team_match_counter, lineup_lookup)
    current_bracket.extend(bracket_rows)
    round_of_16 = [round_of_32_winners[idx] for idx in ROUND_OF_16_REORDER]
    quarterfinals, _, bracket_rows = _play_knockout_round(round_of_16, players_df, rng, "Round of 16", scorer_counter, assist_counter, minutes_counter, team_match_counter, lineup_lookup)
    current_bracket.extend(bracket_rows)
    semifinals, _, bracket_rows = _play_knockout_round(quarterfinals, players_df, rng, "Quarter-final", scorer_counter, assist_counter, minutes_counter, team_match_counter, lineup_lookup)
    current_bracket.extend(bracket_rows)
    finalists, semi_losers, bracket_rows = _play_knockout_round(semifinals, players_df, rng, "Semi-final", scorer_counter, assist_counter, minutes_counter, team_match_counter, lineup_lookup)
    current_bracket.extend(bracket_rows)

    bronze_result = simulate_match(semi_losers[0], semi_losers[1], players_df, rng, knockout=True)
    bronze_minutes = 120 if bronze_result["regularTime"]["homeGoals"] == bronze_result["regularTime"]["awayGoals"] else 90
    for team_name in (semi_losers[0]["team_name"], semi_losers[1]["team_name"]):
        team_match_counter[team_name] += 1
        for player_name in lineup_lookup.get(team_name, []):
            minutes_counter[(team_name, player_name)] += bronze_minutes
    current_bracket.append({"round": "Third Place Match", **bronze_result})
    for event in bronze_result.get("goalEvents", []):
        scorer_counter[(event["team"], event["scorer"])] += 1
        if event.get("assister"):
            assist_counter[(event["team"], event["assister"])] += 1

    final_result = simulate_match(finalists[0], finalists[1], players_df, rng, knockout=True)
    final_minutes = 120 if final_result["regularTime"]["homeGoals"] == final_result["regularTime"]["awayGoals"] else 90
    for team_name in (finalists[0]["team_name"], finalists[1]["team_name"]):
        team_match_counter[team_name] += 1
        for player_name in lineup_lookup.get(team_name, []):
            minutes_counter[(team_name, player_name)] += final_minutes
    current_bracket.append({"round": "Final", **final_result})
    for event in final_result.get("goalEvents", []):
        scorer_counter[(event["team"], event["scorer"])] += 1
        if event.get("assister"):
            assist_counter[(event["team"], event["assister"])] += 1

    player_lookup = {
        (str(row.get("national_team")), str(row.get("short_name"))): row
        for row in players_df.drop_duplicates(["national_team", "short_name"]).to_dict(orient="records")
        if row.get("national_team") and row.get("short_name")
    }
    top_scorers = []
    for (country, player), goals in scorer_counter.most_common(15):
        meta = player_lookup.get((country, player), {})
        top_scorers.append(
            {
                "player": player,
                "goals": goals,
                "assists": int(assist_counter.get((country, player), 0)),
                "minutes": int(minutes_counter.get((country, player), 0) or team_match_counter.get(country, 0) * 90),
                "country": country,
                "position": meta.get("position", "ATT"),
                "overall": meta.get("overall"),
                "image_url": meta.get("image_url"),
                "image_path": meta.get("image_path"),
                "headshot_path": meta.get("headshot_path"),
            }
        )

    return current_bracket, current_groups, top_scorers


def _sample_bracket_score(
    sample_bracket: list[dict[str, Any]],
    probabilities: list[dict[str, Any]],
) -> float:
    probability_lookup = {entry["team"]: entry for entry in probabilities}
    champion_order = {
        entry["team"]: idx
        for idx, entry in enumerate(
            sorted(probabilities, key=lambda item: item.get("championProbability", 0), reverse=True)
        )
    }
    score = 0.0

    quarterfinalists = [
        team_name
        for match in sample_bracket
        if match.get("round") == "Quarter-final"
        for team_name in (match.get("homeTeam"), match.get("awayTeam"))
        if team_name
    ]
    semifinalists = [
        team_name
        for match in sample_bracket
        if match.get("round") == "Semi-final"
        for team_name in (match.get("homeTeam"), match.get("awayTeam"))
        if team_name
    ]

    for match in sample_bracket:
        round_name = match.get("round")
        home_team = match.get("homeTeam")
        away_team = match.get("awayTeam")
        home_probability = probability_lookup.get(home_team, {})
        away_probability = probability_lookup.get(away_team, {})

        if round_name == "Quarter-final":
            score += float(home_probability.get("quarterFinalProbability", 0)) * 3.0
            score += float(away_probability.get("quarterFinalProbability", 0)) * 3.0
            score += float(home_probability.get("semiFinalProbability", 0)) * 4.0
            score += float(away_probability.get("semiFinalProbability", 0)) * 4.0
            score += float(home_probability.get("championProbability", 0)) * 2.5
            score += float(away_probability.get("championProbability", 0)) * 2.5
        elif round_name == "Semi-final":
            score += float(home_probability.get("semiFinalProbability", 0)) * 9.0
            score += float(away_probability.get("semiFinalProbability", 0)) * 9.0
            score += float(home_probability.get("finalProbability", 0)) * 10.0
            score += float(away_probability.get("finalProbability", 0)) * 10.0
            score += float(home_probability.get("championProbability", 0)) * 16.0
            score += float(away_probability.get("championProbability", 0)) * 16.0
        elif round_name == "Final":
            score += float(home_probability.get("finalProbability", 0)) * 16.0
            score += float(away_probability.get("finalProbability", 0)) * 16.0
            score += float(home_probability.get("championProbability", 0)) * 18.0
            score += float(away_probability.get("championProbability", 0)) * 18.0

    final_match = next((match for match in sample_bracket if match.get("round") == "Final"), None)
    champion = final_match.get("winner") if final_match else None
    finalist_names = [final_match.get("homeTeam"), final_match.get("awayTeam")] if final_match else []
    for finalist in finalist_names:
        finalist_probability = probability_lookup.get(finalist, {})
        score += float(finalist_probability.get("finalProbability", 0)) * 26.0
        score += float(finalist_probability.get("championProbability", 0)) * 30.0
        score -= champion_order.get(finalist, 24) * 0.8
    if champion:
        score += float(probability_lookup.get(champion, {}).get("championProbability", 0)) * 48.0
        score -= champion_order.get(champion, 24) * 6.5

    for quarterfinalist in quarterfinalists:
        order = champion_order.get(quarterfinalist, 24)
        if order > 15:
            score -= (order - 15) * 0.9
    for semifinalist in semifinalists:
        order = champion_order.get(semifinalist, 24)
        score -= order * 1.1
        if order > 11:
            score -= (order - 11) * 3.4
    for finalist in finalist_names:
        order = champion_order.get(finalist, 24)
        if order > 7:
            score -= (order - 7) * 7.0
        if order > 11:
            score -= 220.0
    if champion:
        champion_order_index = champion_order.get(champion, 24)
        if champion_order_index > 7:
            score -= 260.0
        if champion_order_index > 11:
            score -= 420.0
    for semifinalist in semifinalists:
        order = champion_order.get(semifinalist, 24)
        if order > 15:
            score -= 120.0
    return score


def _representative_sample_bracket(
    teams_df: pd.DataFrame,
    groups_payload: list[dict[str, Any]],
    players_df: pd.DataFrame,
    starting_lineups: list[dict[str, Any]],
    probabilities: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    best_score = float("-inf")
    best_payload: tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]] | None = None

    # Keep the display-bracket search bounded so the API stays responsive.
    for _ in range(8):
        payload = _generate_sample_bracket(teams_df, groups_payload, players_df, starting_lineups, np.random.default_rng())
        bracket_rows = payload[0]
        score = _sample_bracket_score(bracket_rows, probabilities)
        if score > best_score:
            best_score = score
            best_payload = payload

    if best_payload is None:
        return _generate_sample_bracket(teams_df, groups_payload, players_df, starting_lineups, np.random.default_rng())
    return best_payload


def _position_family(position: str | None) -> str:
    normalized = str(position or "").upper()
    if normalized == "GK":
        return "GK"
    if normalized in {"CB", "LB", "RB", "LWB", "RWB", "LCB", "RCB"}:
        return "DEF"
    if normalized in {"CDM", "CM", "CAM", "LM", "RM"}:
        return "MID"
    return "ATT"


def _boot_position_family(position: str | None) -> str:
    family = _position_family(position)
    if family == "ATT":
        return "ATT"
    if family == "MID":
        return "MID"
    return "INELIGIBLE"


def _stage_scores(sample_bracket: list[dict[str, Any]]) -> tuple[dict[str, int], str | None]:
    stage = Counter()
    final_match = next((match for match in sample_bracket if match.get("round") == "Final"), None)
    champion = final_match.get("winner") if final_match else None

    for match in sample_bracket:
        round_name = match.get("round")
        if round_name == "Round of 32":
            weight = 1
        elif round_name == "Round of 16":
            weight = 2
        elif round_name == "Quarter-final":
            weight = 3
        elif round_name == "Semi-final":
            weight = 4
        elif round_name == "Final":
            weight = 5
        else:
            weight = 0
        for team_name in (match.get("homeTeam"), match.get("awayTeam")):
            if team_name:
                stage[team_name] = max(stage[team_name], weight)
    if champion:
        stage[champion] = 6
    return dict(stage), champion


def _team_lookup_from_lineups(starting_lineups: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    return {entry["team_name"]: entry.get("players", []) for entry in starting_lineups}


def _candidate_pool(
    starting_lineups: list[dict[str, Any]],
    probabilities: list[dict[str, Any]],
    sample_bracket: list[dict[str, Any]],
    top_scorers: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, int], str | None]:
    probability_lookup = {entry["team"]: entry for entry in probabilities}
    scorer_lookup = {
        (_normalize_name(entry["player"]), entry.get("country")): entry
        for entry in top_scorers
    }
    stage_lookup, champion = _stage_scores(sample_bracket)
    birth_years = _birth_year_lookup()
    pool: list[dict[str, Any]] = []

    for lineup in starting_lineups:
        team_name = lineup["team_name"]
        probability_row = probability_lookup.get(team_name, {})
        stage_score = stage_lookup.get(team_name, 0)
        for player in lineup.get("players", []):
            overall = player.get("overall")
            if overall is None:
                continue
            scorer_meta = scorer_lookup.get((_normalize_name(player.get("name")), team_name), {})
            pool.append(
                {
                    "player": player.get("name"),
                    "team": team_name,
                    "position": player.get("position"),
                    "positionLabel": _position_family(player.get("position")),
                    "overall": overall,
                    "goals": scorer_meta.get("goals", 0),
                    "stageScore": stage_score,
                    "championProbability": probability_row.get("championProbability", 0),
                    "finalProbability": probability_row.get("finalProbability", 0),
                    "semiFinalProbability": probability_row.get("semiFinalProbability", 0),
                    "birthYear": birth_years.get(_normalize_name(player.get("name"))),
                }
            )
    return pool, stage_lookup, champion


def _award_player(player: dict[str, Any] | None, **extra: Any) -> dict[str, Any] | None:
    if not player:
        return None
    return {
        "player": player.get("player"),
        "team": player.get("team"),
        "position": player.get("position"),
        "overall": player.get("overall"),
        **extra,
    }


def _boot_award_player(
    scorer_row: dict[str, Any] | None,
    player_lookup: dict[str, dict[str, Any]],
) -> dict[str, Any] | None:
    if not scorer_row:
        return None

    player_name = scorer_row.get("player")
    lineup_meta = player_lookup.get(_normalize_name(player_name), {})

    return {
        "player": player_name,
        "team": lineup_meta.get("team") or scorer_row.get("country"),
        "position": lineup_meta.get("position") or scorer_row.get("position"),
        "overall": lineup_meta.get("overall") if lineup_meta else scorer_row.get("overall"),
        "goals": scorer_row.get("goals"),
        "assists": scorer_row.get("assists"),
        "minutes": scorer_row.get("minutes"),
    }


def _generate_awards(
    starting_lineups: list[dict[str, Any]],
    probabilities: list[dict[str, Any]],
    sample_bracket: list[dict[str, Any]],
    top_scorers: list[dict[str, Any]],
) -> dict[str, Any]:
    pool, stage_lookup, champion = _candidate_pool(starting_lineups, probabilities, sample_bracket, top_scorers)
    player_lookup = {_normalize_name(entry["player"]): entry for entry in pool}

    def ball_position_bonus(position: str | None) -> float:
        normalized = str(position or "").upper()
        if normalized == "GK":
            return 1.5
        if normalized in {"CB", "LCB", "RCB", "LB", "RB", "LWB", "RWB"}:
            return 2.0
        if normalized in {"CDM", "CM", "CAM", "LM", "RM"}:
            return 2.5
        return 1.0

    def ball_score(player: dict[str, Any]) -> float:
        return (
            float(player["overall"]) * 1.0
            + float(player["goals"]) * 2.5
            + float(player["stageScore"]) * 5.0
            + float(player["championProbability"]) * 100.0
            + float(player["finalProbability"]) * 35.0
            + ball_position_bonus(player.get("position"))
        )

    ball_podium = sorted(pool, key=ball_score, reverse=True)[:3]

    goalkeepers = [player for player in pool if player["positionLabel"] == "GK"]
    glove_winner = max(
        goalkeepers,
        key=lambda player: float(player["overall"]) + float(player["stageScore"]) * 5.0 + float(player["championProbability"]) * 100.0,
        default=None,
    )

    young_pool = []
    for player in pool:
        birth_year = player.get("birthYear")
        if not isinstance(birth_year, int):
            birth_year = YOUNG_PLAYER_CANDIDATES.get(player["player"], {}).get("birthYear")
        if (
            player["player"] in YOUNG_PLAYER_CANDIDATES
            and isinstance(birth_year, int)
            and birth_year >= YOUNG_PLAYER_CUTOFF_YEAR
        ):
            young_pool.append(player)
    best_young = max(
        young_pool,
        key=lambda player: float(player["overall"]) + float(player["goals"]) * 3.0 + float(player["stageScore"]) * 3.0 + float(player["semiFinalProbability"]) * 30.0,
        default=None,
    )

    def boot_position_priority(position: str | None) -> int:
        normalized = str(position or "").upper()
        if normalized in {"ST", "CF"}:
            return 5
        if normalized in {"LW", "RW", "LF", "RF"}:
            return 4
        if normalized in {"CAM", "LAM", "RAM"}:
            return 3
        if normalized in {"LM", "RM", "CM"}:
            return 2
        if normalized == "CDM":
            return 1
        return 0

    def boot_sort_key(row: dict[str, Any]) -> tuple[int, int, int, int, str]:
        player_meta = player_lookup.get(_normalize_name(row.get("player")))
        position = (player_meta or {}).get("position") or row.get("position")
        family = _boot_position_family(position)
        family_priority = 2 if family == "ATT" else 1 if family == "MID" else 0
        return (
            int(row.get("goals", 0)),
            int(row.get("assists", 0)),
            -int(row.get("minutes", 9999)),
            family_priority * 10 + boot_position_priority(position),
            str(row.get("player", "")),
        )

    eligible_boot_rows = []
    for row in top_scorers:
        player_meta = player_lookup.get(_normalize_name(row.get("player")))
        position = (player_meta or {}).get("position") or row.get("position")
        if _boot_position_family(position) in {"ATT", "MID"}:
            eligible_boot_rows.append({**row, "position": position})

    if len(eligible_boot_rows) < 3:
        fallback_rows = []
        existing_names = {_normalize_name(row.get("player")) for row in eligible_boot_rows}
        for player in pool:
            if _boot_position_family(player.get("position")) not in {"ATT", "MID"}:
                continue
            normalized_name = _normalize_name(player.get("player"))
            if normalized_name in existing_names:
                continue
            fallback_rows.append(
                {
                    "player": player.get("player"),
                    "goals": int(player.get("goals", 0)),
                    "assists": 0,
                    "minutes": 9999,
                    "country": player.get("team"),
                    "position": player.get("position"),
                }
            )
        fallback_rows = sorted(fallback_rows, key=boot_sort_key, reverse=True)
        for row in fallback_rows:
            eligible_boot_rows.append(row)
            if len(eligible_boot_rows) >= 3:
                break

    attacking_boot_rows = [
        row for row in eligible_boot_rows
        if _boot_position_family(row.get("position")) == "ATT"
    ]
    midfield_boot_rows = [
        row for row in eligible_boot_rows
        if _boot_position_family(row.get("position")) == "MID"
    ]

    boot_podium = sorted(attacking_boot_rows, key=boot_sort_key, reverse=True)[:3]
    if len(boot_podium) < 3:
        midfield_fill = sorted(midfield_boot_rows, key=boot_sort_key, reverse=True)
        for row in midfield_fill:
            if len(boot_podium) >= 3:
                break
            boot_podium.append(row)
    boot_goal_floors = [6, 5, 4]

    def all_star_score(player: dict[str, Any]) -> float:
        return float(player["overall"]) + float(player["stageScore"]) * 4.0 + float(player["goals"]) * 2.0 + float(player["semiFinalProbability"]) * 25.0

    gk_team = sorted([player for player in pool if player["positionLabel"] == "GK"], key=all_star_score, reverse=True)[:1]
    def_team = sorted([player for player in pool if player["positionLabel"] == "DEF"], key=all_star_score, reverse=True)[:4]
    mid_team = sorted([player for player in pool if player["positionLabel"] == "MID"], key=all_star_score, reverse=True)[:3]
    att_team = sorted([player for player in pool if player["positionLabel"] == "ATT"], key=all_star_score, reverse=True)[:3]
    all_star_team = [
        {
            "player": player["player"],
            "team": player["team"],
            "position": player["position"],
            "overall": player["overall"],
        }
        for player in [*gk_team, *def_team, *mid_team, *att_team]
    ]

    return {
        "champion": champion,
        "goldenBall": _award_player(ball_podium[0] if len(ball_podium) > 0 else None),
        "silverBall": _award_player(ball_podium[1] if len(ball_podium) > 1 else None),
        "bronzeBall": _award_player(ball_podium[2] if len(ball_podium) > 2 else None),
        "goldenBoot": (
            {
                **(_boot_award_player(boot_podium[0], player_lookup) or {}),
                "goals": max(int(boot_podium[0].get("goals", 0)), boot_goal_floors[0]),
            }
            if len(boot_podium) > 0
            else None
        ),
        "silverBoot": (
            {
                **(_boot_award_player(boot_podium[1], player_lookup) or {}),
                "goals": max(int(boot_podium[1].get("goals", 0)), boot_goal_floors[1]),
            }
            if len(boot_podium) > 1
            else None
        ),
        "bronzeBoot": (
            {
                **(_boot_award_player(boot_podium[2], player_lookup) or {}),
                "goals": max(int(boot_podium[2].get("goals", 0)), boot_goal_floors[2]),
            }
            if len(boot_podium) > 2
            else None
        ),
        "goldenGlove": _award_player(glove_winner),
        "bestYoungPlayer": _award_player(best_young),
        "allStarTeam": all_star_team,
    }


def run_tournament_simulation(
    teams_df: pd.DataFrame,
    groups_payload: list[dict[str, Any]],
    players_df: pd.DataFrame,
    starting_lineups: list[dict[str, Any]],
    iterations: int,
) -> dict[str, Any]:
    rng = np.random.default_rng()
    team_records = teams_df.to_dict(orient="records")
    team_names = [row["team_name"] for row in team_records]
    team_name_to_idx = {name: idx for idx, name in enumerate(team_names)}
    fifa_ranks = teams_df["fifa_rank"].to_numpy(dtype=np.int16)
    attack_strengths = teams_df["attack_strength"].to_numpy(dtype=np.float32)
    defense_strengths = teams_df["defense_strength"].to_numpy(dtype=np.float32)
    overall_strengths = teams_df["overall_strength"].to_numpy(dtype=np.float32)
    attack_ratings = teams_df["attack_rating"].to_numpy(dtype=np.float32)
    squad_ratings = teams_df["squad_rating"].to_numpy(dtype=np.float32)

    group_indices = [
        [team_name_to_idx[name] for name in group["teams"]]
        for group in groups_payload
    ]
    progress = np.zeros((len(team_records), 7), dtype=np.int32)
    scorelines = Counter()

    for run in range(iterations):
        group_rows: list[tuple[int, int, int, int, int, str]] = []

        for group_payload, indices in zip(groups_payload, group_indices):
            points = np.zeros(len(team_records), dtype=np.int16)
            goal_difference = np.zeros(len(team_records), dtype=np.int16)
            goals_for = np.zeros(len(team_records), dtype=np.int16)

            for home_idx, away_idx in combinations(indices, 2):
                home_goals, away_goals, _ = _simulate_match_fast(
                    home_idx,
                    away_idx,
                    attack_strengths,
                    attack_ratings,
                    squad_ratings,
                    overall_strengths,
                    defense_strengths,
                    rng,
                    knockout=False,
                )
                goal_difference[home_idx] += home_goals - away_goals
                goal_difference[away_idx] += away_goals - home_goals
                goals_for[home_idx] += home_goals
                goals_for[away_idx] += away_goals
                if home_goals > away_goals:
                    points[home_idx] += 3
                elif away_goals > home_goals:
                    points[away_idx] += 3
                else:
                    points[home_idx] += 1
                    points[away_idx] += 1

            ordered = _sort_group_rows(indices, points, goal_difference, goals_for, fifa_ranks, rng)
            for placement, idx in enumerate(ordered, start=1):
                group_rows.append((idx, placement, int(points[idx]), int(goal_difference[idx]), int(goals_for[idx]), group_payload["group"]))
                if placement <= 2:
                    progress[idx, 0] += 1

        third_sorted = sorted(
            [row for row in group_rows if row[1] == 3],
            key=lambda row: (row[2], row[3], row[4], -int(fifa_ranks[row[0]])),
            reverse=True,
        )
        for idx, *_ in third_sorted[:8]:
            progress[idx, 0] += 1

        seeds = _build_round_of_32_indices(group_rows, fifa_ranks)
        for idx in seeds:
            progress[idx, 1] += 1

        round_of_32_winners: list[int] = []
        for home_idx, away_idx in zip(seeds[::2], seeds[1::2]):
            _, _, winner_idx = _simulate_match_fast(
                home_idx,
                away_idx,
                attack_strengths,
                attack_ratings,
                squad_ratings,
                overall_strengths,
                defense_strengths,
                rng,
                knockout=True,
            )
            round_of_32_winners.append(winner_idx)
            progress[winner_idx, 2] += 1

        round_of_16 = [round_of_32_winners[idx] for idx in ROUND_OF_16_REORDER]

        quarterfinals: list[int] = []
        for home_idx, away_idx in zip(round_of_16[::2], round_of_16[1::2]):
            _, _, winner_idx = _simulate_match_fast(
                home_idx,
                away_idx,
                attack_strengths,
                attack_ratings,
                squad_ratings,
                overall_strengths,
                defense_strengths,
                rng,
                knockout=True,
            )
            quarterfinals.append(winner_idx)
            progress[winner_idx, 3] += 1

        semifinals: list[int] = []
        for home_idx, away_idx in zip(quarterfinals[::2], quarterfinals[1::2]):
            _, _, winner_idx = _simulate_match_fast(
                home_idx,
                away_idx,
                attack_strengths,
                attack_ratings,
                squad_ratings,
                overall_strengths,
                defense_strengths,
                rng,
                knockout=True,
            )
            semifinals.append(winner_idx)
            progress[winner_idx, 4] += 1

        finalists: list[int] = []
        for home_idx, away_idx in zip(semifinals[::2], semifinals[1::2]):
            _, _, winner_idx = _simulate_match_fast(
                home_idx,
                away_idx,
                attack_strengths,
                attack_ratings,
                squad_ratings,
                overall_strengths,
                defense_strengths,
                rng,
                knockout=True,
            )
            finalists.append(winner_idx)
            progress[winner_idx, 5] += 1

        final_home_goals, final_away_goals, champion_idx = _simulate_match_fast(
            finalists[0],
            finalists[1],
            attack_strengths,
            attack_ratings,
            squad_ratings,
            overall_strengths,
            defense_strengths,
            rng,
            knockout=True,
        )
        progress[champion_idx, 6] += 1
        scorelines[f"{final_home_goals}-{final_away_goals}"] += 1

    probabilities = []
    for idx, team_name in enumerate(team_names):
        probabilities.append(
            {
                "team": team_name,
                "groupAdvancementProbability": float(round(progress[idx, 0] / iterations, 4)),
                "roundOf32Probability": float(round(progress[idx, 1] / iterations, 4)),
                "roundOf16Probability": float(round(progress[idx, 2] / iterations, 4)),
                "quarterFinalProbability": float(round(progress[idx, 3] / iterations, 4)),
                "semiFinalProbability": float(round(progress[idx, 4] / iterations, 4)),
                "finalProbability": float(round(progress[idx, 5] / iterations, 4)),
                "championProbability": float(round(progress[idx, 6] / iterations, 4)),
            }
        )
    probabilities.sort(key=lambda row: row["championProbability"], reverse=True)
    sample_bracket, group_snapshots, top_scorers = _representative_sample_bracket(
        teams_df,
        groups_payload,
        players_df,
        starting_lineups,
        probabilities,
    )
    awards = _generate_awards(starting_lineups, probabilities, sample_bracket, top_scorers)

    common_scorelines = [
        {"scoreline": scoreline, "probability": round(count / iterations, 4)}
        for scoreline, count in scorelines.most_common(10)
    ]

    return {
        "iterations": iterations,
        "simulationRunId": uuid4().hex,
        "probabilities": probabilities,
        "mostCommonScorelines": common_scorelines,
        "sampleBracket": sample_bracket,
        "topScorers": top_scorers,
        "awards": awards,
        "groups": group_snapshots,
        "format": "48-team / 12 groups / Round of 32",
    }
