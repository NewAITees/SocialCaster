from typing import Any

import pytest

from social_caster.buffer_client import BufferApiError, BufferClient


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


def test_scheduled_posts_follows_pagination(monkeypatch: Any) -> None:
    client = BufferClient("secret")
    pages = [
        {
            "posts": {
                "edges": [
                    {"node": {"id": "p1", "dueAt": "2026-10-09T08:47:00.000Z"}},
                    {"node": {"id": "p2", "dueAt": "2026-10-09T16:05:00.000Z"}},
                ],
                "pageInfo": {"hasNextPage": True, "endCursor": "cursor-1"},
            }
        },
        {
            "posts": {
                "edges": [{"node": {"id": "p3", "dueAt": "2026-10-10T00:38:00.000Z"}}],
                "pageInfo": {"hasNextPage": False, "endCursor": None},
            }
        },
    ]
    captured: list[dict[str, Any]] = []

    def fake_execute(query: str, variables: dict[str, Any] | None = None) -> dict[str, Any]:
        captured.append(variables or {})
        return pages[len(captured) - 1]

    monkeypatch.setattr(client, "execute", fake_execute)

    posts = client.scheduled_posts(organization_id="org-1", channel_id="channel-1")

    assert [post["id"] for post in posts] == ["p1", "p2", "p3"]
    assert captured[0]["after"] is None
    assert captured[0]["input"]["organizationId"] == "org-1"
    assert captured[0]["input"]["filter"] == {
        "channelIds": ["channel-1"],
        "status": ["scheduled"],
    }
    assert captured[1]["after"] == "cursor-1"


def test_scheduled_post_limit_reads_organization_limits(monkeypatch: Any) -> None:
    client = BufferClient("secret")

    def fake_execute(query: str, variables: dict[str, Any] | None = None) -> dict[str, Any]:
        return {
            "account": {
                "organizations": [
                    {"id": "org-1", "limits": {"scheduledPosts": 10}},
                    {"id": "org-2", "limits": {"scheduledPosts": 99}},
                ]
            }
        }

    monkeypatch.setattr(client, "execute", fake_execute)

    assert client.scheduled_post_limit(organization_id="org-1") == 10


def test_scheduled_post_limit_rejects_unknown_organization(monkeypatch: Any) -> None:
    client = BufferClient("secret")

    def fake_execute(query: str, variables: dict[str, Any] | None = None) -> dict[str, Any]:
        return {"account": {"organizations": [{"id": "org-1", "limits": {"scheduledPosts": 10}}]}}

    monkeypatch.setattr(client, "execute", fake_execute)

    with pytest.raises(BufferApiError):
        client.scheduled_post_limit(organization_id="missing")


def test_scheduled_post_limit_rejects_missing_limit(monkeypatch: Any) -> None:
    client = BufferClient("secret")

    def fake_execute(query: str, variables: dict[str, Any] | None = None) -> dict[str, Any]:
        return {"account": {"organizations": [{"id": "org-1", "limits": {"scheduledPosts": None}}]}}

    monkeypatch.setattr(client, "execute", fake_execute)

    with pytest.raises(BufferApiError):
        client.scheduled_post_limit(organization_id="org-1")
