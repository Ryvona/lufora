# X 自動投稿

`queue.json` に書いた投稿を、決めた時刻に @Ryvona_stadio から自動で投稿します。

- 1時間ごとに確認し、時刻を過ぎた投稿を **1回に1本だけ** 送ります。前の投稿から18時間たっていなければ待ちます（連投防止）。
- 送った投稿には `posted_at` と `post_id` が書き込まれ、二度と送られません。
- 投稿を足すときは、`at`（日本時間なら `+09:00`）と `text` を書いた項目を追加します。投票にしたいときは `"poll": ["選択肢1", "選択肢2"]` を足します。
- 止めたいときは GitHub の Actions → X auto post → 「…」→ Disable workflow。

## 最初の設定
1. developer.x.com でアプリを作り、権限を「Read and write」にする。
2. API Key / API Secret / Access Token / Access Token Secret を発行する（権限変更のあとに Access Token を発行し直す）。
3. GitHub の Settings → Secrets and variables → Actions に
   `X_API_KEY` `X_API_SECRET` `X_ACCESS_TOKEN` `X_ACCESS_TOKEN_SECRET` として登録する。
4. このファイルを main に取り込む（定期実行は main でしか動きません）。
5. Actions → X auto post → Run workflow（dry_run=1）で、何が送られるか確認できます。
