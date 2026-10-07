from typing import Any

from social_caster.buffer_client import BufferClient


def test_create_post_uses_custom_schedule(monkeypatch: Any) -> None:
    client = BufferClient("secret")
    captured: dict[str, Any] = {}

    def fake_execute(query: str, variables: dict[str, Any] | None = None) -> dict[str, Any]:
        captured["query"] = query
        return {"createPost": {"post": {"id": "post-1"}}}

    monkeypatch.setattr(client, "execute", fake_execute)

    post_id = client.create_post(
        channel_id="instagram-channel",
        text="hello",
        image_url="https://example.com/image.jpg",
        due_at="2026-07-24T12:00:00Z",
    )

    assert post_id == "post-1"
    assert "mode: customScheduled" in captured["query"]
    assert "https://example.com/image.jpg" in captured["query"]


def test_create_instagram_post_sets_post_type(monkeypatch: Any) -> None:
    client = BufferClient("secret")
    captured: dict[str, Any] = {}

    def fake_execute(query: str, variables: dict[str, Any] | None = None) -> dict[str, Any]:
        captured["query"] = query
        return {"createPost": {"post": {"id": "post-2"}}}

    monkeypatch.setattr(client, "execute", fake_execute)

    client.create_post(
        channel_id="instagram-channel",
        text="hello",
        image_url="https://example.com/image.jpg",
        service="instagram",
    )

    assert "metadata: { instagram: { type: post, shouldShareToFeed: true } }" in captured["query"]


def test_create_pinterest_post_sets_metadata(monkeypatch: Any) -> None:
    client = BufferClient("secret")
    captured: dict[str, Any] = {}

    def fake_execute(query: str, variables: dict[str, Any] | None = None) -> dict[str, Any]:
        captured["query"] = query
        return {"createPost": {"post": {"id": "pin-1"}}}

    monkeypatch.setattr(client, "execute", fake_execute)

    client.create_post(
        channel_id="pinterest-channel",
        text="説明",
        image_url="https://example.com/image.jpg",
        service="pinterest",
        board_service_id="board-1",
        title="作品タイトル",
        destination_url="https://newaitees.github.io/NewAITees",
    )

    query = captured["query"]
    assert "metadata: { pinterest:" in query
    assert 'boardServiceId: "board-1"' in query
    assert 'title: "作品タイトル"' in query
    assert 'url: "https://newaitees.github.io/NewAITees"' in query
