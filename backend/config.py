from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


@dataclass(frozen=True)
class Settings:
    api_football_key: str = os.getenv("API_FOOTBALL_KEY", "")
    api_football_base_url: str = os.getenv(
        "API_FOOTBALL_BASE_URL", "https://v3.football.api-sports.io"
    )
    cache_ttl_hours: int = int(os.getenv("CACHE_TTL_HOURS", "168"))
    team_data_source: str = os.getenv("TEAM_DATA_SOURCE", "sample")
    cache_dir: Path = BASE_DIR / "data" / "cache"


settings = Settings()
