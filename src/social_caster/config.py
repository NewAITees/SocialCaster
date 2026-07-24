"""Environment-backed application configuration."""

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    buffer_api_key: str
    instagram_channel_id: str
    x_channel_id: str
    poll_interval_seconds: int = 300
    database_path: Path = Path("database/posts.db")
    log_path: Path = Path("logs/social-caster.log")

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            buffer_api_key=_required("BUFFER_API_KEY"),
            instagram_channel_id=_required("BUFFER_INSTAGRAM_CHANNEL_ID"),
            x_channel_id=_required("BUFFER_X_CHANNEL_ID"),
            poll_interval_seconds=int(os.getenv("POLL_INTERVAL_SECONDS", "300")),
            database_path=Path(os.getenv("DATABASE_PATH", "database/posts.db")),
            log_path=Path(os.getenv("LOG_PATH", "logs/social-caster.log")),
        )


def _required(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise ValueError(f"必須環境変数が未設定です: {name}")
    return value
