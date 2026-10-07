from typing import Any

from social_caster.provider import BufferProvider


class RecordingBufferClient:
    def __init__(self) -> None:
        self.arguments: dict[str, Any] = {}

    def create_post(self, **kwargs: Any) -> str:
        self.arguments = kwargs
        return "post-1"


def test_pinterest_category_resolves_board() -> None:
    client = RecordingBufferClient()
    provider = BufferProvider(
        client,  # type: ignore[arg-type]
        instagram_channel_id="instagram",
        x_channel_id="x",
        pinterest_channel_id="pinterest",
        pinterest_boards={"horror": "horror-board", "other": "default-board"},
    )

    provider.post(
        service="pinterest",
        text="説明",
        image_url="https://example.com/image.jpg",
        category="horror",
        title="題名",
        destination_url="https://newaitees.github.io/NewAITees",
    )

    assert client.arguments["channel_id"] == "pinterest"
    assert client.arguments["board_service_id"] == "horror-board"


def test_pinterest_unknown_category_uses_default_board() -> None:
    client = RecordingBufferClient()
    provider = BufferProvider(
        client,  # type: ignore[arg-type]
        instagram_channel_id="instagram",
        x_channel_id="x",
        pinterest_channel_id="pinterest",
        pinterest_boards={"other": "default-board"},
    )

    provider.post(
        service="pinterest",
        text="説明",
        image_url="https://example.com/image.jpg",
        category="unknown",
        title="題名",
        destination_url="https://newaitees.github.io/NewAITees",
    )

    assert client.arguments["board_service_id"] == "default-board"
