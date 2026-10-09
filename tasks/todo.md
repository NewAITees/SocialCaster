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
- [x] Gitフックへpre-commitをインストールする（2026-09-01 実施。`.git/hooks` は書き込み可能で「権限待ち」は既に解消していた。導入前に `ruff format` 未適用だった3ファイルを整形）

## MVP実装
- [x] SQLite投稿管理とSNS別ステータスを実装する
- [x] Buffer GraphQL経由のInstagram・X個別投稿を実装する
- [x] 期限到来投稿の1回処理と5分間隔常駐処理を実装する
- [x] CLIによるDB初期化・投稿登録・実行を実装する
- [x] SNS単位の失敗記録と再送を実装する
- [x] MVPテストと品質チェックを完了する

## 認証・本文ルール
- [x] Buffer APIキー設定用の`.env`を作成しGit除外を確認する
- [x] 実APIキーを設定してBuffer認証を検証する（2026-09-01 `auth-check` で確認。organization=My Organization、接続チャンネルは instagram: new_ai_tees と pinterest: newaitees。Xチャンネルは未接続）
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

## 2026-10-07 自動実行の停止解消と失敗通知
- [x] 自動起動の有無と処理の成否を切り分ける（タスクは毎日07:00に起動済み、LastTaskResult=1）
- [x] 停止原因を特定する（`random_20260220_151145_0039.png.json` の英語本文251文字でmanifest検証がexit=1、10-04〜10-07の4日間停止）
- [x] 該当JSONの英語本文を250文字以内へ短縮する
- [x] `verify_manifests.py` で全件パスを確認する
- [x] `.env` / `.env.example` に `DISCORD_WEBHOOK_URL` を追加する
- [x] `run.ps1` に失敗時のみ送信するDiscord通知を実装する
- [x] PowerShell構文チェックとPS5.1でのテスト送信を確認する
- [x] `run.ps1` を手動実行し、validation通過を確認する（iteration 1〜4が検証を通過。ただし投稿は0件で、より深い原因が露出した）

### 2026-10-07 判明した多重の詰まり
- [x] `NewAITees/node_modules` が空で `sharp` が無く画像変換が全件失敗していた → `sfw npm ci --omit=dev` で導入
- [x] NewAITees の push が bot の自動コミットと競合して弾かれていた → 失敗時に `pull --rebase --autostash` して再pushするよう修正
- [x] gitの `core.longpaths` 未設定で rebase/autostash が `Filename too long` で落ちる → `_run_git` に付与
- [x] Pages反映待ちが300秒では足りない（実測約9分）→ 既定を900秒へ
- [x] 失敗した入力が辞書順先頭を占めて新規を止める → 予算をリトライ枠1件と新規枠へ分割
- [x] Discord通知を「静かな無成果」（exit 0でもMEDIA_FAILED残存・STOCK未達）も検知するよう拡張
- [x] 未追跡の使い捨てファイル172件を削除し、ruff/mypyの除外設定を追加（pre-commitが全体で通るようになった）
- [x] pytest 59件・ruff・ruff format・mypy をプロジェクト全体で通した
- [x] 変更を6コミットに分けてコミットした
- [ ] FAILED 9件を回復させる（修正後の `publish-media` で1実行1件のため、回復方法を決める）
- [ ] 回復後に `run.ps1` を通しで実走させ、publish-social まで到達することを確認する

## 2026-10-07 Pinterest投稿の追加（依頼済み・未着手）
- [x] Buffer の Pinterest チャンネルID・ボードID・GraphQL metadata契約をユーザー確定値として確認する
- [x] Pinterest の本文・タイトル・リンク制約をユーザー確定値として確認する
- [x] manifest に Pinterest 専用の本文とタイトルを任意項目として持たせる方針を確認する
- [x] `provider.py` / `batch.py` / `config.py` へ Pinterest を配線する
- [x] `database.py` にPinterest状態・本文・タイトル・カテゴリを追加し、サービス別在庫を実装する
- [x] `verify_manifests.py` の検証を Pinterest 仕様へ追随させる
- [x] `automation/status.py` と `run.ps1` をサービス別在庫へ追随させる
- [x] `prompt.md` と環境変数サンプルへPinterest設定を追加する
- [x] TDDで指定テストを追加し、現存するmanifest 494件を検証する
- [x] pytest・ruff check・ruff format --check・mypyを通す
- [x] 差分を自己レビューし、BOM・禁止事項・ユーザー既存変更の保全を確認する

## 2026-10-07 Pinterest 残作業
- [ ] `.env` の `ENABLE_PINTEREST=true` にするか判断する（ボード5件とIDは設定済み）
- [ ] 有効化後、実 API への1件目の投稿が Pinterest の意図したボードへ入るか確認する
- [ ] 既存494件の manifest には Pinterest 欄がないため、当面 Pinterest へは出ない。遡って付与するか、新規分だけで運用するか決める
- [ ] `joke` / `botanical` は件数が増えたら専用ボードへ分離する（`.env` に1行足すだけ）

## 2026-10-07 判明した構造的な課題（未着手）
- [ ] `publish-social` の成功判定が「Buffer が予約を受理したか」までしか見ておらず、Buffer から先の実配信失敗を検知できない。Buffer 側の配信ステータスを取得して突き合わせる仕組みを検討する
- [ ] `media_status=FAILED` 8件は日次実行のリトライ枠で1日1件ずつ解消される見込み（放置可）

## 2026-10-08 リポジトリの整理
- [x] `input/manifests` を新設し、JSON 308件を inbox から分離（inbox は画像444枚だけに）
- [x] DB の `source_key` 194件を `inbox/` から `manifests/` へ書き換え（二重投稿防止）
- [x] `batch.py` / `verify_manifests.py` / `prompt.md` / `.gitignore` を新構成へ追随
- [x] `run.ps1` に使い捨てファイルの自動削除とログ30日世代管理を組み込み、実地で動作確認
- [x] `prompt.md` に「inbox へ書き込まない」「一時ファイルを作らない」を明記
- [x] 復旧済み `memory.md` 全文（116KB）をコミットし、次の事故に備えた
- [x] pytest 79件・ruff・ruff format・mypy を通した
- [ ] `memory_pending_*.md` 40件の扱いを決める（memory.md へマージするか、復旧用の証跡として残すか）
- [ ] `input/archive` 1.1G は NewAITees と GitHub に同じ画像があるため削除可能。手元バックアップを残すかは要判断
- [ ] `NewAITees/_site` 576M がビルド出力のままコミットされている件の調査（今回は中断）

## 2026-10-08 memory.md の肥大化対応
- [x] memory.md の用途を確認（prompt.md はパス提示と追記指示のみで、生成の判断には未使用）
- [x] 書き手ごとのコストを分離（claude=Editで全文読込 / run.ps1=Add-Contentで読込なし）
- [x] prompt.md から memory への言及を削除し、claude の追記を止めた
- [x] run.ps1 の追記は残した（コストゼロ、30日より古い stop reason の唯一の保存先）
- [x] 上書き事故の教訓を lessons.md へ転記した
- [x] 弾かれた Instagram 4件が、Buffer の枠が空いたとき自動再送されるか確認する
  - 自動再送されない。`publish_social_once` は IG≠SUCCESS を全件リトライする設計だが、
    step3 は `refill > 0` の後ろにあり、Pinterest充足で refill=0 になると到達しない
  - 2026-10-09 時点で Buffer の IG 枠は 6/10（空き4枠）あり、枠不足ではない
- [ ] ログ保持期間30日を延ばすか判断する（本日38件を自動削除）

## 2026-10-08 ディスク整理
- [x] `NewAITees/_site` 575M を調査し、削除した
  - `_config.yml` も `Gemfile` も無く Jekyll は動いていない。`_site` は過去に一度作られたまま
    取り残された古いスナップショットだった
  - 91ファイル575MB。内訳はルート側と同一内容66件、同名だが古い版9件、既に消えたファイルの残骸16件
  - `index.html` からの参照は0件で、サイトの表示には使われていない。`deploy.yml` が `folder: .` で
    リポジトリ全体を gh-pages へ送るため、参照されないまま公開され毎回転送されていた
  - 削除して `.gitignore` へ `_site/` を追加。push 済み（a8bf86d..5997c1b）
  - 調査中に「作業ツリーから消してもディスクは減らない」と誤った説明をした。`.git` に履歴が
    残ることと作業ツリーの容量が空くことは別で、実際には575MB空く
- [x] `input/archive` の原寸画像201件（1.16GB）を削除した
  - 削除前に SHA-256 で全201件が `NewAITees/assets/gallery/` に同一内容で存在することを確認（不一致0件）
  - manifest 201件（914K）は軽量なため保持
  - `posts.archive_image_path` の201行は実ファイルを失ったが、投稿は NewAITees の公開URLを使うため影響なし
- [x] 回収したディスクは合計約1.7GB（archive 1.16GB ＋ _site 575MB）
- [ ] `archive_image_path` の扱いを決める（記録として不正確になった。NULL にするか、列ごと廃止するか、現状維持か）

## 2026-10-09 Instagram在庫が回復しない問題の修正
調査結果: `STOCK_INSTAGRAM=7 TARGET=9` でも「target stock reached」で停止していた原因は、
`status.py` の `REFILL` が有効サービスの最小値を取るため、Pinterest(9/9充足)が律速して
refill=0 に固着していたこと。refill=0 で `run.ps1` が iteration 1 で break するため、
step2/step3 のリトライ（MEDIA_FAILED 5件・IG_FAILED 4件）に永久に到達しない。

Buffer APIの実地確認(2026-10-09): 予約の中身は `posts(filter:{channelIds,status:[scheduled]})`
で取得可能。上限は `account.organizations.limits.scheduledPosts` が 10 を返し、
`BUFFER_RESERVATION_CAP` のハードコードは不要。スキーマ説明は組織単位だが実際はチャンネル単位。

- [ ] `feat:` BufferClientに `get_scheduled_posts` / `get_scheduled_post_limit` を追加する
- [ ] `feat:` status.py の在庫・空き枠をBuffer実数にし、サービス別の NEED/ROOM を出力する（min撤廃）
- [ ] `fix:` publish_social_once のリトライをサービス別の空き枠で打ち切る
- [ ] `feat:` 不足しているサービスだけを補充する（IG専用manifest。Pinterest専用は作らない）
- [ ] `fix:` 在庫充足時でも失敗リトライを実行するよう停止条件を分離する
- [ ] `chore:` `BUFFER_RESERVATION_CAP` を .env / .env.example から削除する
- [ ] 滞留分を回復させる（id 189-193 MEDIA_FAILED、id 200-203 IG_FAILED）

### 範囲外（指示があれば着手）
- [ ] `media_error` の日本語が文字化けして保存されている（subprocessのstderrデコード）
- [ ] `id 203` の `last_error` が空で、Instagram失敗の理由を取り逃がしている
- [ ] Xチャンネルは `Actor can not access the specified channels` で参照不可（ENABLE_TWITTER=false のため実害なし）
