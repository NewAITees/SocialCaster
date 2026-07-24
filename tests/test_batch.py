import json
import shutil
from pathlib import Path

from social_caster.batch import DailyBatch, FolderLayout
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


def _write_manifest(root: Path, publish_at: str) -> Path:
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
                "publish_at": publish_at,
            }
        ),
        encoding="utf-8",
    )
    return manifest


def test_media_phase_publishes_without_moving_inbox_files() -> None:
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
        assert manifest.exists()
        assert (root / "inbox/a.png").exists()
        assert publisher.published == [(root / "inbox/a.png", "horror")]
    finally:
        shutil.rmtree(root, ignore_errors=True)


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
    finally:
        shutil.rmtree(root, ignore_errors=True)
