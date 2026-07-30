import json
import random
import shutil
from datetime import UTC, datetime
from pathlib import Path

from social_caster.batch import (
    SCHEDULE_JITTER_MAX_MINUTES,
    DailyBatch,
    FolderLayout,
    _next_schedule_slots,
)
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
        assert post.image_path == str(root / "inbox/a.png")
        assert post.archive_image_path == str(root / "archive/a.png")
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

    # 分ゆらぎを0に固定すると基準時刻どおりになる。
    slots = _next_schedule_slots(
        connection, count=3, now=now, rng=_ZeroJitterRandom()
    )

    assert slots == [
        "2026-07-25T17:00:00+09:00",
        "2026-07-26T01:00:00+09:00",
        "2026-07-26T09:00:00+09:00",
    ]


class _ZeroJitterRandom(random.Random):
    def randint(self, a: int, b: int) -> int:
        return 0


def test_schedule_slots_apply_minute_jitter_within_range() -> None:
    connection = connect(":memory:")
    now = datetime(2026, 7, 25, 7, 0, tzinfo=UTC)

    slots = _next_schedule_slots(connection, count=3, now=now, rng=random.Random(1))

    parsed = [datetime.fromisoformat(slot) for slot in slots]
    # 基準の時（JST 17,1,9）は保たれ、分だけ0〜上限でゆらぐ。
    assert [dt.hour for dt in parsed] == [17, 1, 9]
    for dt in parsed:
        assert 0 <= dt.minute <= SCHEDULE_JITTER_MAX_MINUTES
    # 少なくとも1件は:00からずれている（ゆらぎが効いている）。
    assert any(dt.minute != 0 for dt in parsed)


def test_schedule_slots_are_deterministic_for_same_seed() -> None:
    connection = connect(":memory:")
    now = datetime(2026, 7, 25, 7, 0, tzinfo=UTC)

    first = _next_schedule_slots(connection, count=3, now=now, rng=random.Random(7))
    second = _next_schedule_slots(connection, count=3, now=now, rng=random.Random(7))

    assert first == second


class RecordingSocialProvider:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def post(self, *, service: str, text: str, image_url: str, due_at: str | None = None) -> str:
        self.calls.append((service, text))
        return f"{service}-1"


def _seed_media_ready_post(
    connection: object, *, source_key: str, twitter_text: str
) -> int:
    from social_caster.database import add_pending_post, mark_media_success

    post_id = add_pending_post(
        connection,
        source_key=source_key,
        image_path=f"/tmp/{source_key}.png",
        instagram_text=f"instagram {source_key}",
        twitter_text=twitter_text,
    )
    mark_media_success(
        connection,
        post_id=post_id,
        archive_image_path=f"/tmp/{source_key}.png",
        image_url="https://newaitees.github.io/NewAITees/assets/gallery-social/other/x.jpg",
    )
    return post_id


def test_social_phase_skips_near_duplicate_twitter_text() -> None:
    connection = connect(":memory:")
    provider = RecordingSocialProvider()
    batch = DailyBatch(connection, provider, FolderLayout(Path("tests/_unused")), None)

    _seed_media_ready_post(
        connection,
        source_key="first",
        twitter_text=(
            "苔むした輪の向こうに、時計仕掛けの妖精郷。歯車の塔がまわり、"
            "青い惑星が浮かび、小さな冒険者が石段をのぼる。 #aiart"
        ),
    )
    dup_id = _seed_media_ready_post(
        connection,
        source_key="second",
        twitter_text=(
            "苔むした環の向こう、月光の時計仕掛け妖精都市。歯車がまわり、"
            "小さな冒険者が橋を渡る。時さえおもちゃになる箱庭世界。 #aiart"
        ),
    )

    batch.publish_social_once()

    twitter_texts = [text for service, text in provider.calls if service == "twitter"]
    assert len(twitter_texts) == 1  # 重複した2件目はXへ投稿されない

    dup = get_post_by_source_key(connection, "second")
    assert dup is not None and dup.id == dup_id
    assert dup.twitter_status == "FAILED"
    assert dup.instagram_status == "SUCCESS"  # Instagramは重複チェックの対象外


def test_social_phase_strips_urls_from_twitter_text() -> None:
    connection = connect(":memory:")
    provider = RecordingSocialProvider()
    batch = DailyBatch(connection, provider, FolderLayout(Path("tests/_unused")), None)

    _seed_media_ready_post(
        connection,
        source_key="withlink",
        twitter_text="作品はこちら→ https://www.instagram.com/new_ai_tees #aiart",
    )

    batch.publish_social_once()

    twitter_texts = [text for service, text in provider.calls if service == "twitter"]
    assert len(twitter_texts) == 1
    assert "http" not in twitter_texts[0]  # X本文からリンクが除去されている


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
        assert post.archive_image_path == str(root / "archive/a.png")
    finally:
        shutil.rmtree(root, ignore_errors=True)
