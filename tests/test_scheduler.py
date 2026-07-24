from social_caster.database import add_post, connect
from social_caster.scheduler import Scheduler


class FakeProvider:
    def __init__(self) -> None:
        self.services: list[str] = []

    def post(self, *, service: str, text: str, image_url: str, due_at: str | None = None) -> str:
        self.services.append(service)
        if service == "instagram":
            raise RuntimeError("instagram unavailable")
        return "x-1"


def test_one_channel_failure_does_not_block_other() -> None:
    connection = connect(":memory:")
    add_post(
        connection,
        image_path="images/a.jpg",
        image_url="https://example.com/a.jpg",
        instagram_text="instagram",
        twitter_text="x",
        publish_at="2026-01-01T00:00:00+00:00",
    )
    provider = FakeProvider()

    Scheduler(connection, provider).process_once()

    assert provider.services == ["instagram", "twitter"]
