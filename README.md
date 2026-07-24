# Social Caster MVP

Buffer APIを使って、InstagramとXへ画像付き投稿を個別配信するPythonサービスです。

## 前提

Buffer APIはGraphQLで、エンドポイントは `https://api.buffer.com` です。InstagramとXはBuffer上の別チャンネルとして、それぞれの`channelId`へ投稿します。

Bufferは画像ファイルそのものを受け取るのではなく、Bufferが取得できる公開HTTPS画像URLを使って投稿します。そのため、画像は独立した`NewAITees`リポジトリへカテゴリ別に登録し、ローカルGitでcommit・pushしてGitHub Pagesで公開します。生成された公開URLをBufferへ渡します。`NewAITees`は親リポジトリへ取り込まず、別リポジトリとして管理します。

## セットアップ

```powershell
Copy-Item .env.example .env
uv sync --dev
```

BufferのSettings → APIでAPIキーを作成します。APIキーはチャットやソースコードへ貼らず、`.env`だけに保存してください。[Buffer公式認証手順](https://developers.buffer.com/guides/authentication.html)

まず認証情報だけを設定します。

```text
BUFFER_API_KEY=...
```

認証と接続済みチャンネルを確認します。

```powershell
uv run python -m social_caster.cli auth-check
```

表示されたInstagramとXのチャンネルIDを、`.env`へ追加します。

```text
BUFFER_API_KEY=...
BUFFER_INSTAGRAM_CHANNEL_ID=...
BUFFER_X_CHANNEL_ID=...
```

## CLI

DB初期化はBuffer認証情報なしで実行できます。

```powershell
uv run python -m social_caster.cli init-db
```

手動登録の`publish-at`はタイムゾーン付きISO 8601日時で指定します。`image-url`は、すでに公開済みのHTTPS画像を手動登録する場合にだけ使います。通常の入力経路では、先にNewAITeesへ登録してURLを生成します。

```powershell
uv run python -m social_caster.cli add-post `
  --image-path images/image001.png `
  --image-url https://example.com/image001.png `
  --instagram-text "Instagram本文 #example" `
  --twitter-text "X本文" `
  --publish-at 2026-07-24T12:00:00+09:00
```

期限到来済みの投稿を一度処理する場合:

```powershell
uv run python -m social_caster.cli run-once
```

5分間隔で常駐する場合:

```powershell
uv run python -m social_caster.cli run
```

Instagramで失敗してもXは独立して処理され、失敗したサービスだけ次回再送されます。

## 本文ルール

- Instagram本文とX本文は別々に登録します。
- Instagramは説明・改行・ハッシュタグを含む長文向けです。MVPでは2,200文字以内を検証します。
- Xは要点を短くまとめ、MVPでは通常投稿の280文字以内を検証します。X Premiumの長文投稿はMVP対象外です。
- 画像URL、本文、投稿日時は両SNSで共通ですが、本文は共有しません。

## 入力・画像公開・SNS投稿

別PCから画像をSMB共有の`\\DESKTOP-OBMGMM7\SocialCasterInput\inbox\`へ置き、[AI入力指示書.md](AI入力指示書.md)をCodexまたはClaude Desktopへ渡します。AIは画像と同じフォルダにInstagram本文、X本文、カテゴリ、投稿日時を含むJSONを作成します。

日次処理は二段階です。

1. JSONの`category`に従って画像をNewAITeesへ登録し、commit・pushしてGitHub Pagesの公開URLを確定する
2. 公開URLを使い、Buffer経由でInstagramとXへ別々に投稿する

画像公開が完了するまでBufferは呼び出しません。処理状態とSNSごとの再送状態はSQLiteで管理します。SMB設定方法は[input/README.md](input/README.md)を参照してください。共有するのは`input/`だけで、リポジトリ全体は共有しません。

`NEWAITEES_PATH`には、ローカルにcloneした独立リポジトリのパスを設定します。実行環境のGitに、対象リポジトリへpushできる認証情報を設定してください。

日次バッチは次のコマンドで実行します。

```powershell
# 画像をNewAITeesへ公開する第1段階
uv run python -m social_caster.cli publish-media

# 公開済みURLをBufferへ投稿する第2段階
uv run python -m social_caster.cli publish-social

# 上記2段階を連続実行
uv run python -m social_caster.cli daily-batch
```

Windowsタスクスケジューラへの登録:

```powershell
PowerShell -ExecutionPolicy Bypass -File scripts/register_daily_task.ps1
```

入力ファイルは`input/inbox/`に置いたままにし、二重処理防止と再送状態はSQLiteで管理します。

## 検証

```powershell
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run mypy .
```
