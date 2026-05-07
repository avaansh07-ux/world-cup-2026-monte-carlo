from __future__ import annotations

from collections import Counter, defaultdict
from itertools import combinations
from typing import Any
from uuid import uuid4

import numpy as np
import pandas as pd

from backend.model_config import SIMULATION_CONFIG


def _scorer_weights(players: pd.DataFrame) -> pd.Series:
    position_bonus = players["position"].map({"ST": 1.2, "CF": 1.15, "LW": 1.0, "RW": 1.0, "CAM": 0.75, "CM": 0.45, "CB": 0.18, "GK": 0.01}).fillna(0.3)
    weights = (
        players["shooting"] * SIMULATION_CONFIG.scorer_weight_shooting
        + players["overall"] * SIMULATION_CONFIG.scorer_weight_overall
        + players["pace"] * 0.04
        + players["passing"] * 0.02
        + position_bonus * 16 * SIMULATION_CONFIG.scorer_weight_position
    )
    return weights.clip(lower=0.01)


def expected_goals(team: dict[str, Any], opponent: dict[str, Any], rng: np.random.Generator) -> float:
    variance = rng.normal(1.0, SIMULATION_CONFIG.variance)
    strength_edge = team["overall_strength"] - opponent["overall_strength"]
    mean = (
        team["attack_strength"] * 0.96
        + (team["attack_rating"] / 100) * 0.52
        + (team["squad_rating"] / 100) * 0.34
        + team["overall_strength"] * 0.62
        + strength_edge * 0.55
        - opponent["defense_strength"] * 0.68
        - opponent["overall_strength"] * 0.18
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
    for team_name, goal_count in ((team_a["team_name"], goals_a), (team_b["team_name"], goals_b)):
        team_players = players_df[(players_df["national_team"] == team_name) & (players_df["is_available"] == True)]
        if team_players.empty or goal_count == 0:
            continue
        weights = _scorer_weights(team_players)
        sampled = rng.choice(
            team_players["short_name"].tolist(),
            size=goal_count,
            replace=True,
            p=(weights / weights.sum()),
        )
        scorers.extend(sampled.tolist())

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
        "regularTime": {"homeGoals": regular_a, "awayGoals": regular_b},
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


def _seed_knockout(group_results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    winners = sorted(
        [row for row in group_results if row["placement"] == 1],
        key=lambda row: (row["points"], row["goal_difference"], row["goals_for"], -row["team"]["fifa_rank"]),
        reverse=True,
    )
    runners_up = sorted(
        [row for row in group_results if row["placement"] == 2],
        key=lambda row: (row["points"], row["goal_difference"], row["goals_for"], -row["team"]["fifa_rank"]),
        reverse=True,
    )
    third_place = sorted(
        [row for row in group_results if row["placement"] == 3],
        key=lambda row: (row["points"], row["goal_difference"], row["goals_for"], -row["team"]["fifa_rank"]),
        reverse=True,
    )[:8]
    seeds = winners + runners_up + third_place
    return [row["team"] for row in seeds]


def _play_knockout_round(
    teams: list[dict[str, Any]],
    players_df: pd.DataFrame,
    rng: np.random.Generator,
    round_name: str,
    scorer_counter: Counter[str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    winners = []
    bracket_rows = []
    for home, away in zip(teams[::2], teams[1::2]):
        result = simulate_match(home, away, players_df, rng, knockout=True)
        winners.append(home if result["winner"] == home["team_name"] else away)
        bracket_rows.append({"round": round_name, **result})
        for scorer in result["scorers"]:
            scorer_counter[scorer] += 1
    return winners, bracket_rows


def run_tournament_simulation(
    teams_df: pd.DataFrame,
    groups_payload: list[dict[str, Any]],
    players_df: pd.DataFrame,
    iterations: int,
) -> dict[str, Any]:
    rng = np.random.default_rng()
    team_lookup = {row["team_name"]: row for row in teams_df.to_dict(orient="records")}
    progress = defaultdict(lambda: defaultdict(int))
    scorelines = Counter()
    scorers = Counter()
    sample_bracket = []
    group_snapshots = []
    sample_index = int(rng.integers(0, max(iterations, 1)))
    player_lookup = players_df.drop_duplicates("short_name").set_index("short_name").to_dict(orient="index")

    group_map = {group["group"]: [team_lookup[name] for name in group["teams"]] for group in groups_payload}

    for run in range(iterations):
        group_results = []
        current_bracket = []
        current_groups = []

        for group_name, group_teams in group_map.items():
            table, _ = _group_table(group_teams, players_df, rng)
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
            for placement, row in enumerate(table, start=1):
                enriched = {**row, "group": group_name, "placement": placement}
                group_results.append(enriched)
                if placement <= 2:
                    progress[row["team"]["team_name"]]["group"] += 1

        third_sorted = sorted(
            [row for row in group_results if row["placement"] == 3],
            key=lambda row: (row["points"], row["goal_difference"], row["goals_for"], -row["team"]["fifa_rank"]),
            reverse=True,
        )
        for row in third_sorted[:8]:
            progress[row["team"]["team_name"]]["group"] += 1

        round_of_32 = _seed_knockout(group_results)
        for team in round_of_32:
            progress[team["team_name"]]["roundOf32"] += 1

        round_of_16, bracket_rows = _play_knockout_round(round_of_32, players_df, rng, "Round of 32", scorers)
        current_bracket.extend(bracket_rows)
        for team in round_of_16:
            progress[team["team_name"]]["roundOf16"] += 1

        quarterfinals, bracket_rows = _play_knockout_round(round_of_16, players_df, rng, "Round of 16", scorers)
        current_bracket.extend(bracket_rows)
        for team in quarterfinals:
            progress[team["team_name"]]["quarter"] += 1

        semifinals, bracket_rows = _play_knockout_round(quarterfinals, players_df, rng, "Quarter-final", scorers)
        current_bracket.extend(bracket_rows)
        for team in semifinals:
            progress[team["team_name"]]["semi"] += 1

        finalists, bracket_rows = _play_knockout_round(semifinals, players_df, rng, "Semi-final", scorers)
        current_bracket.extend(bracket_rows)
        for team in finalists:
            progress[team["team_name"]]["final"] += 1

        final_result = simulate_match(finalists[0], finalists[1], players_df, rng, knockout=True)
        champion = final_result["winner"]
        progress[champion]["champion"] += 1
        current_bracket.append({"round": "Final", **final_result})
        scorelines[f'{final_result["homeGoals"]}-{final_result["awayGoals"]}'] += 1
        for scorer in final_result["scorers"]:
            scorers[scorer] += 1

        if run == sample_index:
            sample_bracket = current_bracket
            group_snapshots = current_groups

    probabilities = []
    for team_name in teams_df["team_name"].tolist():
        row = progress[team_name]
        probabilities.append(
            {
                "team": team_name,
                "groupAdvancementProbability": round(row["group"] / iterations, 4),
                "roundOf32Probability": round(row["roundOf32"] / iterations, 4),
                "roundOf16Probability": round(row["roundOf16"] / iterations, 4),
                "quarterFinalProbability": round(row["quarter"] / iterations, 4),
                "semiFinalProbability": round(row["semi"] / iterations, 4),
                "finalProbability": round(row["final"] / iterations, 4),
                "championProbability": round(row["champion"] / iterations, 4),
            }
        )
    probabilities.sort(key=lambda row: row["championProbability"], reverse=True)

    top_scorers = []
    for player, goals in scorers.most_common(15):
        meta = player_lookup.get(player, {})
        team_name = meta.get("national_team", "Unknown")
        position = meta.get("position", "ATT")
        top_scorers.append(
            {
                "player": player,
                "goals": goals,
                "country": team_name,
                "position": position,
                "image_url": meta.get("image_url"),
                "image_path": meta.get("image_path"),
                "headshot_path": meta.get("headshot_path"),
            }
        )
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
        "groups": group_snapshots,
        "format": "48-team / 12 groups / Round of 32",
    }
