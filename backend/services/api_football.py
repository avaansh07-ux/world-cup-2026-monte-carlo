from __future__ import annotations

from typing import Any

import requests

from config import settings


class APIFootballClient:
    def __init__(self) -> None:
        self.base_url = settings.api_football_base_url.rstrip("/")

    def get(self, endpoint: str, params: dict[str, Any]) -> dict[str, Any]:
        if not settings.api_football_key:
            raise RuntimeError("API_FOOTBALL_KEY is not configured.")

        response = requests.get(
            f"{self.base_url}{endpoint}",
            params=params,
            headers={"x-apisports-key": settings.api_football_key},
            timeout=30,
        )
        response.raise_for_status()
        return response.json()
