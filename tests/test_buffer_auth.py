from typing import Any

from social_caster.buffer_client import BufferClient


def test_get_channels_uses_organization_id(monkeypatch: Any) -> None:
    client = BufferClient("secret")
    captured: dict[str, Any] = {}

    def fake_execute(query: str, variables: dict[str, Any] | None = None) -> dict[str, Any]:
        captured["query"] = query
        captured["variables"] = variables
        return {"channels": [{"id": "1", "name": "Instagram", "service": "instagram"}]}

    monkeypatch.setattr(client, "execute", fake_execute)

    assert client.get_channels("org-1") == [
        {"id": "1", "name": "Instagram", "service": "instagram"}
    ]
    assert captured["variables"] == {"organizationId": "org-1"}
