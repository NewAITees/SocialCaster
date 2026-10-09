"""SocialCaster 自動実行ラッパー用のDBカウント・Buffer在庫出力。

posts テーブルの状態カウントと、Bufferから読んだサービス別の予約在庫・空き枠・
補充必要数を1行で出力する。
`automations/socialcaster-process-1-prepare-and-publish-media-v2/run.ps1` が
在庫トップアップのループで反復ごとに呼び出し、サービスごとの NEED から
今回処理すべき件数を決めるために使う。

在庫はローカルDBの推定ではなくBuffer APIの実数を基準にする（2026-10-09:
ローカル推定とBuffer実数がずれていないか確認済みだが、ずれを検出できるのは
実数を見たときだけなので推定へは戻さない）。取得に失敗した場合はこのプロセスを
異常終了させる。黙ってローカル推定へ退避しない。

出力例:
    MEDIA_SUCCESS=12 MEDIA_FAILED=0 IG_SUCCESS=6 IG_FAILED=0 X_SUCCESS=6 X_FAILED=0
    SCHEDULED_LIMIT=10 TARGET_STOCK=9
    STOCK_INSTAGRAM=6 ROOM_INSTAGRAM=4 NEED_INSTAGRAM=3
    STOCK_PINTEREST=9 ROOM_PINTEREST=1 NEED_PINTEREST=0
"""

import os
from pathlib import Path

from social_caster.buffer_client import BufferClient
from social_caster.config import Settings, load_dotenv
from social_caster.database import connect
from social_caster.stock import read_service_stock, service_channels


def main() -> None:
    load_dotenv()
    settings = Settings.from_env()
    database_path = Path(os.getenv("DATABASE_PATH", "database/posts.db"))
    connection = connect(database_path)

    def count(where: str) -> int:
        row = connection.execute(f"SELECT COUNT(*) FROM posts WHERE {where}").fetchone()
        return int(row[0])

    values: dict[str, int] = {
        "MEDIA_SUCCESS": count("media_status = 'SUCCESS'"),
        "MEDIA_FAILED": count("media_status = 'FAILED'"),
        "IG_SUCCESS": count("instagram_status = 'SUCCESS'"),
        "IG_FAILED": count("instagram_status = 'FAILED'"),
        "X_SUCCESS": count("twitter_status = 'SUCCESS'"),
        "X_FAILED": count("twitter_status = 'FAILED'"),
    }

    client = BufferClient(settings.buffer_api_key)
    channels = service_channels(settings)
    plan = read_service_stock(client, channels=channels, target_stock=settings.target_stock)

    values["PINTEREST_ENABLED"] = int(settings.enable_pinterest)
    values["TARGET_STOCK"] = settings.target_stock
    for service, stock in plan.items():
        key = service.upper()
        values[f"STOCK_{key}"] = stock.stock
        values[f"ROOM_{key}"] = stock.room
        values[f"NEED_{key}"] = stock.need
    # どのサービスでも空き枠の算出に使った上限は同一（Bufferの予約枠は組織単位ではなく
    # チャンネル単位で適用されているため、値そのものはサービス間で変わらない）。
    any_service = next(iter(plan.values()))
    values["SCHEDULED_LIMIT"] = any_service.stock + any_service.room

    print(" ".join(f"{key}={value}" for key, value in values.items()))


if __name__ == "__main__":
    main()
