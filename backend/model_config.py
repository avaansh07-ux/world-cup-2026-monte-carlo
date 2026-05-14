from __future__ import annotations

from dataclasses import dataclass

try:
    from backend.models.static_data import load_model_weights
except ModuleNotFoundError:
    from models.static_data import load_model_weights


@dataclass(frozen=True)
class ModelWeights:
    fifa_rank: float
    squad_quality: float
    attacking_quality: float
    defensive_quality: float
    recent_form: float


@dataclass(frozen=True)
class SimulationConfig:
    weights: ModelWeights
    home_advantage: float = 0.06
    variance: float = 0.11
    default_iterations: int = 1000
    max_iterations: int = 50000
    scorer_weight_goal: float = 0.40
    scorer_weight_shooting: float = 0.24
    scorer_weight_overall: float = 0.16
    scorer_weight_minutes: float = 0.10
    scorer_weight_position: float = 0.10


def _load_weights() -> ModelWeights:
    raw = load_model_weights()
    return ModelWeights(
        fifa_rank=float(raw["fifa_ranking_weight"]),
        squad_quality=float(raw["squad_rating_weight"]),
        attacking_quality=float(raw["attack_weight"]),
        defensive_quality=float(raw["defense_weight"]),
        recent_form=float(raw["form_weight"]),
    )


SIMULATION_CONFIG = SimulationConfig(weights=_load_weights())
