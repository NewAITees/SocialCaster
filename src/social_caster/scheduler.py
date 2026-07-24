"""Polling scheduler for overdue posts."""

import logging
import sqlite3
import time
from collections.abc import Callable

from social_caster.database import due_posts, mark_failed, mark_success
from social_caster.provider import SocialProvider


class Scheduler:
    def __init__(
        self,
        connection: sqlite3.Connection,
        provider: SocialProvider,
        *,
        logger: logging.Logger | None = None,
    ) -> None:
        self._connection = connection
        self._provider = provider
        self._logger = logger or logging.getLogger(__name__)

    def process_once(self) -> None:
        for post in due_posts(self._connection):
            self._try_post(
                post.id, "instagram", post.instagram_status, post.instagram_text, post.image_url
            )
            self._try_post(
                post.id, "twitter", post.twitter_status, post.twitter_text, post.image_url
            )

    def run_forever(
        self, interval_seconds: int, sleep: Callable[[float], None] = time.sleep
    ) -> None:
        while True:
            self.process_once()
            sleep(interval_seconds)

    def _try_post(self, post_id: int, service: str, status: str, text: str, image_url: str) -> None:
        if status == "SUCCESS":
            return
        try:
            provider_id = self._provider.post(service=service, text=text, image_url=image_url)
        except Exception as exc:  # noqa: BLE001 - one channel must not stop the other
            message = str(exc)
            mark_failed(self._connection, post_id=post_id, service=service, error=message)
            self._logger.exception("投稿失敗 post_id=%s service=%s", post_id, service)
        else:
            mark_success(self._connection, post_id=post_id, service=service, buffer_id=provider_id)
            self._logger.info("投稿成功 post_id=%s service=%s", post_id, service)
