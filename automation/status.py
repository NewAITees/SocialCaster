"""SocialCaster 自動実行ラッパー用のDBカウント出力。

秘密情報は一切扱わず、posts テーブルの状態カウントだけを1行で出力する。
`automations/socialcaster-process-1-prepare-and-publish-media-v2/run.ps1` が
在庫トップアップのループで反復ごとに呼び出し、サービス別在庫と REFILL から
今回処理すべき件数を決めるために使う。

出力例:
    MEDIA_SUCCESS=12 MEDIA_FAILED=0 IG_SUCCESS=6 IG_FAILED=0 X_SUCCESS=6 X_FAILED=0
    STOCK_INSTAGRAM=7 STOCK_PINTEREST=4
"""

import os
from pathlib import Path

from social_caster.batch import refill_amount
from social_caster.config import load_dotenv
from social_caster.database import connect, stock_count


def main() -> None:
    load_dotenv()
    database_path = Path(os.getenv("DATABASE_PATH", "database/posts.db"))
    connection = connect(database_path)

    def count(where: str) -> int:
        row = connection.execute(f"SELECT COUNT(*) FROM posts WHERE {where}").fetchone()
        return int(row[0])

    values = {
        "MEDIA_SUCCESS": count("media_status = 'SUCCESS'"),
        "MEDIA_FAILED": count("media_status = 'FAILED'"),
        "IG_SUCCESS": count("instagram_status = 'SUCCESS'"),
        "IG_FAILED": count("instagram_status = 'FAILED'"),
        "X_SUCCESS": count("twitter_status = 'SUCCESS'"),
        "X_FAILED": count("twitter_status = 'FAILED'"),
    }
    instagram_stock = stock_count(connection, service="instagram")
    pinterest_stock = stock_count(connection, service="pinterest")
    enable_pinterest = os.getenv("ENABLE_PINTEREST", "false").strip().lower() not in {
        "false",
        "0",
        "no",
    }
    enabled_stocks = [instagram_stock]
    if enable_pinterest:
        enabled_stocks.append(pinterest_stock)
    current_stock = min(enabled_stocks)
    target_stock = int(os.getenv("TARGET_STOCK", "9"))
    reservation_cap = int(os.getenv("BUFFER_RESERVATION_CAP", "10"))
    values.update(
        STOCK_INSTAGRAM=instagram_stock,
        STOCK_PINTEREST=pinterest_stock,
        PINTEREST_ENABLED=int(enable_pinterest),
        TARGET_STOCK=target_stock,
        RESERVATION_CAP=reservation_cap,
        REFILL=refill_amount(
            current_stock=current_stock,
            target_stock=target_stock,
            reservation_cap=reservation_cap,
        ),
    )
    print(" ".join(f"{key}={value}" for key, value in values.items()))


if __name__ == "__main__":
    main()
