"""Command-line entry points for the MVP."""

import argparse
import logging
import os
from datetime import datetime
from pathlib import Path

from social_caster.batch import DailyBatch, FolderLayout
from social_caster.buffer_client import BufferClient
from social_caster.config import Settings
from social_caster.database import add_post, connect
from social_caster.newaitees import NewAITeesPublisher
from social_caster.provider import BufferProvider
from social_caster.scheduler import Scheduler


def main() -> None:
    parser = argparse.ArgumentParser(prog="social-caster")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("init-db")
    subparsers.add_parser("auth-check")
    subparsers.add_parser("daily-batch")
    subparsers.add_parser("publish-media")
    subparsers.add_parser("publish-social")
    add_parser = subparsers.add_parser("add-post")
    add_parser.add_argument("--image-path", required=True)
    add_parser.add_argument("--image-url", required=True)
    add_parser.add_argument("--instagram-text", required=True)
    add_parser.add_argument("--twitter-text", required=True)
    add_parser.add_argument("--publish-at", required=True, help="ISO 8601日時")
    subparsers.add_parser("run-once")
    subparsers.add_parser("run")
    args = parser.parse_args()

    if args.command == "init-db":
        connection = connect(Path(os.getenv("DATABASE_PATH", "database/posts.db")))
        return
    if args.command == "auth-check":
        api_key = os.getenv("BUFFER_API_KEY")
        if not api_key:
            raise ValueError("BUFFER_API_KEYが未設定です。`.env`へ設定してください")
        client = BufferClient(api_key)
        account = client.get_account()["account"]
        print(f"Buffer認証成功: {account['name']}")
        for organization in account["organizations"]:
            print(f"Organization: {organization['name']} ({organization['id']})")
            for channel in client.get_channels(str(organization["id"])):
                print(f"  {channel['service']}: {channel['name']} ({channel['id']})")
        return
    database_path = Path(os.getenv("DATABASE_PATH", "database/posts.db"))
    if args.command == "publish-media":
        connection = connect(database_path)
        batch = DailyBatch(
            connection,
            None,
            FolderLayout(Path("input")),
            _new_media_publisher(),
        )
        batch.publish_media_once()
        return

    settings = Settings.from_env()
    connection = connect(settings.database_path)
    if args.command in {"daily-batch", "publish-social"}:
        provider = BufferProvider(
            BufferClient(settings.buffer_api_key),
            settings.instagram_channel_id,
            settings.x_channel_id,
        )
        if args.command == "publish-social":
            DailyBatch(
                connection, provider, FolderLayout(Path("input")), None
            ).publish_social_once()
            return
        DailyBatch(
            connection,
            provider,
            FolderLayout(Path("input")),
            _new_media_publisher(),
        ).run_once()
        return
    if args.command == "add-post":
        _validate_datetime(args.publish_at)
        post_id = add_post(
            connection,
            image_path=args.image_path,
            image_url=args.image_url,
            instagram_text=args.instagram_text,
            twitter_text=args.twitter_text,
            publish_at=args.publish_at,
        )
        print(post_id)
        return

    logging.basicConfig(filename=settings.log_path, level=logging.INFO)
    provider = BufferProvider(
        BufferClient(settings.buffer_api_key),
        settings.instagram_channel_id,
        settings.x_channel_id,
    )
    scheduler = Scheduler(connection, provider)
    if args.command == "run-once":
        scheduler.process_once()
    else:
        scheduler.run_forever(settings.poll_interval_seconds)


def _validate_datetime(value: str) -> None:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("publish_atにはタイムゾーンを指定してください")


def _new_media_publisher() -> NewAITeesPublisher:
    return NewAITeesPublisher(
        Path(os.getenv("NEWAITEES_PATH", "NewAITees")),
        branch=os.getenv("NEWAITEES_BRANCH", "main"),
        pages_base_url=os.getenv(
            "NEWAITEES_PAGES_BASE_URL", "https://newaitees.github.io/NewAITees"
        ),
    )


if __name__ == "__main__":
    main()
