"""Buffer provider boundary used by the scheduler."""

from typing import Protocol

from social_caster.buffer_client import BufferClient


class SocialProvider(Protocol):
    def post(self, *, service: str, text: str, image_url: str, due_at: str | None = None) -> str:
        """Submit an image post and return the provider post ID."""


class BufferProvider:
    def __init__(self, client: BufferClient, instagram_channel_id: str, x_channel_id: str) -> None:
        self._client = client
        self._channels = {"instagram": instagram_channel_id, "twitter": x_channel_id}

    def post(self, *, service: str, text: str, image_url: str, due_at: str | None = None) -> str:
        try:
            channel_id = self._channels[service]
        except KeyError as exc:
            raise ValueError(f"未対応のサービスです: {service}") from exc
        return self._client.create_post(
            channel_id=channel_id,
            text=text,
            image_url=image_url,
            due_at=due_at,
            service=service,
        )
