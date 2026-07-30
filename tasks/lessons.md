# Lessons - 過去の失敗と学び

## INDEX（追記・修正のたびに必ず更新すること）
| カテゴリ     | 説明                          | 開始行 | 件数 |
|--------------|-------------------------------|--------|------|
| meta         | AIとの協働ルール              | -      | 2    |
| boundary     | データ型・変換・境界契約      | -      | 2    |
| architecture | 設計・責務・config            | -      | 5    |
| quality      | テスト・CI/CD・品質保証       | -      | 3    |
| ui           | フロントエンド・デザイン・VRM | -      | 0    |

---

## meta — AIとの協働ルール
### [タイトル（キーワードを含む1行）]
- **症状**: 
- **原因**: 
- **対策**: 

### [自動実行: automationでは承認待ちに入らない]
- **症状**: 自動実行用の prompt に通常対話と同じ `y/n` 承認フローを要求すると、scheduled run が承認待ちで停止して自動化の意味を失う。
- **原因**: 対話セッション用の運用原則を、そのまま automation prompt にも適用していた。
- **対策**: automation prompt には「このタスクは自動実行であり、prompt 内容は事前承認済み。`y/n` を求めず最後まで進める」と明記する。

### [無人claude -p: グローバルCLAUDE.mdとパイプ文字化けに注意]
- **症状**: スケジュールから `claude -p` を呼ぶと、(1)ユーザーグローバル`~/.claude/CLAUDE.md`の5原則を毎回出力し第1原則のy/n待ちでファイル生成を拒否、(2)PowerShell 5.1のパイプでUTF-8プロンプトが`?`に化けた。
- **原因**: (1)ヘッドレスでもユーザーmemory(CLAUDE.md)が自動ロードされ、対話用の運用原則が自動化を止める。(2)PS5.1は native コマンドへのパイプ既定エンコーディングがASCII。`--bare`はCLAUDE.md非ロードだがkeychain読取を切りANTHROPIC_API_KEY必須（別課金）になるため不可。
- **対策**: サブスク認証を維持したまま `claude -p --setting-sources project` でユーザーグローバルCLAUDE.mdを外す（実測で原則検出0件）。パイプは`$OutputEncoding`と`[Console]::OutputEncoding`をUTF-8に設定し、プロンプトは`Get-Content -Raw -Encoding UTF8`で渡す。.ps1自体もUTF-8 BOM付きで保存する。

## boundary — データ型・変換・境界契約
### [サブカテゴリ: タイトル]

### [SNS本文: プラットフォーム別に検証する]
- **症状**: Instagram向けの長文本文をそのままXへ送ると、投稿制約や運用目的に合わない。
- **原因**: Instagramは説明・改行・ハッシュタグ中心、Xは短文中心で、通常投稿の文字数制約も異なる。
- **対策**: 本文をSNS別カラムで保持し、登録時にInstagramは2,200文字以内、Xは280文字以内で検証する。

### [投稿JSON: inboxマニフェストはimageキー必須]
- **症状**: `publish-media` 実行時にJSONを作成しても、画像公開へ進まず入力が `inbox` に残留した。
- **原因**: `src/social_caster/batch.py` は投稿JSONの画像指定を `image` キーで読み込むが、`image_path` で作成してしまった。
- **対策**: `input/archive` の既存JSON形式に合わせ、`publish-media` 用マニフェストは画像ファイル名を持つ `image` キーで作成前確認する。

## architecture — 設計・責務・config
### [サブカテゴリ: タイトル]

### [Buffer: 公開HTTPS画像URLが必要]
- **症状**: ローカルの画像パスだけではBufferへ画像付き投稿できない。
- **原因**: Buffer APIは投稿時に外部から取得できる公開HTTPSの直接画像URLを要求する。
- **対策**: ローカル管理用の`image_path`と、Buffer投稿用の`image_url`を分離して設計する。

### [運用: AI入力と日次投稿を分離]
- **症状**: GUIのAIアプリを投稿処理の常駐依存にすると、ログイン状態や確認ダイアログで安定性が下がる。
- **原因**: デスクトップアプリは無人バッチの実行基盤ではなく、Bufferはローカル画像を受け取れない。
- **対策**: AIはSMB共有のinboxへJSONを作成し、日次バッチがNewAITeesへの画像公開とBuffer投稿を二段階で実行する。

### [状態管理: 入力ファイルを移動せずSQLiteで管理]
- **症状**: ready／posted／failedフォルダを分けると、公開URL生成とSNS投稿の処理境界が曖昧になる。
- **原因**: Buffer投稿には先にGitHub Pages上の公開URLが必要で、ファイル移動は公開状態を表さない。
- **対策**: 入力画像とJSONはinboxに残し、SQLiteのmedia_statusとSNS別statusで公開・投稿・再送状態を管理する。

### [パス管理: 元画像パスと保管先パスを分離する]
- **症状**: `image_path` を公開成功後に archive 側へ上書きすると、元の inbox パスと現在の保管先の意味が混ざる。
- **原因**: 1つの列に「受信元」と「現在位置」の2役を持たせていた。
- **対策**: `image_path` は元ファイルとして固定し、公開後の保管先は `archive_image_path` の別列で保持する。

### [Git: 外部サイトリポジトリを親へ取り込まない]
- **症状**: SocialCasterの親リポジトリ内に、独立したNewAITees Gitリポジトリがそのまま存在していた。
- **原因**: 画像公開先の作業コピーと投稿ツールのソース管理を同じ階層で扱っていた。
- **対策**: NewAITeesは独立リポジトリとして保持し、親の`.gitignore`で除外する。パスは`NEWAITEES_PATH`で参照する。

## quality — テスト・CI/CD・品質保証
### [サブカテゴリ: タイトル]

### [Windows: 一時ディレクトリ権限に依存しないテスト]
- **症状**: pytestの`tmp_path`がユーザー一時ディレクトリの権限で失敗した。
- **原因**: 実行環境の一時ディレクトリを読み取れない制約がある。
- **対策**: SQLiteテストはインメモリDBを使い、外部一時ディレクトリへの依存を避ける。

### [入力: 公開成功後にarchiveへ移動する]
- **症状**: NewAITeesへ公開した元画像・JSONをinboxに残すと、未処理入力と処理済み入力を誤認しやすい。
- **原因**: プロセス1の公開処理と、プロセス2のBuffer投稿処理の責務を混同していた。
- **対策**: プロセス1は公開成功後にarchiveへ移動し、プロセス2はSQLiteの公開URLだけを使ってファイルを操作しない。

### [運用: プロセス2でSocialCasterをpullしない]
- **症状**: Buffer投稿だけを担当するプロセス2でSocialCaster本体の`git pull --ff-only`を実行すると、未コミット変更や対象リポジトリの違いで処理が失敗しうる。
- **原因**: SocialCaster本体の更新とNewAITeesの公開・Buffer投稿の責務を混同していた。
- **対策**: プロセス2は`publish-social`だけを実行し、必要なNewAITees同期はプロセス1の開始前に別途行う。

### [公開結果: publish-mediaの成功判定はexit codeだけで決めない]
- **症状**: `publish-media` が終了コード `0` で終わっても、対象画像とJSONが `archive` へ移動されず公開されていないことがある。
- **原因**: `DailyBatch._publish_media_manifest()` が例外を内部で捕捉して `media_status=FAILED` をDBへ記録し、CLI全体は成功終了する実装になっている。
- **対策**: 自動実行では終了コードに加えて `posts.db` の `media_status` と `media_error`、および `archive` への移動有無まで確認して成功判定する。

## ui — フロントエンド・デザイン・VRM
### [サブカテゴリ: タイトル]
