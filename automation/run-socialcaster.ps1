<#
    SocialCaster 承認なし自動実行ラッパー（プロセス1 -> プロセス2 チェーン）

    フロー:
      (1) DBカウントを baseline として記録
      (2) ヘッドレス claude で inbox 画像を分析し、投稿JSONを生成（Read/Write/Glob のみ）
      (3) publish-media で NewAITees へ公開（.env は Python 側が自動読込。秘密情報は本スクリプトに出さない）
      (4) 成功ゲート: media 成功数が baseline より増えたら「プロセス1成功」
      (5) 成功時のみ publish-social（IG/X 各最大3件）を実行
      (6) 件数の差分だけを logs\run-YYYYMMDD.log へ記録（秘密情報・本文全文は出さない）

    使い方:
      通常実行 : powershell -ExecutionPolicy Bypass -File automation\run-socialcaster.ps1
      ドライラン: 同上に -DryRun を付与（JSON生成のみ。公開・投稿はしない）

    注意:
      - 無人実行のため claude はツール確認を出せない。--dangerously-skip-permissions で起動し、
        使用ツールを Read/Write/Glob に限定する。
      - 実行のたびに claude セッションが1回走り、トークン課金が発生する。
#>

param(
    [switch]$DryRun
)

$ErrorActionPreference = 'Stop'

$Root        = 'C:\projects\SocialCaster'
$Python      = Join-Path $Root '.venv\Scripts\python.exe'
$StatusPy    = Join-Path $Root 'automation\status.py'
$PromptFile  = Join-Path $Root 'automation\process1-analyze-prompt.txt'
$LogDir      = Join-Path $Root 'logs'

Set-Location $Root

# Windows PowerShell 5.1 は native コマンドへのパイプ既定が ASCII のため、
# 日本語プロンプトが化ける。UTF-8 に固定して claude へ正しく渡す。
$OutputEncoding = New-Object System.Text.UTF8Encoding $false
[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding $false

New-Item -ItemType Directory -Force $LogDir | Out-Null
$Log = Join-Path $LogDir ("run-{0}.log" -f (Get-Date -Format 'yyyyMMdd'))

function Write-Log {
    param([string]$Message)
    $line = "[{0}] {1}" -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $Message
    Add-Content -Path $Log -Value $line
    Write-Host $line
}

# "KEY=VALUE KEY=VALUE ..." 形式の1行を hashtable へ変換する
function Get-Counts {
    $raw = & $Python $StatusPy 'counts'
    if ($LASTEXITCODE -ne 0) { throw "status.py の実行に失敗しました" }
    $counts = @{}
    foreach ($token in ($raw -split '\s+')) {
        if ($token -match '^(\w+)=(\d+)$') { $counts[$matches[1]] = [int]$matches[2] }
    }
    return $counts
}

try {
    Write-Log "=== run start (DryRun=$DryRun) ==="

    if (-not (Test-Path $Python))   { throw "Python が見つかりません: $Python" }
    if (-not (Test-Path $PromptFile)) { throw "プロンプトが見つかりません: $PromptFile" }

    $before = Get-Counts
    Write-Log ("baseline media_success={0} media_failed={1}" -f $before.MEDIA_SUCCESS, $before.MEDIA_FAILED)

    # (2) 画像分析 + JSON生成（ヘッドレス claude、ツールは Read/Write/Glob に限定）
    Write-Log "process1: claude による画像分析とJSON生成を開始"
    # --setting-sources project でグローバル(ユーザー)CLAUDE.md を読み込ませない。
    # これにより「5原則の毎回出力」と「第1原則によるy/n確認待ち停止」を回避し、
    # 巨大なシステムプロンプトのロードも避ける（サブスク認証は維持される）。
    $prompt = Get-Content -Raw -Encoding UTF8 $PromptFile
    $claudeOut = $prompt | & claude -p --setting-sources project --allowedTools Read Write Glob --dangerously-skip-permissions 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Log ("process1: claude 実行が非0終了 (exit={0})" -f $LASTEXITCODE)
        Write-Log ("claude output: {0}" -f ($claudeOut -join ' '))
        throw "画像分析/JSON生成に失敗しました。処理を停止します。"
    }
    Write-Log ("process1 claude result: {0}" -f ($claudeOut -join ' '))

    if ($DryRun) {
        Write-Log "DryRun のため publish-media / publish-social は実行しません。"
        Write-Log "=== run end (dry-run) ==="
        return
    }

    # (3) 画像公開
    Write-Log "process1: publish-media を実行"
    & $Python -m social_caster.cli publish-media
    if ($LASTEXITCODE -ne 0) {
        throw "publish-media が異常終了しました (exit=$LASTEXITCODE)。処理を停止します。"
    }

    # (4) 成功ゲート
    $mid = Get-Counts
    $mediaSuccessDelta = $mid.MEDIA_SUCCESS - $before.MEDIA_SUCCESS
    $mediaFailedDelta  = $mid.MEDIA_FAILED  - $before.MEDIA_FAILED
    Write-Log ("process1 結果: media成功 +{0} / media失敗 +{1}" -f $mediaSuccessDelta, $mediaFailedDelta)

    if ($mediaSuccessDelta -le 0) {
        Write-Log "プロセス1で新規公開なし。プロセス2はスキップします。"
        Write-Log "=== run end (no new media) ==="
        return
    }

    # (5) プロセス1成功時のみ SNS 予約
    Write-Log "process2: publish-social を実行"
    & $Python -m social_caster.cli publish-social
    if ($LASTEXITCODE -ne 0) {
        Write-Log "process2: publish-social が非0終了。以降の投稿は中止します。"
        throw "publish-social が異常終了しました (exit=$LASTEXITCODE)。"
    }

    # (6) レポート
    $after = Get-Counts
    Write-Log ("process2 結果: IG成功 +{0} / IG失敗 +{1} / X成功 +{2} / X失敗 +{3}" -f `
        ($after.IG_SUCCESS - $mid.IG_SUCCESS), `
        ($after.IG_FAILED  - $mid.IG_FAILED), `
        ($after.X_SUCCESS  - $mid.X_SUCCESS), `
        ($after.X_FAILED   - $mid.X_FAILED))
    Write-Log ("予約枠(JST): 01:00 / 09:00 / 17:00 は SocialCaster が自動設定")
    Write-Log "=== run end (ok) ==="
}
catch {
    Write-Log ("ERROR: {0}" -f $_.Exception.Message)
    Write-Log "=== run end (error) ==="
    exit 1
}
