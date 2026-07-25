import os
from pathlib import Path

import pytest

from social_caster.config import Settings, load_dotenv


def test_settings_load_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BUFFER_API_KEY", "key")
    monkeypatch.setenv("BUFFER_INSTAGRAM_CHANNEL_ID", "instagram")
    monkeypatch.setenv("BUFFER_X_CHANNEL_ID", "x")

    settings = Settings.from_env()

    assert settings.buffer_api_key == "key"
    assert settings.database_path == Path("database/posts.db")


def test_settings_require_buffer_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("BUFFER_API_KEY", raising=False)

    with pytest.raises(ValueError, match="BUFFER_API_KEY"):
        Settings.from_env()


def test_load_dotenv_does_not_override_environment(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    dotenv = tmp_path / ".env"
    dotenv.write_text(
        'BUFFER_API_KEY="from-file"\nBUFFER_INSTAGRAM_CHANNEL_ID=instagram\n',
        encoding="utf-8",
    )
    monkeypatch.setenv("BUFFER_API_KEY", "from-environment")
    monkeypatch.delenv("BUFFER_INSTAGRAM_CHANNEL_ID", raising=False)

    load_dotenv(dotenv)

    assert os.getenv("BUFFER_API_KEY") == "from-environment"
    assert os.getenv("BUFFER_INSTAGRAM_CHANNEL_ID") == "instagram"
    os.environ.pop("BUFFER_INSTAGRAM_CHANNEL_ID", None)
