"""SocialCaster 自動実行ラッパー用のDBカウント出力。

秘密情報は一切扱わず、posts テーブルの状態カウントだけを1行で出力する。
`run-socialcaster.ps1` が publish-media / publish-social の前後で呼び出し、
差分から「プロセス1成功」の判定とレポートを組み立てるために使う。

出力例:
    MEDIA_SUCCESS=12 MEDIA_FAILED=0 IG_SUCCESS=6 IG_FAILED=0 X_SUCCESS=6 X_FAILED=0
"""

import os
from pathlib import Path

from social_caster.config import load_dotenv
from social_caster.database import connect


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
    print(" ".join(f"{key}={value}" for key, value in values.items()))


if __name__ == "__main__":
    main()
