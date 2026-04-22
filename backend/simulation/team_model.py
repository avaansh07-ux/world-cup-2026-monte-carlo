from __future__ import annotations

from typing import Any

import numpy as np


def expected_goals(team: dict[str, Any], opponent: dict[str, Any]) -> float:
    attack = team["attack"] * team["form"]
    defense_resistance = max(opponent["defense"], 0.45)
    rating_factor = team["rating"] / 85
    return max(0.2, attack * rating_factor / defense_resistance)


def simulate_score(team: dict[str, Any], opponent: dict[str, Any], rng: np.random.Generator) -> int:
    lam = expected_goals(team, opponent)
    return int(rng.poisson(lam))


def win_probability_snapshot(results: dict[str, Any], total_runs: int) -> list[dict[str, Any]]:
    probabilities = []
    for team_name, progress in results.items():
        probabilities.append(
            {
                "team": team_name,
                "winProbability": round(progress["champion"] / total_runs, 4),
                "finalProbability": round(progress["final"] / total_runs, 4),
                "semiProbability": round(progress["semi"] / total_runs, 4),
            }
        )
    return sorted(probabilities, key=lambda row: row["winProbability"], reverse=True)
