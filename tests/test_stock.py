from typing import Any

import pytest

from social_caster.buffer_client import BufferApiError
from social_caster.config import Settings
from social_caster.stock import read_service_stock, service_channels


class FakeBufferClient:
    def __init__(self, scheduled: dict[str, list[str]], limit: int | None = 10) -> None:
        self._scheduled = scheduled
        self._limit = limit
        self.calls: list[str] = []

    def organization_id(self) -> str:
        self.calls.append("organization_id")
        return "org-1"

    def scheduled_post_limit(self, *, organization_id: str) -> int:
        self.calls.append("scheduled_post_limit")
        if self._limit is None:
            raise BufferApiError("上限が取得できません")
        return self._limit

    def scheduled_posts(self, *, organization_id: str, channel_id: str) -> list[dict[str, Any]]:
        self.calls.append(f"scheduled_posts:{channel_id}")
        return [{"id": post_id} for post_id in self._scheduled.get(channel_id, [])]


def test_read_service_stock_measures_each_channel_against_buffer() -> None:
    client = FakeBufferClient({"ig": ["a"] * 6, "pin": ["b"] * 9})

    plan = read_service_stock(
        client, channels={"instagram": "ig", "pinterest": "pin"}, target_stock=9
    )

    assert plan["instagram"].stock == 6
    assert plan["instagram"].need == 3
    assert plan["instagram"].room == 4
    assert plan["pinterest"].need == 0
    assert plan["pinterest"].room == 1


def test_read_service_stock_resolves_the_limit_once() -> None:
    client = FakeBufferClient({"ig": [], "pin": []})

    read_service_stock(client, channels={"instagram": "ig", "pinterest": "pin"}, target_stock=9)

    assert client.calls.count("scheduled_post_limit") == 1
    assert client.calls.count("organization_id") == 1


def test_read_service_stock_propagates_api_failure() -> None:
    # 取得できないときローカル推定へ退避すると、実枠とずれたまま補充を続ける。
    client = FakeBufferClient({"ig": []}, limit=None)

    with pytest.raises(BufferApiError):
        read_service_stock(client, channels={"instagram": "ig"}, target_stock=9)


def test_service_channels_includes_pinterest_only_when_enabled() -> None:
    def settings(*, enable_pinterest: bool) -> Settings:
        return Settings(
            buffer_api_key="k",
            instagram_channel_id="ig",
            x_channel_id="x",
            pinterest_channel_id="pin",
            enable_pinterest=enable_pinterest,
        )

    assert service_channels(settings(enable_pinterest=False)) == {"instagram": "ig"}
    assert service_channels(settings(enable_pinterest=True)) == {
        "instagram": "ig",
        "pinterest": "pin",
    }
