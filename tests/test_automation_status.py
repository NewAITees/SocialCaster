import importlib.util
import sqlite3
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

from social_caster.buffer_client import BufferApiError
from social_caster.database import add_post, connect, mark_failed, mark_success


def _load_status_module() -> ModuleType:
    path = Path(__file__).resolve().parents[1] / "automation" / "status.py"
    spec = importlib.util.spec_from_file_location("automation_status", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _add_media_counts(connection: sqlite3.Connection, *, service: str, count: int) -> None:
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


class FakeBufferClient:
    """status.py内から `BufferClient(api_key)` として生成される想定のスタブ。"""

    instances: list["FakeBufferClient"] = []

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key
        self.scheduled: dict[str, int] = {}
        self.limit: int | None = 10
        FakeBufferClient.instances.append(self)

    def organization_id(self) -> str:
        return "org-1"

    def scheduled_post_limit(self, *, organization_id: str) -> int:
        if self.limit is None:
            raise BufferApiError("Buffer APIへの接続に失敗しました")
        return self.limit

    def scheduled_posts(self, *, organization_id: str, channel_id: str) -> list[dict[str, Any]]:
        return [{"id": f"p{i}"} for i in range(self.scheduled.get(channel_id, 0))]


@pytest.fixture(autouse=True)
def _reset_fake_instances() -> None:
    FakeBufferClient.instances = []


def _common_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BUFFER_API_KEY", "secret")
    monkeypatch.setenv("BUFFER_INSTAGRAM_CHANNEL_ID", "ig-channel")
    monkeypatch.setenv("BUFFER_X_CHANNEL_ID", "x-channel")
    monkeypatch.setenv("TARGET_STOCK", "9")


def test_status_computes_need_and_room_independently_per_service(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # Instagramが不足していてもPinterestが充足していれば、互いの数値は干渉しない。
    database_path = tmp_path / "posts.db"
    connect(database_path).close()
    _common_env(monkeypatch)
    monkeypatch.setenv("DATABASE_PATH", str(database_path))
    monkeypatch.setenv("ENABLE_PINTEREST", "true")
    monkeypatch.setenv("BUFFER_PINTEREST_CHANNEL_ID", "pin-channel")
    monkeypatch.setenv("BUFFER_PINTEREST_BOARD_DEFAULT", "board-1")

    module = _load_status_module()

    def init_with_stock(self: FakeBufferClient, api_key: str) -> None:
        self.api_key = api_key
        self.scheduled = {"ig-channel": 7, "pin-channel": 9}
        self.limit = 10

    monkeypatch.setattr(FakeBufferClient, "__init__", init_with_stock)
    monkeypatch.setattr(module, "BufferClient", FakeBufferClient)

    module.main()

    output = dict(
        token.split("=", 1) for token in capsys.readouterr().out.strip().split() if "=" in token
    )
    assert output["STOCK_INSTAGRAM"] == "7"
    assert output["NEED_INSTAGRAM"] == "2"
    assert output["ROOM_INSTAGRAM"] == "3"
    assert output["STOCK_PINTEREST"] == "9"
    assert output["NEED_PINTEREST"] == "0"
    assert output["ROOM_PINTEREST"] == "1"
    assert output["SCHEDULED_LIMIT"] == "10"
    assert "REFILL" not in output
    assert "RESERVATION_CAP" not in output


def test_status_omits_pinterest_fields_when_disabled(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    database_path = tmp_path / "posts.db"
    connect(database_path).close()
    _common_env(monkeypatch)
    monkeypatch.setenv("DATABASE_PATH", str(database_path))
    monkeypatch.setenv("ENABLE_PINTEREST", "false")

    module = _load_status_module()

    def init_with_stock(self: FakeBufferClient, api_key: str) -> None:
        self.api_key = api_key
        self.scheduled = {"ig-channel": 7}
        self.limit = 10

    monkeypatch.setattr(FakeBufferClient, "__init__", init_with_stock)
    monkeypatch.setattr(module, "BufferClient", FakeBufferClient)

    module.main()

    output = capsys.readouterr().out
    assert "STOCK_INSTAGRAM=7" in output
    assert "STOCK_PINTEREST" not in output
    assert "NEED_PINTEREST" not in output


def test_status_counts_media_and_social_outcomes_from_the_local_db(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    database_path = tmp_path / "posts.db"
    connection = connect(database_path)
    _add_media_counts(connection, service="instagram", count=3)
    connection.close()
    _common_env(monkeypatch)
    monkeypatch.setenv("DATABASE_PATH", str(database_path))
    monkeypatch.setenv("ENABLE_PINTEREST", "false")

    module = _load_status_module()

    def init_with_stock(self: FakeBufferClient, api_key: str) -> None:
        self.api_key = api_key
        self.scheduled = {"ig-channel": 0}
        self.limit = 10

    monkeypatch.setattr(FakeBufferClient, "__init__", init_with_stock)
    monkeypatch.setattr(module, "BufferClient", FakeBufferClient)

    module.main()

    output = capsys.readouterr().out
    assert "MEDIA_SUCCESS=3" in output
    assert "IG_SUCCESS=3" in output
    assert "PIN_SUCCESS=0" in output
    assert "PIN_FAILED=0" in output


def test_status_counts_pinterest_failures_for_the_retry_backlog_check(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # run.ps1 はPIN_FAILEDをリトライ継続の判断に使う。Instagramが充足していても
    # Pinterestの失敗分が残っていることを見失ってはならない。
    database_path = tmp_path / "posts.db"
    connection = connect(database_path)
    post_id = add_post(
        connection,
        image_path="images/pin-fail.jpg",
        image_url="https://example.com/pin-fail.jpg",
        instagram_text="instagram",
        twitter_text="twitter",
        category="other",
        pinterest_text="pinterest",
        pinterest_title="title",
        publish_at="2999-01-01T00:00:00+00:00",
    )
    mark_failed(
        connection, post_id=post_id, service="pinterest", error="Scheduled posts limit reached"
    )
    connection.close()
    _common_env(monkeypatch)
    monkeypatch.setenv("DATABASE_PATH", str(database_path))
    monkeypatch.setenv("ENABLE_PINTEREST", "true")
    monkeypatch.setenv("BUFFER_PINTEREST_CHANNEL_ID", "pin-channel")
    monkeypatch.setenv("BUFFER_PINTEREST_BOARD_DEFAULT", "board-1")

    module = _load_status_module()

    def init_with_stock(self: FakeBufferClient, api_key: str) -> None:
        self.api_key = api_key
        self.scheduled = {"ig-channel": 9, "pin-channel": 9}
        self.limit = 10

    monkeypatch.setattr(FakeBufferClient, "__init__", init_with_stock)
    monkeypatch.setattr(module, "BufferClient", FakeBufferClient)

    module.main()

    output = capsys.readouterr().out
    assert "PIN_FAILED=1" in output


def test_status_does_not_fall_back_to_local_estimates_when_buffer_fails(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # Bufferが答えられないのに在庫を推定すると、実枠とずれたまま補充を続けてしまう。
    database_path = tmp_path / "posts.db"
    connect(database_path).close()
    _common_env(monkeypatch)
    monkeypatch.setenv("DATABASE_PATH", str(database_path))
    monkeypatch.setenv("ENABLE_PINTEREST", "false")

    module = _load_status_module()

    def init_that_fails(self: FakeBufferClient, api_key: str) -> None:
        self.api_key = api_key
        self.scheduled = {}
        self.limit = None

    monkeypatch.setattr(FakeBufferClient, "__init__", init_that_fails)
    monkeypatch.setattr(module, "BufferClient", FakeBufferClient)

    with pytest.raises(BufferApiError):
        module.main()
