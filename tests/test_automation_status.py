import importlib.util
import sqlite3
from pathlib import Path
from types import ModuleType

import pytest

from social_caster.database import add_post, connect, mark_success


def _load_status_module() -> ModuleType:
    path = Path(__file__).resolve().parents[1] / "automation" / "status.py"
    spec = importlib.util.spec_from_file_location("automation_status", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _add_stock(connection: sqlite3.Connection, service: str, count: int) -> None:
    for index in range(count):
        post_id = add_post(
            connection,
            image_path=f"images/{service}-{index}.jpg",
            image_url=f"https://example.com/{service}-{index}.jpg",
            instagram_text=f"instagram {index}",
            twitter_text=f"twitter {index}",
            category="other",
            pinterest_text=f"pinterest {index}",
            pinterest_title=f"title {index}",
            publish_at="2999-01-01T00:00:00+00:00",
        )
        mark_success(connection, post_id=post_id, service=service, buffer_id=f"{service}-{index}")


def test_status_outputs_service_stock_and_refills_from_enabled_minimum(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    database_path = tmp_path / "posts.db"
    connection = connect(database_path)
    _add_stock(connection, "instagram", 7)
    _add_stock(connection, "pinterest", 4)
    connection.close()
    monkeypatch.setenv("DATABASE_PATH", str(database_path))
    monkeypatch.setenv("ENABLE_PINTEREST", "true")
    monkeypatch.setenv("TARGET_STOCK", "9")
    monkeypatch.setenv("BUFFER_RESERVATION_CAP", "10")

    _load_status_module().main()

    output = capsys.readouterr().out
    assert "STOCK_INSTAGRAM=7" in output
    assert "STOCK_PINTEREST=4" in output
    assert "REFILL=5" in output
    assert " STOCK=" not in output


def test_status_ignores_pinterest_stock_when_disabled(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    database_path = tmp_path / "posts.db"
    connection = connect(database_path)
    _add_stock(connection, "instagram", 7)
    connection.close()
    monkeypatch.setenv("DATABASE_PATH", str(database_path))
    monkeypatch.setenv("ENABLE_PINTEREST", "false")
    monkeypatch.setenv("TARGET_STOCK", "9")
    monkeypatch.setenv("BUFFER_RESERVATION_CAP", "10")

    _load_status_module().main()

    output = capsys.readouterr().out
    assert "STOCK_PINTEREST=0" in output
    assert "REFILL=2" in output
