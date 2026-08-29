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
    enable_twitter: bool = True

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            buffer_api_key=_required("BUFFER_API_KEY"),
            instagram_channel_id=_required("BUFFER_INSTAGRAM_CHANNEL_ID"),
            x_channel_id=_required("BUFFER_X_CHANNEL_ID"),
            poll_interval_seconds=int(os.getenv("POLL_INTERVAL_SECONDS", "300")),
            database_path=Path(os.getenv("DATABASE_PATH", "database/posts.db")),
            log_path=Path(os.getenv("LOG_PATH", "logs/social-caster.log")),
            enable_twitter=os.getenv("ENABLE_TWITTER", "true").strip().lower()
            not in {"false", "0", "no"},
        )


def load_dotenv(path: Path | None = None) -> None:
    """Load simple KEY=VALUE entries without overriding process variables."""
    dotenv_path = path or Path(__file__).resolve().parents[2] / ".env"
    if not dotenv_path.is_file():
        return
    for raw_line in dotenv_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        name = name.strip()
        value = value.strip()
        if not name or name.startswith("export "):
            name = name.removeprefix("export ").strip()
        if not name or name in os.environ:
            continue
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        os.environ[name] = value


def _required(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise ValueError(f"必須環境変数が未設定です: {name}")
    return value
