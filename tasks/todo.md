## 運用ルール
1. タスクを追加するときはチェックボックス形式で書く
2. 完了したら [x] にする
3. セクションが全て完了したら、セクションごと削除してよい

## 今回の作業
- [x] 「SNS自動投稿ツール 要件定義書.md」を読み、要点を整理する

## 環境構築
- [x] Buffer公式API仕様を調査する
- [x] Python 3.12とuv環境を構築する
- [x] exact version固定の開発依存関係を導入する
- [x] Buffer GraphQLクライアントと設定テストを追加する
- [x] pytest・ruff・mypyを実行する
- [ ] Gitフックへpre-commitをインストールする（Git hooks書き込み権限待ち）

## MVP実装
- [x] SQLite投稿管理とSNS別ステータスを実装する
- [x] Buffer GraphQL経由のInstagram・X個別投稿を実装する
- [x] 期限到来投稿の1回処理と5分間隔常駐処理を実装する
- [x] CLIによるDB初期化・投稿登録・実行を実装する
- [x] SNS単位の失敗記録と再送を実装する
- [x] MVPテストと品質チェックを完了する

## 認証・本文ルール
- [x] Buffer APIキー設定用の`.env`を作成しGit除外を確認する
- [ ] 実APIキーを設定してBuffer認証を検証する（ユーザー入力待ち）
- [x] Instagram・Xの本文ルールと投稿前検証を実装する

## フォルダ入力・日次バッチ
- [x] input/inboxを入力フォルダとして定義する
- [x] AIが作成する投稿JSONの形式を定義する
- [x] 画像公開とBuffer投稿を順番に処理する日次バッチを実装する
- [x] 投稿済み入力の重複処理を防止するsource_keyを追加する
- [x] Windowsタスクスケジューラ登録スクリプトを作る
- [x] 実機でタスクスケジューラへ登録する（`\SocialCaster-Process1-PublishMedia` として登録済み）

## NewAITees連携・コミット
- [x] NewAITeesを独立リポジトリとして親リポジトリから除外する
- [x] GitHub Pages反映待ちをBuffer投稿前に実行する
- [x] lint・テスト・型チェックを完了する
- [x] 親リポジトリの初回コミットを作成する

## 外部入力経路
- [x] input/inboxだけをSMB共有する設定スクリプトを作る
- [x] 別PCからの接続手順とコピー中ファイル対策を記載する

## 二段階処理設計
- [x] Bufferが公開HTTPS画像URLを必要とする理由を要件定義へ反映する
- [x] NewAITees画像公開後にBuffer投稿する二段階フローを文書化する
- [x] 画像公開処理とBuffer投稿処理をコード上でも分離する
- [x] ready／posted／failedフォルダ依存を廃止し、SQLite状態管理へ移行する

## 今回の修正
- [x] プロセス2は `publish-social` だけを実行する
- [x] プロセス1のNewAITees公開後に画像・JSONをarchiveへ移動する責務を確認する
- [x] プロセス2がinbox・archiveを操作しないことを明記する
- [x] 関連テストとScheduled指示を更新する
- [x] pytest・lint・型チェックを実行する
- [x] 2026-07-25 17:00、翌日01:00・09:00のJST予約枠をテストする

## 今回の自動実行
- [x] inbox先頭3件の画像を確認し、必要なJSONを作成する
- [x] JSONのカテゴリ・文字数・ハッシュタグ数を検証する
- [x] `publish-media` を実行し、結果を確認する

## 2026-07-26 プロセス2自動実行
- [x] 自動化メモリと既存タスクを確認する
- [x] `publish-social` を1回だけ実行する
- [x] 実行結果を記録し、必要な学びを更新する

## 2026-07-27 プロセス1自動実行
- [x] 自動化メモリと既存タスクを確認する
- [x] inbox先頭3件の画像を確認し、カテゴリを選定する
- [x] 必要なJSONを作成する
- [x] JSONの文字数・タグ数・必須項目を検証する
- [x] `publish-media` を実行し、結果を記録する

## 2026-07-27 パス管理改善
- [x] `image_path` を元ファイルとして固定する方針を決める
- [x] `archive_image_path` を追加し、公開後の保管先を分離する
- [x] 関連テストを更新して通過させる

## 2026-07-27 プロセス1再実行
- [x] `newaitees.py` の Git 呼び出し不具合を修正する
- [x] 関連テストを更新して通過させる
- [x] `publish-media` を再実行する
- [x] 失敗原因を確認して記録する

## 2026-07-27 プロセス1手動完了
- [x] サンドボックス外で `publish-media` を手動実行する
- [x] 対象3件の archive 移動とDB成功状態を確認する

## 2026-07-27 automation prompt修正
- [x] 自動実行で `y/n` 確認を要求しない方針を定義する
- [x] process-1 / process-1-v2 の automation prompt を更新する
- [x] process-2 の automation prompt に事前承認済み・追加確認禁止を明記する

## 2026-07-27 プロセス1 v2自動実行
- [x] 自動化メモリと inbox 先頭3件を確認する
- [x] 対象3件の画像を目視し、JSONを作成する
- [x] JSONのカテゴリ・文字数・ハッシュタグ数を検証する
- [x] `publish-media` を実行する
- [x] DBの `media_status` と `media_error` を確認し、GitHub接続失敗を記録する

## 2026-07-28 プロセス1 v2再実行
- [x] 前回失敗の原因を切り分ける
- [x] サンドボックス外で `publish-media` を再実行する
- [x] 公開済みコミットとPages反映待ちを確認する
- [x] 3件すべての `media_status=SUCCESS` と archive 移動を確認する

## 2026-07-28 承認なし自動スケジュール（プロセス1→2チェーン）
- [x] `automation/status.py` … DBカウント出力（gate判定・レポート用、秘密情報なし）
- [x] `automation/process1-analyze-prompt.txt` … ヘッドレスclaude用の分析&JSON生成専用プロンプト（2026-09-01 削除。後述の run.ps1 へ統合済み）
- [x] `automation/run-socialcaster.ps1` … ラッパー（claude分析→publish-media→成功ゲート→publish-social→ログ）（2026-09-01 削除。実際に稼働しているのは `automations/socialcaster-process-1-prepare-and-publish-media-v2/run.ps1`）
- [x] エンコーディング(UTF-8 BOM/$OutputEncoding)とグローバルCLAUDE.md非ロード(--setting-sources project)を解決
- [x] ドライランで3枚分析→JSON生成→仕様検証（カテゴリ/文字数/タグ）まで確認
- [x] `schtasks` 登録（`\SocialCaster-Process1-PublishMedia`、毎日07:00）
- [x] 本番1回を実機で走らせ、publish-media→ゲート→publish-social まで確認（2026-08-18以降、連日 exit 0）

## 2026-08-30 進捗確認で判明した残課題
- [x] `ENABLE_TWITTER` を `DailyBatch` へ配線し、テストを追加する
- [x] 2026-08-28 の分析記録を automation の `memory.md` へマージする
- [ ] 2026-08-29 の自動実行が欠落した原因を確認する（ログ・タスク履歴ともになし。PC停止の可能性）
- [x] `prompt.md` のハッシュタグ数・本文文字数の確定版仕様を記録する（未コミットだった現行 prompt.md をコミットし git 管理下に置いた。確定版は IG 日本語250字・英語250字・小文字タグ20個・本文にXリンク、twitter_text は280字・タグ0〜2個・リンクなし）
- [ ] `tests/test_batch.py` の `_seed_media_ready_post` の型注釈（`connection: object`）を修正し `mypy` を通す
- [ ] 未追跡の `scripts/_verify_*.py` 18件を整理する（ruff エラー40件の全てがこれら）
- [x] `feature/anti-freeze-safeguards` を main へマージし push する（2026-08-30、18コミットを origin/main へ反映）

## 2026-08-30 投稿在庫トップアップ機能（承認済み計画）
- [ ] 現在地・環境・既存タスク・対象実装を確認する
- [ ] 投稿在庫数と補充数（目標・上限クランプ）を実装する
- [ ] status.py に STOCK 出力を追加する
- [ ] publish-media / publish-social に件数引数を追加する
- [ ] Settings と .env.example に目標在庫9・予約上限10を追加する
- [ ] run.ps1 を在庫再計算付き反復処理へ変更する
- [ ] prompt.md を生成件数パラメーター対応にする
- [ ] 在庫・補充・上限・CLI件数のテストを追加する
- [ ] 既存 test_batch.py の型注釈を修正する
- [ ] pytest・ruff・mypy をすべて通す
- [ ] 自己レビューし lessons.md と本進捗を更新する

### 2026-08-30 完了状況（追記）
- [x] 現在地・環境・既存タスク・対象実装を確認した
- [x] 投稿在庫数と補充数（目標・上限クランプ）を実装した
- [x] status.py に STOCK 出力を追加した
- [x] publish-media / publish-social に省略時3の `--count` を追加した
- [x] Settings と .env.example に目標在庫9・予約上限10を追加した
- [x] run.ps1 を在庫再計算・最大10反復・入力枯渇停止へ変更した
- [x] prompt.md を `{{COUNT}}` パラメーター対応にした
- [x] 在庫・補充・上限・CLI件数のテストを追加した
- [x] test_batch.py の接続型注釈を sqlite3.Connection に修正した
- [x] pytest 37件、ruff、mypy の最終検証を完了した
- [x] 自己レビューし lessons.md を更新した

## 2026-08-30 投稿在庫トップアップ レビュー指摘修正
- [ ] stock_count のタイムゾーン比較を実時刻比較へ修正する
- [ ] run.ps1 の失敗時も memory.md へ結果を記録する
- [ ] JSTオフセット付き過去時刻の回帰テストを追加する
- [ ] 壊れたpytest一時ディレクトリ3件を削除する
- [ ] pytest・ruff・mypy・PowerShell構文を検証する

### 2026-08-30 レビュー指摘修正 完了状況（追記）
- [x] stock_count を SQLite julianday によるオフセット解釈付き実時刻比較へ修正した
- [x] run.ps1 を try/catch/finally 化し、失敗時も停止理由とexit結果を memory.md へ追記するよう修正した
- [x] JSTオフセット付き過去時刻を在庫に数えない回帰テストを追加した
- [x] 壊れたpytest一時ディレクトリ3件をACL復旧後に削除した
- [x] pytest・ruff・mypy・PowerShell構文とfinally追記経路を検証した

## 2026-08-30 manifest検証スクリプト統合
- [ ] scripts/verify_manifests.py を現行prompt仕様で実装する
- [ ] run.ps1 のJSON生成後・publish-media前へ検証を組み込む
- [ ] scripts/_verify_* の使い捨て18件を削除する
- [ ] 正常系と各違反ケースの回帰テストを追加する
- [ ] pytest・プロジェクト全体ruff・mypyを通す

### 2026-08-30 manifest検証スクリプト統合 完了状況（追記）
- [x] scripts/verify_manifests.py を現行prompt仕様で実装した
- [x] run.ps1 のJSON生成後・publish-media前へ検証ゲートを組み込んだ
- [x] scripts/_verify_* の使い捨て18件を削除した
- [x] 正常系と各指定違反ケースの回帰テスト14件を追加した
- [x] pytest・プロジェクト全体ruff・mypy・PowerShell構文を検証した
