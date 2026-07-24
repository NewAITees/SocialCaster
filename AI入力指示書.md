# Codex／Claude Desktop向け入力指示書

あなたはSocial Casterの投稿データ作成担当です。

`input/inbox/`にある画像をファイル名順に1件ずつ処理し、画像ごとに同名JSONを`input/ready/`へ作成してください。画像も`input/ready/`へ移動してください。

JSONは次の形式です。

```json
{
  "image": "画像ファイル名.jpg",
  "category": "horror",
  "instagram_text": "詳しい説明文、改行、ハッシュタグを含めてよい",
  "twitter_text": "X向けの短い本文。280文字以内",
  "publish_at": "2026-07-25T09:00:00+09:00"
}
```

ルール:

- InstagramとXの本文は別々に考える
- X本文は280文字を超えない
- 投稿日時が不明なら勝手に決めず、処理を止めて質問する
- `category`はNEWAITEESの既存カテゴリから選ぶ（abstract_image、botanical、bottled_image、horror、joke、monochrome、other）
- JSONと画像のファイル名を一致させる
- すでに`input/ready/`や`input/posted/`にある画像は再処理しない
