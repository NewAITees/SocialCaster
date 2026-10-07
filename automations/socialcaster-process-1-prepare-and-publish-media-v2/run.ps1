$ErrorActionPreference = "Stop"

# BOM無しのUTF8を使う。[System.Text.Encoding]::UTF8 はプリアンブルを持つため、
# claudeへのパイプ先頭にBOMが混入する。
[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)
[Console]::InputEncoding = New-Object System.Text.UTF8Encoding($false)
$OutputEncoding = New-Object System.Text.UTF8Encoding($false)
$env:PYTHONIOENCODING = "utf-8"

$root = "D:\projects\SocialCaster"
$autoDir = Join-Path $root "automations\socialcaster-process-1-prepare-and-publish-media-v2"
$promptFile = Join-Path $autoDir "prompt.md"
$logDir = Join-Path $autoDir "logs"
$memoryFile = Join-Path $autoDir "memory.md"
$statusFile = Join-Path $root "automation\status.py"
$verifyManifests = Join-Path $root "scripts\verify_manifests.py"
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
    $savedErrorActionPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = "Continue"
        $raw = & $python $statusFile 2>&1
        $statusExit = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $savedErrorActionPreference
    }
    $raw | Where-Object { $_ -is [System.Management.Automation.ErrorRecord] } |
        Out-File -FilePath $logFile -Encoding utf8 -Append
    if ($statusExit -ne 0) { throw "status.py failed (exit=$statusExit)" }
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

function Send-DiscordNotification {
    param([string]$Title, [string]$Reason, [string[]]$Notes, [string]$LogPath)

    # webhook URLは.env（git管理外）にのみ置く。未設定なら通知せず黙って戻る。
    $envFile = Join-Path $root ".env"
    if (-not (Test-Path $envFile)) { return }
    $webhook = $null
    foreach ($line in (Get-Content $envFile -Encoding UTF8)) {
        if ($line -match '^\s*DISCORD_WEBHOOK_URL\s*=\s*(\S+)\s*$') { $webhook = $matches[1] }
    }
    if ([string]::IsNullOrWhiteSpace($webhook)) { return }

    $tail = ""
    if (Test-Path $LogPath) {
        $tail = Get-Content $LogPath -Raw -Encoding UTF8
        if ($tail.Length -gt 1200) { $tail = $tail.Substring($tail.Length - 1200) }
    }

    $lines = @(
        ("**" + $Title + "**"),
        ("- 日時: " + (Get-Date -Format "yyyy-MM-dd HH:mm:ss")),
        ("- 停止理由: " + $Reason),
        ("- ログ: " + (Split-Path $LogPath -Leaf))
    )
    foreach ($note in $Notes) { $lines += ("- 警告: " + $note) }
    # ``` をPowerShellのエスケープ文字と衝突させずに組み立てる。
    $fence = ([string][char]96) * 3
    $lines += @("", $fence, $tail, $fence)
    $content = $lines -join "`n"
    # Discordのメッセージ上限は2000文字。
    if ($content.Length -gt 1990) { $content = $content.Substring(0, 1990) }

    # 本処理はWindows PowerShell 5.1で動くため、TLS1.2を明示する。
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    $body = [System.Text.Encoding]::UTF8.GetBytes((@{ content = $content } | ConvertTo-Json -Compress))
    Invoke-RestMethod -Uri $webhook -Method Post `
        -ContentType "application/json; charset=utf-8" -Body $body | Out-Null
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
            "==== iteration {0}: stock_instagram={1} stock_pinterest={2} target={3} cap={4} refill={5} ====" -f `
                $iteration, $status.STOCK_INSTAGRAM, $status.STOCK_PINTEREST, `
                $status.TARGET_STOCK, $status.RESERVATION_CAP, $refill
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
        $savedErrorActionPreference = $ErrorActionPreference
        try {
            $ErrorActionPreference = "Continue"
            $prompt | claude -p --setting-sources project --add-dir $root `
                --allowedTools "Read Write Glob" --output-format text 2>&1 |
                Out-File -FilePath $logFile -Encoding utf8 -Append
            $claudeExit = $LASTEXITCODE
        }
        finally {
            $ErrorActionPreference = $savedErrorActionPreference
        }
        if ($claudeExit -ne 0) { throw "claude JSON generation failed (exit=$claudeExit)" }

        Add-Content -Path $logFile -Value "==== validation: verify-manifests ===="
        $savedErrorActionPreference = $ErrorActionPreference
        try {
            $ErrorActionPreference = "Continue"
            & $python $verifyManifests 2>&1 |
                Out-File -FilePath $logFile -Encoding utf8 -Append
            $validationExit = $LASTEXITCODE
        }
        finally {
            $ErrorActionPreference = $savedErrorActionPreference
        }
        if ($validationExit -ne 0) { throw "manifest validation failed (exit=$validationExit)" }

        Add-Content -Path $logFile -Value "==== step2: publish-media, count=$count ===="
        $savedErrorActionPreference = $ErrorActionPreference
        try {
            $ErrorActionPreference = "Continue"
            & $python -m social_caster.cli publish-media --count $count 2>&1 |
                Out-File -FilePath $logFile -Encoding utf8 -Append
            $mediaExit = $LASTEXITCODE
        }
        finally {
            $ErrorActionPreference = $savedErrorActionPreference
        }
        if ($mediaExit -ne 0) { throw "publish-media failed (exit=$mediaExit)" }

        # ENABLE_TWITTER=false の間はXへ投稿せず、Instagramだけを予約する。
        Add-Content -Path $logFile -Value "==== step3: publish-social, count=$count ===="
        $savedErrorActionPreference = $ErrorActionPreference
        try {
            $ErrorActionPreference = "Continue"
            & $python -m social_caster.cli publish-social --count $count 2>&1 |
                Out-File -FilePath $logFile -Encoding utf8 -Append
            $socialExit = $LASTEXITCODE
        }
        finally {
            $ErrorActionPreference = $savedErrorActionPreference
        }
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

    # exitが0でも「静かに何も投稿しない」ことがある（publish-mediaは失敗してもexit 0を返す）。
    # 完走したかどうかではなく、終了時点の在庫と失敗件数で結果を判定する。
    $warnings = @()
    try {
        $closingStatus = Get-Status
        if ($closingStatus.MEDIA_FAILED -gt 0) {
            $warnings += ("公開に失敗したままの投稿が {0} 件あります (MEDIA_FAILED)" -f $closingStatus.MEDIA_FAILED)
        }
        if ($closingStatus.STOCK_INSTAGRAM -lt $closingStatus.TARGET_STOCK) {
            $warnings += ("Instagram予約在庫が目標に届いていません: STOCK_INSTAGRAM={0} TARGET={1}" -f `
                $closingStatus.STOCK_INSTAGRAM, $closingStatus.TARGET_STOCK)
        }
        if ($closingStatus.PINTEREST_ENABLED -eq 1 -and `
            $closingStatus.STOCK_PINTEREST -lt $closingStatus.TARGET_STOCK) {
            $warnings += ("Pinterest予約在庫が目標に届いていません: STOCK_PINTEREST={0} TARGET={1}" -f `
                $closingStatus.STOCK_PINTEREST, $closingStatus.TARGET_STOCK)
        }
    }
    catch {
        $warnings += ("実行後の在庫確認に失敗しました: " + $_.Exception.Message)
    }

    if ($automationExit -ne 0 -or $warnings.Count -gt 0) {
        if ($automationExit -ne 0) {
            $title = "SocialCaster 自動実行が失敗しました"
        }
        else {
            $title = "SocialCaster 自動実行は完走しましたが結果が想定外です"
        }
        # 通知の失敗で本処理の結果を壊さないため、例外はログに残して飲み込む。
        try {
            Send-DiscordNotification -Title $title -Reason $stopReason -Notes $warnings -LogPath $logFile
        }
        catch {
            Add-Content -Path $logFile -Encoding utf8 `
                -Value ("==== discord notification failed: " + $_.Exception.Message + " ====")
        }
    }
}

exit $automationExit
