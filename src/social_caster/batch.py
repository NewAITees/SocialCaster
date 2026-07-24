"""Daily folder-to-Buffer batch runner."""

import json
import shutil
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

from social_caster.database import (
    Post,
    add_post,
    get_post_by_source_key,
    mark_failed,
    mark_success,
)
from social_caster.provider import SocialProvider


class MediaPublisher(Protocol):
    def publish(self, image_path: Path, category: str) -> str:
        """Publish a local image and return its public URL."""

    def wait_until_available(self, url: str) -> None:
        """Wait until the public URL is served by the Pages deployment."""


@dataclass(frozen=True)
class FolderLayout:
    root: Path

    @property
    def ready(self) -> Path:
        return self.root / "ready"

    @property
    def failed(self) -> Path:
        return self.root / "failed"

    @property
    def posted(self) -> Path:
        return self.root / "posted"

    def ensure(self) -> None:
        for directory in (self.ready, self.failed, self.posted):
            directory.mkdir(parents=True, exist_ok=True)


class DailyBatch:
    def __init__(
        self,
        connection: sqlite3.Connection,
        provider: SocialProvider,
        layout: FolderLayout,
        media_publisher: MediaPublisher,
    ) -> None:
        self._connection = connection
        self._provider = provider
        self._layout = layout
        self._media_publisher = media_publisher

    def run_once(self) -> None:
        self._layout.ensure()
        inputs = sorted(
            (*self._layout.ready.glob("*.json"), *self._layout.failed.glob("*.json")),
            key=lambda path: (self._publish_at(path), path.name),
        )
        for manifest_path in inputs:
            self._process_manifest(manifest_path)

    def _process_manifest(self, manifest_path: Path) -> None:
        payload = _read_manifest(manifest_path)
        image_name = _required_string(payload, "image")
        category = _required_string(payload, "category")
        image_path = manifest_path.parent / image_name
        instagram_text = _required_string(payload, "instagram_text")
        twitter_text = _required_string(payload, "twitter_text")
        publish_at = _required_string(payload, "publish_at")
        source_key = manifest_path.name
        post = get_post_by_source_key(self._connection, source_key)
        if post is None:
            image_url = self._media_publisher.publish(image_path, category)
            self._media_publisher.wait_until_available(image_url)
            post_id = add_post(
                self._connection,
                source_key=source_key,
                image_path=str(image_path),
                image_url=image_url,
                instagram_text=instagram_text,
                twitter_text=twitter_text,
                publish_at=publish_at,
            )
            post = Post(
                post_id,
                str(image_path),
                image_url,
                instagram_text,
                twitter_text,
                publish_at,
                "WAIT",
                "WAIT",
            )
        due_at = publish_at if _is_future(publish_at) else None
        self._try_post(post, "instagram", post.instagram_status, post.instagram_text, due_at)
        self._try_post(post, "twitter", post.twitter_status, post.twitter_text, due_at)
        updated = get_post_by_source_key(self._connection, source_key)
        if (
            updated
            and updated.instagram_status == "SUCCESS"
            and updated.twitter_status == "SUCCESS"
        ):
            _move_bundle(manifest_path, self._layout.posted)
        else:
            _move_bundle(manifest_path, self._layout.failed)

    def _try_post(
        self, post: Post, service: str, status: str, text: str, due_at: str | None
    ) -> None:
        if status == "SUCCESS":
            return
        try:
            provider_id = self._provider.post(
                service=service, text=text, image_url=post.image_url, due_at=due_at
            )
        except Exception as exc:  # noqa: BLE001 - continue with the other service
            mark_failed(self._connection, post_id=post.id, service=service, error=str(exc))
        else:
            mark_success(self._connection, post_id=post.id, service=service, buffer_id=provider_id)

    @staticmethod
    def _publish_at(path: Path) -> str:
        try:
            return _required_string(_read_manifest(path), "publish_at")
        except (ValueError, OSError, json.JSONDecodeError):
            return "9999-12-31T23:59:59+00:00"


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


def _is_future(value: str) -> bool:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("publish_atにはタイムゾーンが必要です")
    return parsed > datetime.now(UTC)


def _move_bundle(manifest_path: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    image_name = _required_string(_read_manifest(manifest_path), "image")
    image_path = manifest_path.parent / image_name
    shutil.move(str(manifest_path), str(destination / manifest_path.name))
    if image_path.exists():
        shutil.move(str(image_path), str(destination / image_path.name))
