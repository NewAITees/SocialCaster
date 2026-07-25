# Codex Scheduled運用指示書

この文書は、CodexのScheduledへ登録するSocialCasterの定期処理用指示書です。

## 固定パス

- 作業ディレクトリ: `C:\projects\SocialCaster`
- 入力フォルダ: `C:\projects\SocialCaster\input\inbox`
- 処理済みアーカイブ: `C:\projects\SocialCaster\input\archive`
- NewAITeesリポジトリ: `C:\projects\SocialCaster\NewAITees`
- Python実行ファイル: `C:\projects\SocialCaster\.venv\Scripts\python.exe`
- SQLiteデータベース: `C:\projects\SocialCaster\database\posts.db`
- 環境設定: `C:\projects\SocialCaster\.env`

Codex Scheduledは、ローカルプロジェクトとして`C:\projects\SocialCaster`を指定してください。実行時は、このPCとCodexデスクトップアプリを起動したままにしてください。

`.env`の内容、Buffer APIキー、チャンネルIDは画面・チャット・ログへ出力しないでください。

## 運用順序

1. プロセス1を毎日実行する
2. プロセス2を、プロセス1の完了後に毎日実行する
3. 推奨時刻は、プロセス1を日本時間05:00、プロセス2を日本時間06:00とする
4. 1日あたり最大3画像だけを処理する

プロセス1は画像をNewAITeesへ公開します。プロセス2は公開済み画像のURLをBufferへ予約登録します。プロセス1でBufferを呼び出してはいけません。プロセス2でNewAITeesへ画像を追加してはいけません。

---

## Scheduledタスク1：プロセス1

### タスク名

`SocialCaster Process 1 - Prepare and Publish Media`

### 実行コマンド

作業ディレクトリ`C:\projects\SocialCaster`で、次を実行してください。

```powershell
C:\projects\SocialCaster\.venv\Scripts\python.exe -m social_caster.cli publish-media
```

### Codexへの指示文

あなたはSocialCasterのプロセス1担当です。

`C:\projects\SocialCaster\input\inbox`を確認し、画像ファイル名順に未処理画像を最大3枚選んでください。

対象条件:

- `.png`、`.jpg`、`.jpeg`だけを対象にする
- `.part`ファイルは対象外にする
- 画像と同名の`.json`が存在する画像は、JSONを再生成しない
- 1回の実行で新規JSONを最大3件だけ作成する
- NewAITeesへの公開成功後、画像とJSONは`C:\projects\SocialCaster\input\archive`へ移動される
- 投稿日時は設定しない

各画像を目視で分析し、画像と同じフォルダに同名JSONをUTF-8で作成してください。JSONの保存先は必ず次の形式にしてください。

```text
C:\projects\SocialCaster\input\inbox\画像ファイル名.json
```

### カテゴリ分類

`category`は次の既存カテゴリから必ず1つ選んでください。

- `abstract_image`: 抽象表現、幾何学、色や形が主役
- `botanical`: 植物、花、森、自然が主役
- `bottled_image`: 容器、瓶、球体、ミニチュア世界、閉じ込められた風景
- `horror`: 怪物、死体、恐怖、血、暗い廃墟、不気味な人影
- `joke`: 明確なジョーク、パロディ、コミカルな表現
- `monochrome`: 白黒、ほぼ無彩色、強いモノクロ表現
- `other`: 上記に分類できないもの

ファイル名だけでカテゴリを推測しないでください。画像の視覚内容を優先してください。複数候補がある場合は、主役となる視覚要素で分類してください。

### 画像分析

次の3点を内部で分析してください。ただし、分析結果そのものをInstagram本文へ貼り付けないでください。

1. 主要な視覚要素
2. 色使いと構図
3. 全体の印象と雰囲気

### Instagram本文の制作

`instagram_text`には、マーケティング文章とハッシュタグだけを入れてください。画像分析の箇条書きや「画像分析」という見出しは入れないでください。

マーケティング文章は次の条件で作成してください。

- 日本語250文字以内
- 英語250文字以内
- 最初の1文は、驚き・共感・問いかけを使った強いフック
- ENFPらしい直感的な印象
- 感情的なつながり
- 想像力豊かで前向き、エネルギッシュなトーン
- 少なくとも1つの比喩またはイメージ表現
- 小さなストーリー性
- 読者が共感、保存、シェアしたくなる内容
- 最後に軽いCTAを入れる
- Tシャツの宣伝を入れない

本文は次のように構成してください。

```text
日本語:
日本語のマーケティング文章

English:
English marketing text

#hashtag1 ... #hashtag20
```

### Instagramハッシュタグ

合計20個、すべて小文字で作成してください。次の4個は必須です。

```text
#stablediffusion #sd #newaitees #aiart
```

20個は次の内訳にしてください。

- 一般的なタグ: 5個
- オリジナルタグ: 5個
- 指定タグ: 5個（必須タグを含める）
- ユーザー視点タグ: 5個

タグの重複は禁止です。大文字を使わないでください。

### X本文の制作

`twitter_text`には、画像分析ではなくマーケティング内容を要約した投稿文だけを入れてください。

- 280文字以内
- 画像の主役と印象を短く伝える
- Instagramと同じ感情的・想像的な方向性にする
- フックまたは問いかけを含める
- 必要に応じて短いCTAを含める
- ハッシュタグは0〜2個まで
- Tシャツの宣伝を入れない

### JSON形式

```json
{
  "image": "画像ファイル名.jpg",
  "category": "horror",
  "instagram_text": "日本語・英語のマーケティング文章と20個の小文字ハッシュタグ",
  "twitter_text": "X向けの280文字以内の要約本文"
}
```

JSON作成後、次を確認してください。

- JSONが正しい形式である
- `image`のファイルが実際に存在する
- `category`が既存カテゴリのいずれかである
- Instagramのハッシュタグが20個で、すべて小文字である
- `#stablediffusion`、`#sd`、`#newaitees`、`#aiart`が含まれている
- X本文が280文字以内である
- `publish_at`をJSONへ追加していない

確認後、上記の`publish-media`コマンドを実行してください。実行結果を確認し、画像公開に失敗した場合は、失敗内容を報告して停止してください。Buffer投稿は実行しないでください。

---

## Scheduledタスク2：プロセス2

### タスク名

`SocialCaster Process 2 - Schedule Social Posts`

### 実行コマンド

作業ディレクトリ`C:\projects\SocialCaster`で、次を実行してください。

```powershell
Set-Location C:\projects\SocialCaster
C:\projects\SocialCaster\.venv\Scripts\python.exe -m social_caster.cli publish-social
```

### Codexへの指示文

あなたはSocialCasterのプロセス2担当です。

上記の`publish-social`コマンドだけを実行してください。SocialCaster本体やNewAITeesのpullは実行しないでください。プロセス1が成功して公開URLが確定した投稿だけが対象になります。

- NewAITeesへ画像を追加しない
- inboxやarchiveのファイルを移動・変更しない
- JSONを新規作成・変更しない
- Buffer APIキーやチャンネルIDを表示しない
- 1回の実行で最大3件をBufferへ予約登録する
- InstagramとXへ同じ公開画像URLを渡す
- InstagramとXの本文はJSONの別フィールドを使う
- Buffer予約に成功したら、投稿IDと状態をSQLiteへ保存する
- 片方が失敗しても、もう片方の成功を取り消さない

予約時刻はSocialCasterが日本時間で自動設定します。

```text
01:00
09:00
17:00
```

この3枠を使い、1日3件のペースでBufferへ予約します。Codexが独自に日時を変更しないでください。

### 実行後の確認

成功時は、次の内容だけを報告してください。

- 処理件数
- Instagramの成功・失敗件数
- Xの成功・失敗件数
- 予約日時
- エラーがある場合のエラー概要

APIキー、アクセストークン、秘密情報、本文全文は報告へ含めないでください。

## 失敗時のルール

- 失敗した画像や投稿は移動しない
- `ready`、`posted`、`failed`フォルダを作成しない
- 未処理の入力画像とJSONは`C:\projects\SocialCaster\input\inbox`に残す
- プロセス1で公開成功した画像とJSONは`C:\projects\SocialCaster\input\archive`に置かれる
- 状態確認はSQLiteとコマンド結果で行う
- 同じ失敗を無制限に繰り返さず、エラーを報告して停止する
