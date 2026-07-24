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
