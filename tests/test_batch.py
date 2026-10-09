import json
import random
import shutil
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

from social_caster.batch import (
    SCHEDULE_JITTER_MAX_MINUTES,
    DailyBatch,
    FolderLayout,
    _next_schedule_slots,
    plan_service_stock,
    refill_amount,
)
from social_caster.database import connect, get_post_by_source_key


class FakeMediaPublisher:
    def __init__(self) -> None:
        self.published: list[tuple[Path, str]] = []

    def publish(self, image_path: Path, category: str) -> str:
        self.published.append((image_path, category))
        return "https://newaitees.github.io/NewAITees/assets/gallery/horror/a.png"

    def flush(self) -> None:
        return

    def wait_until_available(self, url: str) -> None:
        return


class FakeSocialProvider:
    def __init__(self) -> None:
        self.services: list[str] = []

    def post(
        self,
        *,
        service: str,
        text: str,
        image_url: str,
        due_at: str | None = None,
        category: str | None = None,
        title: str | None = None,
        destination_url: str | None = None,
    ) -> str:
        self.services.append(service)
        return f"{service}-1"


def _write_manifest(root: Path, publish_at: str | None = None) -> Path:
    # 画像は inbox、manifest は manifests に分かれて置かれる。
    inbox = root / "inbox"
    manifests = root / "manifests"
    inbox.mkdir(parents=True)
    manifests.mkdir(parents=True)
    (inbox / "a.png").write_bytes(b"image")
    manifest = manifests / "a.json"
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

        post = get_post_by_source_key(connection, "manifests/a.json")
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


def test_media_phase_stores_optional_pinterest_fields() -> None:
    root = Path("tests/_runtime_batch_pinterest_manifest")
    try:
        manifest = _write_manifest(root)
        payload = json.loads(manifest.read_text(encoding="utf-8"))
        payload.update(pinterest_text="Pinterest本文", pinterest_title="Pinterest題名")
        manifest.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        connection = connect(":memory:")

        DailyBatch(
            connection,
            None,
            FolderLayout(root),
            FakeMediaPublisher(),
        ).publish_media_once()

        post = get_post_by_source_key(connection, "manifests/a.json")
        assert post is not None
        assert post.category == "horror"
        assert post.pinterest_text == "Pinterest本文"
        assert post.pinterest_title == "Pinterest題名"
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_schedule_slots_cover_evening_and_next_day_morning() -> None:
    connection = connect(":memory:")
    now = datetime(2026, 7, 25, 7, 0, tzinfo=UTC)

    # 分ゆらぎを0に固定すると基準時刻どおりになる。
    slots = _next_schedule_slots(connection, count=3, now=now, rng=_ZeroJitterRandom())

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
        self.details: list[tuple[str, str | None, str | None, str | None]] = []

    def post(
        self,
        *,
        service: str,
        text: str,
        image_url: str,
        due_at: str | None = None,
        category: str | None = None,
        title: str | None = None,
        destination_url: str | None = None,
    ) -> str:
        self.calls.append((service, text))
        self.details.append((service, category, title, destination_url))
        return f"{service}-1"


class DueAtRecordingProvider:
    def __init__(self) -> None:
        self.due_at_values: list[str | None] = []

    def post(
        self,
        *,
        service: str,
        text: str,
        image_url: str,
        due_at: str | None = None,
        category: str | None = None,
        title: str | None = None,
        destination_url: str | None = None,
    ) -> str:
        self.due_at_values.append(due_at)
        return f"{service}-1"


def _seed_media_ready_post(
    connection: sqlite3.Connection,
    *,
    source_key: str,
    twitter_text: str,
    pinterest_text: str | None = None,
    pinterest_title: str | None = None,
    category: str = "other",
) -> int:
    from social_caster.database import add_pending_post, mark_media_success

    post_id = add_pending_post(
        connection,
        source_key=source_key,
        image_path=f"/tmp/{source_key}.png",
        instagram_text=f"instagram {source_key}",
        twitter_text=twitter_text,
        pinterest_text=pinterest_text,
        pinterest_title=pinterest_title,
        category=category,
    )
    mark_media_success(
        connection,
        post_id=post_id,
        archive_image_path=f"/tmp/{source_key}.png",
        image_url="https://newaitees.github.io/NewAITees/assets/gallery-social/other/x.jpg",
    )
    return post_id


def test_refill_amount_uses_target_difference() -> None:
    assert refill_amount(current_stock=4, target_stock=9, reservation_cap=10) == 5


def test_refill_amount_is_zero_when_target_is_met() -> None:
    assert refill_amount(current_stock=9, target_stock=9, reservation_cap=10) == 0


def test_refill_amount_is_clamped_to_reservation_cap() -> None:
    assert refill_amount(current_stock=8, target_stock=12, reservation_cap=10) == 2


def test_future_jst_publish_at_remains_scheduled_against_utc_now() -> None:
    from social_caster.database import assign_publish_at

    connection = connect(":memory:")
    provider = DueAtRecordingProvider()
    post_id = _seed_media_ready_post(connection, source_key="future-jst", twitter_text="x本文")
    publish_at = "2026-08-31T01:05:00+09:00"
    assign_publish_at(connection, post_id=post_id, publish_at=publish_at)
    batch = DailyBatch(
        connection,
        provider,
        FolderLayout(Path("tests/_unused")),
        None,
        enable_twitter=False,
    )

    with patch("social_caster.batch.datetime", wraps=datetime) as mocked_datetime:
        mocked_datetime.now.return_value = datetime(2026, 8, 30, 16, 0, tzinfo=UTC)
        batch.publish_social_once()

    assert provider.due_at_values == [publish_at]


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


def test_social_phase_skips_twitter_when_disabled() -> None:
    connection = connect(":memory:")
    provider = RecordingSocialProvider()
    batch = DailyBatch(
        connection,
        provider,
        FolderLayout(Path("tests/_unused")),
        None,
        enable_twitter=False,
    )

    _seed_media_ready_post(connection, source_key="disabled", twitter_text="x本文 #aiart")

    batch.publish_social_once()

    services = [service for service, _ in provider.calls]
    assert services == ["instagram"]  # Xへは一度も投稿されない

    post = get_post_by_source_key(connection, "disabled")
    assert post is not None
    assert post.instagram_status == "SUCCESS"
    assert post.twitter_status == "WAIT"  # 失敗扱いにせず未処理のまま残す


def test_social_phase_posts_twitter_when_enabled_by_default() -> None:
    connection = connect(":memory:")
    provider = RecordingSocialProvider()
    batch = DailyBatch(connection, provider, FolderLayout(Path("tests/_unused")), None)

    _seed_media_ready_post(connection, source_key="enabled", twitter_text="x本文 #aiart")

    batch.publish_social_once()

    services = [service for service, _ in provider.calls]
    assert services == ["instagram", "twitter"]

    post = get_post_by_source_key(connection, "enabled")
    assert post is not None
    assert post.twitter_status == "SUCCESS"


def test_social_phase_skips_pinterest_when_disabled() -> None:
    connection = connect(":memory:")
    provider = RecordingSocialProvider()
    batch = DailyBatch(
        connection,
        provider,
        FolderLayout(Path("tests/_unused")),
        None,
        enable_pinterest=False,
    )
    _seed_media_ready_post(
        connection,
        source_key="pin-disabled",
        twitter_text="x本文",
        pinterest_text="Pinterest本文",
        pinterest_title="Pinterest題名",
    )

    batch.publish_social_once()

    assert "pinterest" not in [service for service, _ in provider.calls]


def test_social_phase_skips_pinterest_without_text() -> None:
    connection = connect(":memory:")
    provider = RecordingSocialProvider()
    batch = DailyBatch(
        connection,
        provider,
        FolderLayout(Path("tests/_unused")),
        None,
        enable_pinterest=True,
    )
    _seed_media_ready_post(connection, source_key="old-manifest", twitter_text="x本文")

    batch.publish_social_once()

    assert "pinterest" not in [service for service, _ in provider.calls]


def test_social_phase_posts_pinterest_with_category_metadata() -> None:
    connection = connect(":memory:")
    provider = RecordingSocialProvider()
    batch = DailyBatch(
        connection,
        provider,
        FolderLayout(Path("tests/_unused")),
        None,
        enable_pinterest=True,
        pinterest_destination_url="https://newaitees.github.io/NewAITees",
    )
    _seed_media_ready_post(
        connection,
        source_key="pin-enabled",
        twitter_text="x本文",
        pinterest_text="Pinterest本文",
        pinterest_title="Pinterest題名",
        category="horror",
    )

    batch.publish_social_once()

    post = get_post_by_source_key(connection, "pin-enabled")
    assert post is not None
    assert post.pinterest_status == "SUCCESS"
    assert (
        "pinterest",
        "horror",
        "Pinterest題名",
        "https://newaitees.github.io/NewAITees",
    ) in provider.details


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
        post = get_post_by_source_key(connection, "manifests/a.json")
        assert post is not None
        assert post.publish_at is not None
        assert post.archive_image_path == str(root / "archive/a.png")
    finally:
        shutil.rmtree(root, ignore_errors=True)


class SelectiveFailingPublisher:
    """指定した画像名のときだけ公開に失敗する公開役。"""

    def __init__(self, failing: set[str]) -> None:
        self._failing = failing
        self.published: list[str] = []

    def publish(self, image_path: Path, category: str) -> str:
        self.published.append(image_path.name)
        if image_path.name in self._failing:
            raise RuntimeError(f"公開に失敗しました: {image_path.name}")
        return f"https://newaitees.github.io/NewAITees/assets/gallery-social/{category}/x.jpg"

    def flush(self) -> None:
        return

    def wait_until_available(self, url: str) -> None:
        return


def _write_named_manifest(root: Path, name: str) -> Path:
    inbox = root / "inbox"
    manifests = root / "manifests"
    inbox.mkdir(parents=True, exist_ok=True)
    manifests.mkdir(parents=True, exist_ok=True)
    (inbox / f"{name}.png").write_bytes(b"image")
    manifest = manifests / f"{name}.png.json"
    manifest.write_text(
        json.dumps(
            {
                "image": f"{name}.png",
                "category": "horror",
                "instagram_text": "instagram",
                "twitter_text": "x",
            }
        ),
        encoding="utf-8",
    )
    return manifest


def test_media_phase_reaches_new_manifests_despite_leading_failures() -> None:
    # 失敗した manifest は inbox に残り辞書順の先頭を占めるため、
    # 予算を分割しないと新規の画像へ永久に到達できない。
    root = Path("tests/_runtime_batch_headline")
    try:
        for name in ("a_fail1", "a_fail2", "a_fail3"):
            _write_named_manifest(root, name)
        for name in ("b_new1", "b_new2", "b_new3"):
            _write_named_manifest(root, name)
        connection = connect(":memory:")
        failing = {"a_fail1.png", "a_fail2.png", "a_fail3.png"}

        first = SelectiveFailingPublisher(failing)
        DailyBatch(connection, None, FolderLayout(root), first).publish_media_once(3)
        assert first.published == ["a_fail1.png", "a_fail2.png", "a_fail3.png"]

        second = SelectiveFailingPublisher(failing)
        DailyBatch(connection, None, FolderLayout(root), second).publish_media_once(3)

        # リトライは1件だけに制限し、残りの枠は必ず新規へ回す
        assert second.published == ["a_fail1.png", "b_new1.png", "b_new2.png"]
        assert get_post_by_source_key(connection, "manifests/b_new1.png.json") is not None
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_media_phase_prefers_new_manifest_when_only_one_slot() -> None:
    root = Path("tests/_runtime_batch_single_slot")
    try:
        _write_named_manifest(root, "a_fail1")
        _write_named_manifest(root, "b_new1")
        connection = connect(":memory:")
        failing = {"a_fail1.png"}

        DailyBatch(
            connection, None, FolderLayout(root), SelectiveFailingPublisher(failing)
        ).publish_media_once(1)

        second = SelectiveFailingPublisher(failing)
        DailyBatch(connection, None, FolderLayout(root), second).publish_media_once(1)

        # 枠が1件しかないときはリトライで潰さず新規を進める
        assert second.published == ["b_new1.png"]
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_media_phase_skips_already_published_manifests() -> None:
    root = Path("tests/_runtime_batch_skip_success")
    try:
        _write_named_manifest(root, "a_done")
        _write_named_manifest(root, "b_new1")
        connection = connect(":memory:")

        first = SelectiveFailingPublisher(set())
        DailyBatch(connection, None, FolderLayout(root), first).publish_media_once(1)
        assert first.published == ["a_done.png"]

        second = SelectiveFailingPublisher(set())
        DailyBatch(connection, None, FolderLayout(root), second).publish_media_once(1)

        # 成功した manifest は archive へ移動しているので二度処理しない
        assert second.published == ["b_new1.png"]
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_media_phase_keeps_images_and_manifests_in_separate_folders() -> None:
    # 利用者が画像を置く inbox に JSON が混ざらないようにする。
    root = Path("tests/_runtime_batch_split")
    try:
        manifest = _write_manifest(root, "2026-01-01T00:00:00+00:00")
        assert manifest.parent.name == "manifests"
        connection = connect(":memory:")
        publisher = FakeMediaPublisher()

        DailyBatch(connection, None, FolderLayout(root), publisher).publish_media_once()

        post = get_post_by_source_key(connection, "manifests/a.json")
        assert post is not None
        assert post.media_status == "SUCCESS"
        # 画像は inbox から読み、公開後は画像も manifest も archive へ移す
        assert publisher.published == [(root / "inbox/a.png", "horror")]
        assert not (root / "inbox/a.png").exists()
        assert not manifest.exists()
        assert (root / "archive/a.png").exists()
        assert (root / "archive/a.json").exists()
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_layout_ensure_creates_the_manifests_folder() -> None:
    root = Path("tests/_runtime_batch_ensure")
    try:
        layout = FolderLayout(root)
        layout.ensure()
        assert layout.inbox.is_dir()
        assert layout.manifests.is_dir()
        assert layout.archive.is_dir()
    finally:
        shutil.rmtree(root, ignore_errors=True)


class RecordingBatchPublisher:
    """stage(publish) と flush と待機の呼び出し順を記録する公開役。"""

    def __init__(self, flush_error: str | None = None) -> None:
        self.events: list[str] = []
        self._flush_error = flush_error

    def publish(self, image_path: Path, category: str) -> str:
        self.events.append(f"publish:{image_path.name}")
        return f"https://example.invalid/{image_path.stem}.jpg"

    def flush(self) -> None:
        self.events.append("flush")
        if self._flush_error is not None:
            raise RuntimeError(self._flush_error)

    def wait_until_available(self, url: str) -> None:
        self.events.append(f"wait:{url.rsplit('/', 1)[-1]}")


def test_media_phase_pushes_once_after_staging_every_image() -> None:
    root = Path("tests/_runtime_batch_flush")
    try:
        for name in ("a_one", "b_two", "c_three"):
            _write_named_manifest(root, name)
        connection = connect(":memory:")
        publisher = RecordingBatchPublisher()

        DailyBatch(connection, None, FolderLayout(root), publisher).publish_media_once(3)

        # 3枚ぶんのcommitを済ませてから1回だけpushし、そのあとで反映を待つ
        assert publisher.events == [
            "publish:a_one.png",
            "publish:b_two.png",
            "publish:c_three.png",
            "flush",
            "wait:a_one.jpg",
            "wait:b_two.jpg",
            "wait:c_three.jpg",
        ]
        assert publisher.events.count("flush") == 1
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_media_phase_fails_the_whole_batch_when_the_push_fails() -> None:
    root = Path("tests/_runtime_batch_flush_fail")
    try:
        for name in ("a_one", "b_two"):
            _write_named_manifest(root, name)
        connection = connect(":memory:")

        DailyBatch(
            connection, None, FolderLayout(root), RecordingBatchPublisher(flush_error="push拒否")
        ).publish_media_once(2)

        # pushが通らなければ公開URLは成立しないので、commit済みの全件を失敗にする
        for name in ("a_one", "b_two"):
            post = get_post_by_source_key(connection, f"manifests/{name}.png.json")
            assert post is not None
            assert post.media_status == "FAILED"
        # 画像とmanifestはarchiveへ動かさず、次回リトライできる状態で残す
        assert (root / "inbox/a_one.png").exists()
        assert (root / "manifests/a_one.png.json").exists()
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_social_phase_stops_at_the_room_left_on_the_channel() -> None:
    # Bufferのチャンネルは予約枠が埋まると以降を拒否するため、空き枠を超えて試行しない。
    connection = connect(":memory:")
    provider = RecordingSocialProvider()
    batch = DailyBatch(
        connection,
        provider,
        FolderLayout(Path("tests/_unused")),
        None,
        enable_twitter=False,
    )
    for index in range(4):
        _seed_media_ready_post(connection, source_key=f"backlog-{index}", twitter_text="x本文")

    batch.publish_social_once(room={"instagram": 1})

    assert [service for service, _ in provider.calls] == ["instagram"]


def test_social_phase_leaves_untried_posts_waiting_not_failed() -> None:
    # 空き枠待ちは失敗ではない。FAILEDにすると翌日のリトライ対象から外れる。
    connection = connect(":memory:")
    provider = RecordingSocialProvider()
    batch = DailyBatch(
        connection,
        provider,
        FolderLayout(Path("tests/_unused")),
        None,
        enable_twitter=False,
    )
    _seed_media_ready_post(connection, source_key="goes-through", twitter_text="x本文")
    skipped_id = _seed_media_ready_post(connection, source_key="no-room", twitter_text="x本文")

    batch.publish_social_once(room={"instagram": 1})

    skipped = get_post_by_source_key(connection, "no-room")
    assert skipped is not None and skipped.id == skipped_id
    assert skipped.instagram_status == "WAIT"


def test_social_phase_counts_room_per_service() -> None:
    # Instagramが満杯でもPinterestに空きがあれば、Pinterestだけは進める。
    connection = connect(":memory:")
    provider = RecordingSocialProvider()
    batch = DailyBatch(
        connection,
        provider,
        FolderLayout(Path("tests/_unused")),
        None,
        enable_twitter=False,
        enable_pinterest=True,
    )
    _seed_media_ready_post(
        connection, source_key="pin-only", twitter_text="x本文", pinterest_text="説明"
    )

    batch.publish_social_once(room={"instagram": 0, "pinterest": 1})

    assert [service for service, _ in provider.calls] == ["pinterest"]


def test_social_phase_is_unbounded_when_no_room_is_given() -> None:
    connection = connect(":memory:")
    provider = RecordingSocialProvider()
    batch = DailyBatch(
        connection,
        provider,
        FolderLayout(Path("tests/_unused")),
        None,
        enable_twitter=False,
    )
    for index in range(3):
        _seed_media_ready_post(connection, source_key=f"free-{index}", twitter_text="x本文")

    batch.publish_social_once()

    assert len(provider.calls) == 3


def test_plan_service_stock_keeps_services_independent() -> None:
    # 充足しているサービスが、不足しているサービスの補充を止めてはならない。
    plan = plan_service_stock(scheduled={"instagram": 6, "pinterest": 9}, limit=10, target_stock=9)

    assert plan["instagram"].need == 3
    assert plan["instagram"].room == 4
    assert plan["pinterest"].need == 0
    assert plan["pinterest"].room == 1


def test_plan_service_stock_clamps_need_to_the_room() -> None:
    plan = plan_service_stock(scheduled={"instagram": 8}, limit=10, target_stock=12)

    assert plan["instagram"].need == 2
    assert plan["instagram"].room == 2


def test_plan_service_stock_never_goes_negative_past_the_limit() -> None:
    plan = plan_service_stock(scheduled={"instagram": 11}, limit=10, target_stock=9)

    assert plan["instagram"].need == 0
    assert plan["instagram"].room == 0
    assert plan["instagram"].stock == 11
