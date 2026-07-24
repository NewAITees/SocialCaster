"""SQLite persistence for posts and per-channel delivery state."""

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from social_caster.content import validate_platform_texts

SCHEMA = """
CREATE TABLE IF NOT EXISTS posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    image_path TEXT NOT NULL,
    image_url TEXT NOT NULL,
    instagram_text TEXT NOT NULL,
    twitter_text TEXT NOT NULL,
    publish_at TEXT NOT NULL,
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


@dataclass(frozen=True)
class Post:
    id: int
    image_path: str
    image_url: str
    instagram_text: str
    twitter_text: str
    publish_at: str
    instagram_status: str
    twitter_status: str


def connect(path: Path | str) -> sqlite3.Connection:
    db_path = Path(path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute(SCHEMA)
    _migrate(connection)
    connection.commit()
    return connection


def add_post(
    connection: sqlite3.Connection,
    *,
    source_key: str | None = None,
    image_path: str,
    image_url: str,
    instagram_text: str,
    twitter_text: str,
    publish_at: str,
) -> int:
    validate_platform_texts(instagram_text=instagram_text, twitter_text=twitter_text)
    if not image_url.startswith("https://"):
        raise ValueError("image_urlはBufferから取得可能なhttps:// URLである必要があります")
    now = _utc_now()
    cursor = connection.execute(
        """
        INSERT INTO posts (
            image_path, image_url, instagram_text, twitter_text, publish_at,
            source_key, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            image_path,
            image_url,
            instagram_text,
            twitter_text,
            publish_at,
            source_key,
            now,
            now,
        ),
    )
    connection.commit()
    if cursor.lastrowid is None:
        raise RuntimeError("投稿IDを取得できませんでした")
    return int(cursor.lastrowid)


def get_post_by_source_key(connection: sqlite3.Connection, source_key: str) -> Post | None:
    row = connection.execute(
        """
        SELECT id, image_path, image_url, instagram_text, twitter_text, publish_at,
               instagram_status, twitter_status
        FROM posts WHERE source_key = ?
        """,
        (source_key,),
    ).fetchone()
    return _post_from_row(row) if row else None


def due_posts(connection: sqlite3.Connection, *, now: str | None = None) -> list[Post]:
    current = now or _utc_now()
    rows = connection.execute(
        """
        SELECT id, image_path, image_url, instagram_text, twitter_text, publish_at,
               instagram_status, twitter_status
        FROM posts
        WHERE publish_at <= ?
          AND (instagram_status != 'SUCCESS' OR twitter_status != 'SUCCESS')
        ORDER BY publish_at, id
        """,
        (current,),
    ).fetchall()
    return [_post_from_row(row) for row in rows]


def mark_success(
    connection: sqlite3.Connection, *, post_id: int, service: str, buffer_id: str
) -> None:
    _update_service(connection, post_id, service, "SUCCESS", buffer_id)


def mark_failed(connection: sqlite3.Connection, *, post_id: int, service: str, error: str) -> None:
    _update_service(connection, post_id, service, "FAILED", None, error)


def _update_service(
    connection: sqlite3.Connection,
    post_id: int,
    service: str,
    status: str,
    buffer_id: str | None,
    error: str | None = None,
) -> None:
    if service not in {"instagram", "twitter"}:
        raise ValueError(f"未対応のサービスです: {service}")
    status_column = f"{service}_status"
    id_column = f"{service}_buffer_id"
    now = _utc_now()
    connection.execute(
        f"UPDATE posts SET {status_column} = ?, {id_column} = ?, last_error = ?, updated_at = ? "
        "WHERE id = ?",
        (status, buffer_id, error, now, post_id),
    )
    connection.commit()


def _post_from_row(row: sqlite3.Row) -> Post:
    return Post(
        id=int(row["id"]),
        image_path=str(row["image_path"]),
        image_url=str(row["image_url"]),
        instagram_text=str(row["instagram_text"]),
        twitter_text=str(row["twitter_text"]),
        publish_at=str(row["publish_at"]),
        instagram_status=str(row["instagram_status"]),
        twitter_status=str(row["twitter_status"]),
    )


def _migrate(connection: sqlite3.Connection) -> None:
    columns = {
        str(row["name"]) for row in connection.execute("PRAGMA table_info(posts)").fetchall()
    }
    if "source_key" not in columns:
        connection.execute("ALTER TABLE posts ADD COLUMN source_key TEXT")
        connection.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_posts_source_key ON posts(source_key)"
        )
        connection.commit()


def _utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")
