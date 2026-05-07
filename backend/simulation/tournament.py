from __future__ import annotations

from collections import Counter, defaultdict
from itertools import combinations
from typing import Any

import numpy as np

try:
    from .team_model import simulate_score, win_probability_snapshot
except ImportError:
    from simulation.team_model import simulate_score, win_probability_snapshot


def _group_table(teams: list[dict[str, Any]], rng: np.random.Generator) -> list[dict[str, Any]]:
    table = {
        team["name"]: {
            "team": team,
            "points": 0,
            "goal_diff": 0,
            "goals_for": 0,
        }
        for team in teams
    }

    for home, away in combinations(teams, 2):
        home_goals = simulate_score(home, away, rng)
        away_goals = simulate_score(away, home, rng)
        table[home["name"]]["goal_diff"] += home_goals - away_goals
        table[away["name"]]["goal_diff"] += away_goals - home_goals
        table[home["name"]]["goals_for"] += home_goals
        table[away["name"]]["goals_for"] += away_goals

        if home_goals > away_goals:
            table[home["name"]]["points"] += 3
        elif away_goals > home_goals:
            table[away["name"]]["points"] += 3
        else:
            table[home["name"]]["points"] += 1
            table[away["name"]]["points"] += 1

    ordered = sorted(
        table.values(),
        key=lambda row: (row["points"], row["goal_diff"], row["goals_for"]),
        reverse=True,
    )
    return ordered


def _knockout_winner(
    team_a: dict[str, Any], team_b: dict[str, Any], rng: np.random.Generator
) -> tuple[dict[str, Any], tuple[int, int]]:
    goals_a = simulate_score(team_a, team_b, rng)
    goals_b = simulate_score(team_b, team_a, rng)
    if goals_a == goals_b:
        extra_a = int(rng.binomial(1, 0.38))
        extra_b = int(rng.binomial(1, 0.33))
        goals_a += extra_a
        goals_b += extra_b
    if goals_a == goals_b:
        winner = team_a if rng.random() > 0.5 else team_b
    else:
        winner = team_a if goals_a > goals_b else team_b
    return winner, (goals_a, goals_b)


def simulate_tournament(teams: list[dict[str, Any]], iterations: int = 10000) -> dict[str, Any]:
    rng = np.random.default_rng()
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for team in teams:
        groups[team["group"]].append(team)

    progress = {
        team["name"]: {"semi": 0, "final": 0, "champion": 0}
        for team in teams
    }
    finals_counter: Counter[str] = Counter()
    scoreline_counter: Counter[str] = Counter()
    bracket_example: list[dict[str, Any]] = []

    for attempt in range(iterations):
        qualifiers: list[dict[str, Any]] = []
        for group_teams in groups.values():
            table = _group_table(group_teams, rng)
            qualifiers.extend([table[0]["team"], table[1]["team"]])

        quarter_pairs = list(zip(qualifiers[::2], qualifiers[1::2]))
        semifinalists = []
        current_bracket = []
        for team_a, team_b in quarter_pairs:
            winner, score = _knockout_winner(team_a, team_b, rng)
            semifinalists.append(winner)
            current_bracket.append(
                {
                    "round": "Quarter-final",
                    "home": team_a["name"],
                    "away": team_b["name"],
                    "score": f"{score[0]}-{score[1]}",
                    "winner": winner["name"],
                }
            )

        for team in semifinalists:
            progress[team["name"]]["semi"] += 1

        finalists = []
        for team_a, team_b in zip(semifinalists[::2], semifinalists[1::2]):
            winner, score = _knockout_winner(team_a, team_b, rng)
            finalists.append(winner)
            current_bracket.append(
                {
                    "round": "Semi-final",
                    "home": team_a["name"],
                    "away": team_b["name"],
                    "score": f"{score[0]}-{score[1]}",
                    "winner": winner["name"],
                }
            )

        for team in finalists:
            progress[team["name"]]["final"] += 1
            finals_counter[team["name"]] += 1

        champion, score = _knockout_winner(finalists[0], finalists[1], rng)
        progress[champion["name"]]["champion"] += 1
        scoreline_counter[f"{score[0]}-{score[1]}"] += 1
        current_bracket.append(
            {
                "round": "Final",
                "home": finalists[0]["name"],
                "away": finalists[1]["name"],
                "score": f"{score[0]}-{score[1]}",
                "winner": champion["name"],
            }
        )

        if attempt == 0:
            bracket_example = current_bracket

    return {
        "iterations": iterations,
        "probabilities": win_probability_snapshot(progress, iterations),
        "scorelines": [
            {"score": score, "probability": round(count / iterations, 4)}
            for score, count in scoreline_counter.most_common(8)
        ],
        "finalists": [
            {"team": team, "probability": round(count / iterations, 4)}
            for team, count in finals_counter.most_common()
        ],
        "bracketExample": bracket_example,
    }
