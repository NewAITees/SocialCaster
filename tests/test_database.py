import sqlite3
from pathlib import Path

import pytest

from social_caster.database import (
    add_post,
    connect,
    due_posts,
    mark_failed,
    mark_success,
    stock_count,
)


def test_due_post_excludes_twitter_only_failure() -> None:
    connection = connect(":memory:")
    post_id = add_post(
        connection,
        image_path="images/a.jpg",
        image_url="https://example.com/a.jpg",
        instagram_text="instagram",
        twitter_text="x",
        category="other",
        pinterest_text=None,
        pinterest_title=None,
        publish_at="2026-01-01T00:00:00+00:00",
    )
    mark_success(connection, post_id=post_id, service="instagram", buffer_id="ig-1")
    mark_failed(connection, post_id=post_id, service="twitter", error="temporary")

    posts = due_posts(connection, now="2026-01-01T00:01:00+00:00")

    assert posts == []


def test_local_image_url_is_rejected() -> None:
    connection = connect(":memory:")

    with pytest.raises(ValueError, match="https://"):
        add_post(
            connection,
            image_path="images/a.jpg",
            image_url="C:/images/a.jpg",
            instagram_text="instagram",
            twitter_text="x",
            category="other",
            pinterest_text=None,
            pinterest_title=None,
            publish_at="2026-01-01T00:00:00+00:00",
        )


def test_stock_count_only_includes_future_instagram_success() -> None:
    connection = connect(":memory:")
    future_id = add_post(
        connection,
        image_path="images/future.jpg",
        image_url="https://example.com/future.jpg",
        instagram_text="future",
        twitter_text="future",
        category="other",
        pinterest_text="future pin",
        pinterest_title="future pin",
        publish_at="2026-09-02T00:00:00+00:00",
    )
    past_id = add_post(
        connection,
        image_path="images/past.jpg",
        image_url="https://example.com/past.jpg",
        instagram_text="past",
        twitter_text="past",
        category="other",
        pinterest_text="past pin",
        pinterest_title="past pin",
        publish_at="2026-08-01T00:00:00+00:00",
    )
    failed_id = add_post(
        connection,
        image_path="images/failed.jpg",
        image_url="https://example.com/failed.jpg",
        instagram_text="failed",
        twitter_text="failed",
        category="other",
        pinterest_text="failed pin",
        pinterest_title="failed pin",
        publish_at="2026-09-03T00:00:00+00:00",
    )
    mark_success(connection, post_id=future_id, service="instagram", buffer_id="ig-future")
    mark_success(connection, post_id=past_id, service="instagram", buffer_id="ig-past")
    mark_failed(connection, post_id=failed_id, service="instagram", error="failed")

    mark_success(connection, post_id=future_id, service="pinterest", buffer_id="pin-future")
    mark_success(connection, post_id=past_id, service="pinterest", buffer_id="pin-past")
    mark_failed(connection, post_id=failed_id, service="pinterest", error="failed")

    now = "2026-08-30T00:00:00+00:00"
    assert stock_count(connection, service="instagram", now=now) == 1
    assert stock_count(connection, service="pinterest", now=now) == 1


def test_stock_count_rejects_unsupported_service() -> None:
    connection = connect(":memory:")

    with pytest.raises(ValueError, match="未対応のサービス"):
        stock_count(connection, service="twitter")


def test_stock_count_does_not_treat_past_jst_time_as_future() -> None:
    connection = connect(":memory:")
    post_id = add_post(
        connection,
        image_path="images/past-jst.jpg",
        image_url="https://example.com/past-jst.jpg",
        instagram_text="past JST",
        twitter_text="past JST",
        category="other",
        pinterest_text=None,
        pinterest_title=None,
        publish_at="2026-08-30T08:00:00+09:00",
    )
    mark_success(connection, post_id=post_id, service="instagram", buffer_id="ig-past-jst")

    assert stock_count(connection, service="instagram", now="2026-08-30T00:00:00+00:00") == 0


def test_connect_migrates_existing_database(tmp_path: Path) -> None:
    database_path = tmp_path / "legacy.db"
    legacy = sqlite3.connect(database_path)
    legacy.execute(
        """
        CREATE TABLE posts (
            id INTEGER PRIMARY KEY,
            image_path TEXT NOT NULL,
            archive_image_path TEXT,
            image_url TEXT NOT NULL,
            media_status TEXT NOT NULL DEFAULT 'WAIT',
            media_error TEXT,
            instagram_text TEXT NOT NULL,
            twitter_text TEXT NOT NULL,
            publish_at TEXT NOT NULL DEFAULT '',
            instagram_status TEXT NOT NULL DEFAULT 'WAIT',
            twitter_status TEXT NOT NULL DEFAULT 'WAIT',
            instagram_buffer_id TEXT,
            twitter_buffer_id TEXT,
            last_error TEXT,
            source_key TEXT UNIQUE,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    legacy.commit()
    legacy.close()

    connection = connect(database_path)
    columns = {
        str(row["name"]) for row in connection.execute("PRAGMA table_info(posts)").fetchall()
    }

    assert {
        "pinterest_status",
        "pinterest_buffer_id",
        "pinterest_text",
        "pinterest_title",
        "category",
    } <= columns
