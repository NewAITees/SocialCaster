# Social Caster MVP

Buffer APIを使って、InstagramとXへ画像付き投稿を個別配信するPythonサービスです。

## 前提

Buffer APIはGraphQLで、エンドポイントは `https://api.buffer.com` です。InstagramとXはBuffer上の別チャンネルとして、それぞれの`channelId`へ投稿します。

画像は、独立した`NewAITees`リポジトリへコピーしてローカルGitでコミット・pushし、GitHub Pagesの公開URLを生成します。そのURLをBufferへ渡します。`NewAITees`は親リポジトリへ取り込まず、別リポジトリとして管理します。

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

投稿登録の`publish-at`はタイムゾーン付きISO 8601日時で指定します。

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

## フォルダ入力と日次実行

別PCから画像だけを`input/inbox/`へ置き、[AI入力指示書.md](AI入力指示書.md)をCodexまたはClaude Desktopへ渡します。AIは画像ごとにInstagram本文、X本文、カテゴリ、投稿日時を含むJSONを作成し、画像と一緒に`input/ready/`へ移動します。日次バッチが`NewAITees`へ画像を登録して公開URLを生成します。

`NEWAITEES_PATH`には、ローカルにcloneした独立リポジトリのパスを設定します。実行環境のGitに、対象リポジトリへpushできる認証情報を設定してください。

日次バッチは次のコマンドで実行します。

```powershell
uv run python -m social_caster.cli daily-batch
```

Windowsタスクスケジューラへの登録:

```powershell
PowerShell -ExecutionPolicy Bypass -File scripts/register_daily_task.ps1
```

成功した入力は`input/posted/`、失敗した入力は`input/failed/`へ移動します。

## 検証

```powershell
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run mypy .
```
