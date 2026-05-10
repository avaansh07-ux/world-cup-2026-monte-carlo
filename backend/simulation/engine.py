from __future__ import annotations

from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path
from typing import Any
from uuid import uuid4

import numpy as np
import pandas as pd

from backend.model_config import SIMULATION_CONFIG

YOUNG_PLAYER_CANDIDATES = {
    "Lamine Yamal": {"team": "Spain", "position": "Forward"},
    "Désiré Doué": {"team": "France", "position": "Forward"},
    "Kendry Páez": {"team": "Ecuador", "position": "Forward"},
    "Kenan Yıldız": {"team": "Turkiye", "position": "Forward"},
    "Arda Güler": {"team": "Turkiye", "position": "Midfielder"},
    "Antonio Nusa": {"team": "Norway", "position": "Forward"},
    "Dário Essugo": {"team": "Portugal", "position": "Midfielder"},
}

YOUNG_PLAYER_CUTOFF_YEAR = 2005
_BIRTH_YEAR_LOOKUP: dict[str, int] | None = None


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


def _generate_sample_bracket(
    teams_df: pd.DataFrame,
    groups_payload: list[dict[str, Any]],
    players_df: pd.DataFrame,
    rng: np.random.Generator,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    team_lookup = {row["team_name"]: row for row in teams_df.to_dict(orient="records")}
    scorer_counter: Counter[str] = Counter()
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
            for scorer in match.get("scorers", []):
                scorer_counter[scorer] += 1
        for placement, row in enumerate(table, start=1):
            group_results.append({**row, "group": group_name, "placement": placement})

    round_of_32 = _seed_knockout(group_results)
    round_of_16, bracket_rows = _play_knockout_round(round_of_32, players_df, rng, "Round of 32", scorer_counter)
    current_bracket.extend(bracket_rows)
    quarterfinals, bracket_rows = _play_knockout_round(round_of_16, players_df, rng, "Round of 16", scorer_counter)
    current_bracket.extend(bracket_rows)
    semifinals, bracket_rows = _play_knockout_round(quarterfinals, players_df, rng, "Quarter-final", scorer_counter)
    current_bracket.extend(bracket_rows)
    finalists, bracket_rows = _play_knockout_round(semifinals, players_df, rng, "Semi-final", scorer_counter)
    current_bracket.extend(bracket_rows)

    final_result = simulate_match(finalists[0], finalists[1], players_df, rng, knockout=True)
    current_bracket.append({"round": "Final", **final_result})
    for scorer in final_result["scorers"]:
        scorer_counter[scorer] += 1

    player_lookup = players_df.drop_duplicates("short_name").set_index("short_name").to_dict(orient="index")
    top_scorers = []
    for player, goals in scorer_counter.most_common(15):
        meta = player_lookup.get(player, {})
        top_scorers.append(
            {
                "player": player,
                "goals": goals,
                "country": meta.get("national_team", "Unknown"),
                "position": meta.get("position", "ATT"),
                "image_url": meta.get("image_url"),
                "image_path": meta.get("image_path"),
                "headshot_path": meta.get("headshot_path"),
            }
        )

    return current_bracket, current_groups, top_scorers


def _position_family(position: str | None) -> str:
    normalized = str(position or "").upper()
    if normalized == "GK":
        return "GK"
    if normalized in {"CB", "LB", "RB", "LWB", "RWB", "LCB", "RCB"}:
        return "DEF"
    if normalized in {"CDM", "CM", "CAM", "LM", "RM"}:
        return "MID"
    return "ATT"


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
    scorer_lookup = {entry["player"]: entry for entry in top_scorers}
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
            scorer_meta = scorer_lookup.get(player.get("name"), {})
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
    lineup_meta = player_lookup.get(player_name or "", {})

    return {
        "player": player_name,
        "team": lineup_meta.get("team") or scorer_row.get("country"),
        "position": lineup_meta.get("position") or scorer_row.get("position"),
        "overall": lineup_meta.get("overall"),
        "goals": scorer_row.get("goals"),
    }


def _generate_awards(
    starting_lineups: list[dict[str, Any]],
    probabilities: list[dict[str, Any]],
    sample_bracket: list[dict[str, Any]],
    top_scorers: list[dict[str, Any]],
) -> dict[str, Any]:
    pool, stage_lookup, champion = _candidate_pool(starting_lineups, probabilities, sample_bracket, top_scorers)
    player_lookup = {entry["player"]: entry for entry in pool}

    def ball_score(player: dict[str, Any]) -> float:
        return (
            float(player["overall"]) * 1.0
            + float(player["goals"]) * 5.0
            + float(player["stageScore"]) * 4.0
            + float(player["championProbability"]) * 100.0
            + float(player["finalProbability"]) * 35.0
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
        if normalized in {"CDM", "LWB", "RWB", "LB", "RB"}:
            return 1
        return 0

    boot_podium = sorted(
        top_scorers,
        key=lambda row: (
            int(row.get("goals", 0)),
            boot_position_priority(row.get("position")),
            row.get("player", ""),
        ),
        reverse=True,
    )[:3]

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
        "goldenBoot": _boot_award_player(boot_podium[0] if len(boot_podium) > 0 else None, player_lookup),
        "silverBoot": _boot_award_player(boot_podium[1] if len(boot_podium) > 1 else None, player_lookup),
        "bronzeBoot": _boot_award_player(boot_podium[2] if len(boot_podium) > 2 else None, player_lookup),
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
        group_rows: list[tuple[int, int, int, int, int]] = []

        for indices in group_indices:
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
                group_rows.append((idx, placement, int(points[idx]), int(goal_difference[idx]), int(goals_for[idx])))
                if placement <= 2:
                    progress[idx, 0] += 1

        third_sorted = sorted(
            [row for row in group_rows if row[1] == 3],
            key=lambda row: (row[2], row[3], row[4], -int(fifa_ranks[row[0]]), float(rng.random())),
            reverse=True,
        )
        for idx, *_ in third_sorted[:8]:
            progress[idx, 0] += 1

        winners = sorted(
            [row for row in group_rows if row[1] == 1],
            key=lambda row: (row[2], row[3], row[4], -int(fifa_ranks[row[0]])),
            reverse=True,
        )
        runners_up = sorted(
            [row for row in group_rows if row[1] == 2],
            key=lambda row: (row[2], row[3], row[4], -int(fifa_ranks[row[0]])),
            reverse=True,
        )
        seeds = [idx for idx, *_ in winners + runners_up + third_sorted[:8]]
        for idx in seeds:
            progress[idx, 1] += 1

        round_of_16: list[int] = []
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
            round_of_16.append(winner_idx)
            progress[winner_idx, 2] += 1

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

    sample_bracket, group_snapshots, top_scorers = _generate_sample_bracket(
        teams_df,
        groups_payload,
        players_df,
        np.random.default_rng(),
    )

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
