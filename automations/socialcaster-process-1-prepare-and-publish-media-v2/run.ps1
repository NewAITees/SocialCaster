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
$statusFile = Join-Path $root "automation\status.py"
$inbox = Join-Path $root "input\inbox"
$python = Join-Path $root ".venv\Scripts\python.exe"
$maxIterations = 10

if (-not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir | Out-Null
}

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$logFile = Join-Path $logDir "$timestamp.log"

Set-Location $root

function Get-Status {
    $raw = & $python $statusFile
    if ($LASTEXITCODE -ne 0) { throw "status.py failed (exit=$LASTEXITCODE)" }
    $values = @{}
    foreach ($token in ($raw -split '\s+')) {
        if ($token -match '^(\w+)=(\d+)$') { $values[$matches[1]] = [int]$matches[2] }
    }
    return $values
}

function Write-StopReason {
    param([string]$Reason)
    Add-Content -Path $logFile -Value "==== stop: $Reason ===="
    $entry = "## {0}`n- stop reason: {1}`n- log: {2}`n" -f `
        (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Reason, (Split-Path $logFile -Leaf)
    Add-Content -Path $memoryFile -Value $entry -Encoding utf8
}

$mediaExit = 0
$socialExit = 0
$stopReason = "maximum iteration cap reached"
$automationExit = 0

try {
    for ($iteration = 1; $iteration -le $maxIterations; $iteration++) {
        $status = Get-Status
        $refill = $status.REFILL
        Add-Content -Path $logFile -Value (
            "==== iteration {0}: stock={1} target={2} cap={3} refill={4} ====" -f `
                $iteration, $status.STOCK, $status.TARGET_STOCK, $status.RESERVATION_CAP, $refill
        )
        if ($refill -le 0) {
            $stopReason = "target stock reached"
            break
        }

        $unprocessedImages = @(
            Get-ChildItem -Path $inbox -File -ErrorAction SilentlyContinue |
                Where-Object {
                    $_.Extension -in ".png", ".jpg", ".jpeg" -and
                    -not (Test-Path ($_.FullName + ".json"))
                }
        )
        if ($unprocessedImages.Count -eq 0) {
            $stopReason = "no unprocessed images in input/inbox"
            break
        }
        $count = [Math]::Min($refill, $unprocessedImages.Count)
        $prompt = (Get-Content $promptFile -Raw -Encoding UTF8).Replace("{{COUNT}}", [string]$count)

        # claudeはJSON生成だけを担当し、公開・投稿はPythonを直接実行する。
        Add-Content -Path $logFile -Value "==== step1: json generation (claude), count=$count ===="
        $prompt | claude -p --add-dir $root --allowedTools "Read Write Glob" --output-format text 2>&1 |
            Out-File -FilePath $logFile -Encoding utf8 -Append
        if ($LASTEXITCODE -ne 0) { throw "claude JSON generation failed (exit=$LASTEXITCODE)" }

        Add-Content -Path $logFile -Value "==== step2: publish-media, count=$count ===="
        & $python -m social_caster.cli publish-media --count $count 2>&1 |
            Out-File -FilePath $logFile -Encoding utf8 -Append
        $mediaExit = $LASTEXITCODE
        if ($mediaExit -ne 0) { throw "publish-media failed (exit=$mediaExit)" }

        # ENABLE_TWITTER=false の間はXへ投稿せず、Instagramだけを予約する。
        Add-Content -Path $logFile -Value "==== step3: publish-social, count=$count ===="
        & $python -m social_caster.cli publish-social --count $count 2>&1 |
            Out-File -FilePath $logFile -Encoding utf8 -Append
        $socialExit = $LASTEXITCODE
        if ($socialExit -ne 0) { throw "publish-social failed (exit=$socialExit)" }
    }

    if ($stopReason -eq "maximum iteration cap reached") {
        $finalStatus = Get-Status
        if ($finalStatus.REFILL -le 0) { $stopReason = "target stock reached" }
    }
}
catch {
    $automationExit = 1
    $stopReason = $_.Exception.Message
    Add-Content -Path $logFile -Value "==== error: $stopReason ===="
}
finally {
    Write-StopReason $stopReason
    $summary = "## {0}`n- publish-media exit: {1}`n- publish-social exit: {2}`n- log: {3}`n" -f `
        (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $mediaExit, $socialExit, (Split-Path $logFile -Leaf)
    Add-Content -Path $memoryFile -Value $summary -Encoding utf8
}

exit $automationExit
