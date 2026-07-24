# 入力フォルダ運用

## 1. 画像を置く

別PCから画像ファイルを`input/inbox/`へコピーします。画像ファイル以外は置きません。

## 2. CodexまたはClaude Desktopへ依頼する

次の指示を渡します。

```text
input/inbox/ にある未処理画像をファイル名順に処理してください。

画像ごとに以下を行ってください。
1. 画像の内容を確認する
2. Instagram向けの詳しい説明文を日本語で作る
3. X向けに280文字以内の短い本文を作る
4. 投稿日時を確認できない場合は、publish_atを依頼者に質問する
5. 元画像と同じファイル名のJSONをinput/ready/へ作成する
6. 画像もinput/ready/へ移動する

JSON形式:
{
  "image": "画像ファイル名.jpg",
  "category": "horror",
  "instagram_text": "Instagram本文",
  "twitter_text": "X本文",
  "publish_at": "2026-07-25T09:00:00+09:00"
}

画像とJSONのファイル名は一致させ、JSONを先に作らないでください。
処理済み画像は再処理しないでください。
```

画像は日次バッチがNEWAITEESへGit commit・pushし、GitHub Pages URLを自動生成します。`image_url`の入力は不要です。

## 3. 日次バッチ

日次バッチは`input/ready/`と`input/failed/`をファイル名・投稿日時順に処理します。

- 両SNS成功: `input/posted/`へ移動
- 片方でも失敗: `input/failed/`へ移動
- 次回起動時: 失敗したSNSだけ再送
