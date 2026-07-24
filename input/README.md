# 入力フォルダ運用

## 別PCからSMBで画像を置く

SocialCasterを実行するPCで、管理者として次を実行します。

```powershell
PowerShell -ExecutionPolicy Bypass -File scripts/setup_input_smb_share.ps1
```

表示された共有先を、別PCのエクスプローラーで開きます。`inbox`へ画像を置き、AIは画像と同じ場所にJSONを作成します。

ホストPC名だけを確認する場合は、SocialCaster PCで次を実行します。

```powershell
hostname
```

```text
\\DESKTOP-OBMGMM7\SocialCasterInput
```

このPCでは上記のパスを使用します。別のPC名になった場合は、`hostname`の出力に置き換えてください。SMB共有にはSocialCaster PCのWindowsユーザー認証が必要です。ネットワークプロファイルは「プライベート」にしてください。

画像のコピー中に日次処理が走らないよう、一時拡張子でコピーしてから最後に画像名へ変更します。

```text
monster.png.part  ← コピー中
monster.png       ← コピー完了後にリネーム
```

画像は共有先の`inbox`へ置き、AIが同じフォルダに投稿JSONを作成します。日次処理がNewAITeesへの画像公開とBuffer投稿を順番に行います。

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
5. 元画像と同じファイル名のJSONをinput/inbox/へ作成する
6. 画像はinput/inbox/に残す

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

日次バッチは`input/inbox/`の画像とJSONを処理します。まずNewAITeesへカテゴリ別に画像を公開し、公開URLを確定します。その後、公開URLを使ってBufferからInstagramとXへ投稿します。画像公開の状態とSNS別の再送状態はSQLiteで管理します。
