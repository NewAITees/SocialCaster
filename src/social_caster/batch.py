"""Two-stage inbox batch: publish media first, then post to Buffer."""

import json
import random
import shutil
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path
from typing import Protocol

from social_caster.content import diversify_hashtags, is_duplicate_text, strip_urls
from social_caster.database import (
    Post,
    add_pending_post,
    assign_publish_at,
    get_post_by_source_key,
    mark_failed,
    mark_media_failed,
    mark_media_success,
    mark_success,
    posted_twitter_texts,
    scheduled_posts,
    unscheduled_posts,
)
from social_caster.provider import SocialProvider

# 機械的な等間隔投稿を避けるため、基準時刻に0〜この分数のゆらぎを足す（凍結対策）。
SCHEDULE_JITTER_MAX_MINUTES = 50


class MediaPublisher(Protocol):
    def publish(self, image_path: Path, category: str) -> str:
        """Publish a local image and return its public URL."""

    def wait_until_available(self, url: str) -> None:
        """Wait until the public URL is served by the Pages deployment."""


@dataclass(frozen=True)
class FolderLayout:
    root: Path

    @property
    def inbox(self) -> Path:
        return self.root / "inbox"

    @property
    def archive(self) -> Path:
        return self.root / "archive"

    def ensure(self) -> None:
        self.inbox.mkdir(parents=True, exist_ok=True)
        self.archive.mkdir(parents=True, exist_ok=True)


class DailyBatch:
    MEDIA_PER_RUN = 3
    SOCIAL_POSTS_PER_RUN = 3
    SCHEDULE_HOURS_JST = (1, 9, 17)

    def __init__(
        self,
        connection: sqlite3.Connection,
        provider: SocialProvider | None,
        layout: FolderLayout,
        media_publisher: MediaPublisher | None,
        enable_twitter: bool = True,
    ) -> None:
        self._connection = connection
        self._provider = provider
        self._layout = layout
        self._media_publisher = media_publisher
        self._enable_twitter = enable_twitter

    def run_once(self) -> None:
        if self._media_publisher is None:
            raise RuntimeError("画像公開処理が設定されていません")
        self.publish_media_once()
        self.publish_social_once()

    def publish_media_once(self) -> None:
        media_publisher = self._media_publisher
        if media_publisher is None:
            raise RuntimeError("画像公開処理が設定されていません")
        self._layout.ensure()
        manifests = sorted(
            self._layout.inbox.glob("*.json"),
            key=lambda path: (self._publish_at(path), path.name),
        )
        for manifest_path in manifests[: self.MEDIA_PER_RUN]:
            self._publish_media_manifest(manifest_path)

    def publish_social_once(self) -> None:
        if self._provider is None:
            raise RuntimeError("SNS投稿処理が設定されていません")
        unscheduled = unscheduled_posts(self._connection, limit=self.SOCIAL_POSTS_PER_RUN)
        slots = _next_schedule_slots(
            self._connection, count=len(unscheduled), now=datetime.now(UTC)
        )
        for post, slot in zip(unscheduled, slots, strict=True):
            assign_publish_at(self._connection, post_id=post.id, publish_at=slot)
        seen_twitter_texts = posted_twitter_texts(self._connection)
        for post in scheduled_posts(self._connection):
            due_at = post.publish_at
            if due_at and due_at <= datetime.now(UTC).isoformat(timespec="seconds"):
                due_at = None
            self._try_post(post, "instagram", post.instagram_status, post.instagram_text, due_at)
            if not self._enable_twitter:
                continue
            if post.twitter_status != "SUCCESS" and is_duplicate_text(
                post.twitter_text, seen_twitter_texts
            ):
                mark_failed(
                    self._connection,
                    post_id=post.id,
                    service="twitter",
                    error="類似投稿のためXへの投稿をスキップしました（凍結対策）",
                )
                continue
            tweet_text = diversify_hashtags(strip_urls(post.twitter_text), index=post.id)
            self._try_post(post, "twitter", post.twitter_status, tweet_text, due_at)
            seen_twitter_texts.append(post.twitter_text)

    def _publish_media_manifest(self, manifest_path: Path) -> None:
        post: Post | None = None
        media_publisher = self._media_publisher
        try:
            if media_publisher is None:
                raise RuntimeError("画像公開処理が設定されていません")
            payload = _read_manifest(manifest_path)
            image_name = _required_string(payload, "image")
            category = _required_string(payload, "category")
            image_path = manifest_path.parent / image_name
            instagram_text = _required_string(payload, "instagram_text")
            twitter_text = _required_string(payload, "twitter_text")
            source_key = manifest_path.relative_to(self._layout.root).as_posix()
            post = get_post_by_source_key(self._connection, source_key)
            if post is None:
                post_id = add_pending_post(
                    self._connection,
                    source_key=source_key,
                    image_path=str(image_path),
                    instagram_text=instagram_text,
                    twitter_text=twitter_text,
                    publish_at=None,
                )
                post = get_post_by_source_key(self._connection, source_key)
                if post is None or post.id != post_id:
                    raise RuntimeError("画像公開用の投稿レコードを取得できませんでした")
            if post.media_status == "SUCCESS":
                return
            image_url = media_publisher.publish(image_path, category)
            media_publisher.wait_until_available(image_url)
        except Exception as exc:  # noqa: BLE001 - continue with the next input
            if post is not None:
                mark_media_failed(self._connection, post_id=post.id, error=str(exc))
            return
        archive_image_path = self._archive_inputs(manifest_path, image_path)
        mark_media_success(
            self._connection,
            post_id=post.id,
            archive_image_path=str(archive_image_path),
            image_url=image_url,
        )

    def _archive_inputs(self, manifest_path: Path, image_path: Path) -> Path:
        self._layout.archive.mkdir(parents=True, exist_ok=True)
        archive_image_path = self._layout.archive / image_path.name
        shutil.move(str(image_path), archive_image_path)
        shutil.move(str(manifest_path), self._layout.archive / manifest_path.name)
        return archive_image_path

    def _try_post(
        self, post: Post, service: str, status: str, text: str, due_at: str | None
    ) -> None:
        if status == "SUCCESS":
            return
        try:
            if self._provider is None:
                raise RuntimeError("SNS投稿処理が設定されていません")
            provider_id = self._provider.post(
                service=service, text=text, image_url=post.image_url, due_at=due_at
            )
        except Exception as exc:  # noqa: BLE001 - continue with the other service
            mark_failed(self._connection, post_id=post.id, service=service, error=str(exc))
        else:
            mark_success(self._connection, post_id=post.id, service=service, buffer_id=provider_id)

    @staticmethod
    def _publish_at(path: Path) -> str:
        return path.name


def _next_schedule_slots(
    connection: sqlite3.Connection,
    *,
    count: int,
    now: datetime,
    rng: random.Random | None = None,
) -> list[str]:
    if count == 0:
        return []
    rng = rng if rng is not None else random.Random()
    latest = connection.execute(
        "SELECT MAX(publish_at) FROM posts WHERE publish_at <> ''"
    ).fetchone()[0]
    cursor = now.astimezone(_JST).replace(second=0, microsecond=0)
    if latest:
        latest_time = datetime.fromisoformat(str(latest)).astimezone(_JST)
        if latest_time >= cursor:
            cursor = latest_time + timedelta(minutes=1)
    slots: list[str] = []
    while len(slots) < count:
        for hour in DailyBatch.SCHEDULE_HOURS_JST:
            candidate = cursor.replace(hour=hour, minute=0)
            if candidate <= cursor:
                continue
            jitter = rng.randint(0, SCHEDULE_JITTER_MAX_MINUTES)
            slots.append((candidate + timedelta(minutes=jitter)).isoformat())
            cursor = candidate
            if len(slots) == count:
                break
        cursor = (cursor + timedelta(days=1)).replace(hour=0, minute=0)
    return slots


_JST = timezone(timedelta(hours=9))


def _read_manifest(path: Path) -> dict[str, object]:
    with path.open(encoding="utf-8") as file:
        value = json.load(file)
    if not isinstance(value, dict):
        raise ValueError(f"投稿JSONはオブジェクトである必要があります: {path.name}")
    return value


def _required_string(payload: dict[str, object], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"投稿JSONの{key}が未設定です")
    return value
