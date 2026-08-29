$ErrorActionPreference = "Stop"

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::InputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
$env:PYTHONIOENCODING = "utf-8"

$root = "C:\projects\SocialCaster"
$autoDir = Join-Path $root "automations\socialcaster-process-1-prepare-and-publish-media-v2"
$promptFile = Join-Path $autoDir "prompt.md"
$logDir = Join-Path $autoDir "logs"
$memoryFile = Join-Path $autoDir "memory.md"
$python = Join-Path $root ".venv\Scripts\python.exe"

if (-not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir | Out-Null
}

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$logFile = Join-Path $logDir "$timestamp.log"

Set-Location $root

# Step 1: claudeはJSON生成のみ担当（Bash不使用。長時間コマンドを持たないため
# ヘッドレス(-p)モードのバックグラウンド化問題が起きない）。
Add-Content -Path $logFile -Value "==== step1: json generation (claude) ===="
Get-Content $promptFile -Raw | claude -p --add-dir $root --allowedTools "Read Write Glob" --output-format text 2>&1 |
    Out-File -FilePath $logFile -Encoding utf8 -Append

# Step 2/3: 画像公開・SNS投稿はLLMを介さず直接pythonで実行する。
# ENABLE_TWITTER=false の間はXへは投稿されず、Instagramのみキューが処理される。
Add-Content -Path $logFile -Value "==== step2: publish-media ===="
& $python -m social_caster.cli publish-media 2>&1 | Out-File -FilePath $logFile -Encoding utf8 -Append
$mediaExit = $LASTEXITCODE

Add-Content -Path $logFile -Value "==== step3: publish-social ===="
& $python -m social_caster.cli publish-social 2>&1 | Out-File -FilePath $logFile -Encoding utf8 -Append
$socialExit = $LASTEXITCODE

$summary = "## {0}`n- publish-media exit: {1}`n- publish-social exit: {2}`n- log: {3}`n" -f `
    (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $mediaExit, $socialExit, (Split-Path $logFile -Leaf)
Add-Content -Path $memoryFile -Value $summary -Encoding utf8
