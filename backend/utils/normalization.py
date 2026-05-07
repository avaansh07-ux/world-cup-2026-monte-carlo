from __future__ import annotations


def min_max_scale(value: float, minimum: float, maximum: float, inverse: bool = False) -> float:
    if maximum == minimum:
        return 0.5
    scaled = (value - minimum) / (maximum - minimum)
    scaled = max(0.0, min(1.0, scaled))
    return 1 - scaled if inverse else scaled
