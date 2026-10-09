from collections.abc import Mapping
from typing import Any

from social_caster.batch import DailyBatch
from social_caster.buffer_client import BufferClient
from social_caster.cli import _build_parser


def test_publish_media_count_argument_defaults_and_overrides() -> None:
    parser = _build_parser()

    assert parser.parse_args(["publish-media"]).count == DailyBatch.MEDIA_PER_RUN
    assert parser.parse_args(["publish-media", "--count", "7"]).count == 7


def test_publish_social_count_argument_defaults_and_overrides() -> None:
    parser = _build_parser()

    assert parser.parse_args(["publish-social"]).count == DailyBatch.SOCIAL_POSTS_PER_RUN
    assert parser.parse_args(["publish-social", "--count", "5"]).count == 5


def test_publish_social_bounds_retries_by_buffer_room(monkeypatch: Any) -> None:
    # publish-social は呼び出し時点のBuffer空き枠を自分で読み、サービス別に渡す。
    # run.ps1側で空き枠を渡さずに呼んでも、満杯のチャンネルへ試行し続けない。
    import social_caster.cli as cli_module

    monkeypatch.setenv("BUFFER_API_KEY", "secret")
    monkeypatch.setenv("BUFFER_INSTAGRAM_CHANNEL_ID", "ig-channel")
    monkeypatch.setenv("BUFFER_X_CHANNEL_ID", "x-channel")
    monkeypatch.setenv("ENABLE_PINTEREST", "false")
    monkeypatch.setenv("ENABLE_TWITTER", "false")
    monkeypatch.setenv("DATABASE_PATH", ":memory:")

    captured: dict[str, Any] = {}

    class FakeStock:
        def __init__(self, room: int) -> None:
            self.room = room

    def fake_read_service_stock(
        client: Any, *, channels: dict[str, str], target_stock: int
    ) -> dict[str, Any]:
        captured["channels"] = channels
        return {service: FakeStock(room=1) for service in channels}

    class FakeBatch(DailyBatch):
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass  # 接続やproviderの実体化を避ける。パーサーが参照するクラス定数だけ必要。

        def publish_social_once(
            self,
            count: int = DailyBatch.SOCIAL_POSTS_PER_RUN,
            *,
            room: Mapping[str, int] | None = None,
        ) -> None:
            captured["count"] = count
            captured["room"] = room

    monkeypatch.setattr(cli_module, "read_service_stock", fake_read_service_stock)
    monkeypatch.setattr(cli_module, "DailyBatch", FakeBatch)
    monkeypatch.setattr(cli_module, "connect", lambda path: None)
    monkeypatch.setattr(BufferClient, "__init__", lambda self, api_key: None)

    import sys

    monkeypatch.setattr(sys, "argv", ["social-caster", "publish-social", "--count", "2"])
    cli_module.main()

    assert captured["count"] == 2
    assert captured["room"] == {"instagram": 1}
