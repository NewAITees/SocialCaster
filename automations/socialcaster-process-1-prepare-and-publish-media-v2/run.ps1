$ErrorActionPreference = "Stop"

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::InputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
$env:PYTHONIOENCODING = "utf-8"

$root = "C:\projects\SocialCaster"
$autoDir = Join-Path $root "automations\socialcaster-process-1-prepare-and-publish-media-v2"
$promptFile = Join-Path $autoDir "prompt.md"
$logDir = Join-Path $autoDir "logs"

if (-not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir | Out-Null
}

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$logFile = Join-Path $logDir "$timestamp.log"

Set-Location $root

Get-Content $promptFile -Raw | claude -p --add-dir $root --allowedTools "Bash Read Write Glob Grep" --output-format text 2>&1 | Out-File -FilePath $logFile -Encoding utf8
