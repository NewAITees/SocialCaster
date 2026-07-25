import json
import shutil
from datetime import UTC, datetime
from pathlib import Path

from social_caster.batch import DailyBatch, FolderLayout, _next_schedule_slots
from social_caster.database import connect, get_post_by_source_key


class FakeMediaPublisher:
    def __init__(self) -> None:
        self.published: list[tuple[Path, str]] = []

    def publish(self, image_path: Path, category: str) -> str:
        self.published.append((image_path, category))
        return "https://newaitees.github.io/NewAITees/assets/gallery/horror/a.png"

    def wait_until_available(self, url: str) -> None:
        return


class FakeSocialProvider:
    def __init__(self) -> None:
        self.services: list[str] = []

    def post(self, *, service: str, text: str, image_url: str, due_at: str | None = None) -> str:
        self.services.append(service)
        return f"{service}-1"


def _write_manifest(root: Path, publish_at: str | None = None) -> Path:
    inbox = root / "inbox"
    inbox.mkdir(parents=True)
    (inbox / "a.png").write_bytes(b"image")
    manifest = inbox / "a.json"
    manifest.write_text(
        json.dumps(
            {
                "image": "a.png",
                "category": "horror",
                "instagram_text": "instagram",
                "twitter_text": "x",
                **({"publish_at": publish_at} if publish_at else {}),
            }
        ),
        encoding="utf-8",
    )
    return manifest


def test_media_phase_archives_inputs_after_publishing() -> None:
    root = Path("tests/_runtime_batch_media")
    try:
        manifest = _write_manifest(root, "2026-01-01T00:00:00+00:00")
        connection = connect(":memory:")
        publisher = FakeMediaPublisher()

        DailyBatch(
            connection,
            None,
            FolderLayout(root),
            publisher,
        ).publish_media_once()

        post = get_post_by_source_key(connection, "inbox/a.json")
        assert post is not None
        assert post.media_status == "SUCCESS"
        assert not manifest.exists()
        assert not (root / "inbox/a.png").exists()
        assert (root / "archive/a.json").exists()
        assert (root / "archive/a.png").exists()
        assert publisher.published == [(root / "inbox/a.png", "horror")]
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_schedule_slots_cover_evening_and_next_day_morning() -> None:
    connection = connect(":memory:")
    now = datetime(2026, 7, 25, 7, 0, tzinfo=UTC)

    slots = _next_schedule_slots(connection, count=3, now=now)

    assert slots == [
        "2026-07-25T17:00:00+09:00",
        "2026-07-26T01:00:00+09:00",
        "2026-07-26T09:00:00+09:00",
    ]


def test_social_phase_uses_published_media_url() -> None:
    root = Path("tests/_runtime_batch_social")
    try:
        _write_manifest(root, "2026-01-01T00:00:00+00:00")
        connection = connect(":memory:")
        publisher = FakeMediaPublisher()
        provider = FakeSocialProvider()
        batch = DailyBatch(connection, provider, FolderLayout(root), publisher)

        batch.run_once()

        assert provider.services == ["instagram", "twitter"]
        assert not (root / "inbox/a.json").exists()
        assert not (root / "inbox/a.png").exists()
        assert (root / "archive/a.json").exists()
        assert (root / "archive/a.png").exists()
        post = get_post_by_source_key(connection, "inbox/a.json")
        assert post is not None
        assert post.publish_at is not None
    finally:
        shutil.rmtree(root, ignore_errors=True)
