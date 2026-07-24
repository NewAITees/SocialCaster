# SNS自動投稿ツール 要件定義書（MVP）

## 目的

InstagramとX（Twitter）へ画像付き投稿を自動で配信する。

投稿内容はローカルPC上で管理し、一度登録した投稿を指定日時に自動配信できるようにする。

運用はできるだけ無料サービスを利用し、将来的に他SNSへの拡張を考慮した設計とする。

---

# システム構成

```text
入力画像・投稿JSON
        │
        ▼
画像公開処理(Python)
        │
        └── NewAITeesへカテゴリ別登録・GitHub Pages公開
                    │
                    ▼
              公開HTTPS画像URL
                    │
                    ▼
投稿管理(SQLite)
        │
        ▼
SNS投稿処理(Python)
        │
        ├── Buffer（X）
        └── Buffer（Instagram）
```

Bufferは画像ファイルそのもののアップロード先ではなく、Bufferが取得できる公開HTTPS画像URLを使って投稿する。そのため、既存のNewAITeesリポジトリへ画像をカテゴリ別に登録し、GitHub Pagesで公開したURLをBufferへ渡す。NewAITeesはSocialCasterの親リポジトリへ取り込まず、独立リポジトリとして管理する。

※ 将来的にInstagramだけMeta Business Suiteへ変更できるように設計する。

---

# 対応SNS

初期対応

* Instagram
* X（Twitter）

将来追加予定

* Threads
* Pinterest
* Bluesky
* Facebook

---

# 投稿データ

画像はSQLiteへ保存しない。

```text
/images/
    image001.png
    image002.png
```

SQLiteには画像パスのみ保存する。

## postsテーブル

| 項目               | 内容           |
| ---------------- | ------------ |
| id               | 投稿ID         |
| image_path       | 画像ファイルパス     |
| image_url        | NewAITeesの公開HTTPS画像URL |
| instagram_text   | Instagram用本文 |
| twitter_text     | X用本文         |
| publish_at       | 投稿予定日時       |
| media_status     | 画像公開処理の状態 |
| instagram_status | 待機・投稿済・失敗    |
| twitter_status   | 待機・投稿済・失敗    |
| created_at       | 登録日時         |
| updated_at       | 更新日時         |

---

# 投稿方式

InstagramとXは別々に管理する。

Instagram

* 長文可
* ハッシュタグ多め

X

* 短文
* X向け文章
* 必要ならInstagramプロフィールURLを付与

---

# 投稿フロー

```text
第1段階：画像公開

SMB共有のinboxから画像・投稿JSONを取得

↓

JSONのcategoryに従ってNewAITees/assets/gallery/<category>/へ登録

↓

NewAITeesをcommit・push

↓

GitHub Pagesへの反映を確認し、公開URLをSQLiteへ保存

↓

第2段階：SNS投稿

公開URLが保存済みで投稿予定時刻になったデータを取得

↓

BufferのInstagramチャンネルへ投稿

↓

BufferのXチャンネルへ投稿

↓

SNSごとのステータス更新
```

画像公開が成功して公開URLが確定するまで、Bufferは呼び出さない。InstagramとXには同じ公開画像URLを渡すが、本文とステータスはSNSごとに分ける。

日次実行では、第1段階完了後に第2段階を実行する。障害時はSQLiteの状態を使って、画像公開または失敗したSNS投稿から再開する。

旧方式のように、投稿状態を`ready`・`posted`・`failed`フォルダへ移動して管理しない。入力はSMB共有の`input/inbox/`に集約し、処理状態はSQLiteで管理する。

---

# スケジューリング

Windowsタスクスケジューラは使用しない。

Pythonサービスを常駐させる。

```text
while True

    投稿予定取得

    未投稿確認

    投稿

    5分待機
```

Windows再起動後は自動起動する。

---

# 障害対策

PC停止

↓

起動後に未投稿を確認

↓

投稿時刻を過ぎている場合は即投稿

これにより

* Windows Update
* 停電
* 手動再起動

でも投稿漏れを最小化する。

---

# 投稿状態

Instagram

* WAIT
* SUCCESS
* FAILED

X

* WAIT
* SUCCESS
* FAILED

片方だけ失敗しても再送可能。

---

# API

投稿サービスはSNSごとに分離する。

```text
SocialProvider

├─ BufferProvider
├─ MetaProvider（将来）
├─ XProvider（将来）
```

これにより配信先を容易に追加・変更できる。

---

# ディレクトリ構成

```text
project/

    images/

    database/
        posts.db

    scheduler.py

    providers/
        buffer_provider.py

    config.py

    logs/
```

---

# MVPの機能

* SQLiteで投稿管理
* 画像ファイル管理
* Instagram・Xへの画像付き投稿
* SNSごとに本文を変更可能
* 投稿日時指定
* 常駐サービスによる自動投稿
* 投稿履歴管理
* 失敗時の再送
* ログ出力

---

# 将来追加したい機能

* WebUI
* カレンダー表示
* AIによる本文生成
* AIによるハッシュタグ生成
* 複数画像投稿
* 動画投稿
* リール対応
* Pinterest対応
* Bluesky対応
* Threads対応
* 投稿プレビュー
* 投稿分析
* AIBackgroundWorkerとの連携
* Buffer以外のAPIへの切り替え
