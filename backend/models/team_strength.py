from __future__ import annotations

import pandas as pd

from backend.model_config import SIMULATION_CONFIG
from backend.utils.normalization import min_max_scale


POSITION_GROUPS = {
    "GK": "goalkeeper",
    "CB": "defense",
    "LB": "defense",
    "RB": "defense",
    "LWB": "defense",
    "RWB": "defense",
    "CDM": "midfield",
    "CM": "midfield",
    "CAM": "midfield",
    "LM": "midfield",
    "RM": "midfield",
    "LW": "attack",
    "RW": "attack",
    "ST": "attack",
    "CF": "attack",
}

TOP_FIVE_LEAGUES = {"Premier League", "La Liga", "Bundesliga", "Serie A", "Ligue 1"}
ELITE_TEAMS = {"France", "England", "Spain", "Argentina", "Brazil", "Portugal", "Germany", "Netherlands"}
CONTENDER_TEAMS = ELITE_TEAMS | {"Belgium", "Uruguay", "Croatia", "Colombia"}
DARK_HORSE_TEAMS = {"Morocco", "Senegal", "Switzerland", "Japan"}


def _position_frame(players: pd.DataFrame) -> pd.DataFrame:
    frame = players.copy()
    frame["position_group"] = frame["position"].map(POSITION_GROUPS).fillna("midfield")
    frame["top_five_bonus"] = frame["league"].isin(TOP_FIVE_LEAGUES).astype(float) * 3.0
    frame["form_contribution"] = (
        frame["overall"] * 0.55
        + frame["top_five_bonus"]
        + frame["pace"] * 0.05
        + frame["passing"] * 0.08
        + frame["dribbling"] * 0.08
        + frame["shooting"] * 0.06
    )
    frame["attack_contribution"] = (
        frame["shooting"] * 0.34
        + frame["pace"] * 0.18
        + frame["dribbling"] * 0.16
        + frame["passing"] * 0.12
        + frame["overall"] * 0.18
        + frame["top_five_bonus"] * 0.2
    )
    frame["midfield_contribution"] = (
        frame["passing"] * 0.30
        + frame["dribbling"] * 0.18
        + frame["physic"] * 0.12
        + frame["defending"] * 0.10
        + frame["overall"] * 0.22
        + frame["top_five_bonus"] * 0.25
    )
    frame["defense_contribution"] = (
        frame["defending"] * 0.33
        + frame["physic"] * 0.16
        + frame["passing"] * 0.08
        + frame["overall"] * 0.20
        + frame["top_five_bonus"] * 0.20
    )
    frame["goalkeeper_contribution"] = frame["overall"] * 0.75 + frame["physic"] * 0.08
    return frame


def _safe_mean(series: pd.Series, fallback: float) -> float:
    return float(series.mean()) if not series.empty else fallback


def calculate_team_profiles(teams_df: pd.DataFrame, players_df: pd.DataFrame) -> pd.DataFrame:
    players = _position_frame(players_df)
    team_rows = []

    fifa_points_min = teams_df["fifa_points"].min()
    fifa_points_max = teams_df["fifa_points"].max()
    form_min = players["form_contribution"].min()
    form_max = players["form_contribution"].max()

    for team in teams_df.to_dict(orient="records"):
        squad = players[players["national_team"] == team["team_name"]]
        if squad.empty:
            continue

        base_rating = float(team["base_rating"])
        attack_rating = _safe_mean(
            squad[squad["position_group"] == "attack"]["attack_contribution"],
            base_rating,
        )
        midfield_rating = _safe_mean(
            squad[squad["position_group"] == "midfield"]["midfield_contribution"],
            base_rating,
        )
        defense_rating = _safe_mean(
            squad[squad["position_group"] == "defense"]["defense_contribution"],
            base_rating,
        )
        goalkeeper_rating = _safe_mean(
            squad[squad["position_group"] == "goalkeeper"]["goalkeeper_contribution"],
            base_rating - 2,
        )
        squad_rating = _safe_mean(squad["overall"], base_rating)
        form_score_raw = _safe_mean(squad["form_contribution"], base_rating)
        ranking_score = min_max_scale(team["fifa_points"], fifa_points_min, fifa_points_max, inverse=False)

        attack_component = ((attack_rating + midfield_rating) / 2) / 100
        defense_component = ((defense_rating + goalkeeper_rating) / 2) / 100
        squad_component = squad_rating / 100
        form_component = min_max_scale(form_score_raw, form_min, form_max)
        if team["team_name"] in ELITE_TEAMS:
            pedigree_component = 0.16
        elif team["team_name"] in CONTENDER_TEAMS:
            pedigree_component = 0.03
        elif team["team_name"] in DARK_HORSE_TEAMS:
            pedigree_component = -0.02
        else:
            pedigree_component = -0.11

        weights = SIMULATION_CONFIG.weights
        overall_strength = (
            ranking_score * weights.fifa_rank
            + squad_component * weights.squad_quality
            + attack_component * weights.attacking_quality
            + defense_component * weights.defensive_quality
            + form_component * weights.recent_form
            + pedigree_component
        )

        team_rows.append(
            {
                **team,
                "squad_rating": round(squad_rating, 2),
                "attack_rating": round(attack_rating, 2),
                "midfield_rating": round(midfield_rating, 2),
                "defense_rating": round(defense_rating, 2),
                "goalkeeper_rating": round(goalkeeper_rating, 2),
                "form_score": round(form_component, 3),
                "ranking_score": round(ranking_score, 3),
                "attack_strength": round(0.86 + attack_component + overall_strength * 1.15, 3),
                "defense_strength": round(0.9 + defense_component + overall_strength * 1.08, 3),
                "overall_strength": round(overall_strength, 3),
            }
        )

    return pd.DataFrame(team_rows)
