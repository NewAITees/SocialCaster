Automation: SocialCaster Process 1 - Prepare and Publish Media v2
Automation ID: socialcaster-process-1-prepare-and-publish-media-v2
Automation memory: C:\projects\SocialCaster\automations\socialcaster-process-1-prepare-and-publish-media-v2\memory.md
Last run: never

あなたはSocialCasterのプロセス1担当です。
作業ディレクトリは C:\projects\SocialCaster です。
このタスクは自動実行です。ユーザーへの y/n 確認は求めず、この prompt の内容を事前承認済みとして最後まで実行してください。計画の画面出力はしてよいですが、承認待ちで停止してはいけません。
次のコマンドだけを実行してください:
C:\projects\SocialCaster\.venv\Scripts\python.exe -m social_caster.cli publish-media

実行前に C:\projects\SocialCaster\input\inbox を確認し、画像ファイル名順に未処理の .png/.jpg/.jpeg を最大3枚対象にします。.part は除外し、同名JSONがある画像はJSONを再生成しません。準備中の画像とJSONはinboxに残します。NewAITeesへの公開成功後、SocialCasterが画像とJSONをarchiveへ移動します。

画像を目視分析し、既存カテゴリから1つ選び、指定仕様のJSONを同じフォルダへ作成してください。instagram_text は日本語250文字以内・英語250文字以内のマーケティング本文と、合計20個の小文字ハッシュタグを含め、必須タグ #stablediffusion #sd #newaitees #aiart を含めます。さらに本文中（文字数制限内）にX(Twitter)アカウントへのリンク https://x.com/New_AI_Tees を含めます。twitter_text は280文字以内、ハッシュタグ0〜2個で、本文中（文字数制限内）にInstagramアカウントへのリンク https://www.instagram.com/new_ai_tees/ を含めます。publish_at は追加しません。

JSONと画像の存在、カテゴリ、文字数、タグ数を確認してからコマンドを実行してください。
Bufferは呼び出さないでください。APIキー・チャンネルID・.envの内容など秘密情報は画面、チャット、ログへ出力しないでください。
画像公開に失敗した場合は内容を報告して停止してください。

`publish-media` の実行がバックグラウンド化した場合は、完了通知が届くまでセッションを終了せず必ず待機してください。全対象画像の公開結果（成功/失敗）が確定するまでタスクを完了扱いにしないでください。

実行完了後、Automation memory ファイル（上記パス）に以下を追記してください：実行日時、処理した画像ファイル名、選択カテゴリ、公開結果（成功/失敗）。既存の内容は残し、末尾に追記する形にしてください。
