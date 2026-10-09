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
$manifestDir = Join-Path $root "input\manifests"
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

function Merge-PendingMemory {
    # claudeがmemory.mdへ直接追記できなかった場合、memory_pending_*.md へ退避される。
    # 過去に40件が未マージのまま放置され、記録欠落の原因になった。実行のたびに回収する。
    # 追記のみを行い、取り込みを確認してから退避ファイルを消す（全文上書きは事故のもと）。
    $pending = @(Get-ChildItem -Path $autoDir -Filter "memory_pending_*.md" -File -ErrorAction SilentlyContinue |
        Sort-Object Name)
    if ($pending.Count -eq 0) { return }

    $merged = 0
    foreach ($item in $pending) {
        $body = (Get-Content -LiteralPath $item.FullName -Raw -Encoding UTF8)
        if ([string]::IsNullOrWhiteSpace($body)) {
            Remove-Item -LiteralPath $item.FullName -Force -ErrorAction SilentlyContinue
            continue
        }
        # 退避ファイル側が既に出所マーカーを持つ場合は重ねない。
        $marker = "<!-- {0} -->" -f $item.Name
        if ($body.TrimStart().StartsWith($marker)) {
            $entry = "`n{0}`n" -f $body.Trim()
        }
        else {
            $entry = "`n{0}`n{1}`n" -f $marker, $body.TrimEnd()
        }
        Add-Content -Path $memoryFile -Value $entry -Encoding utf8
        # 取り込めたことを確認してから退避ファイルを消す。
        $probe = $body.TrimEnd()
        if ($probe.Length -gt 40) { $probe = $probe.Substring(0, 40) }
        if ((Get-Content -Path $memoryFile -Raw -Encoding UTF8).Contains($probe)) {
            Remove-Item -LiteralPath $item.FullName -Force -ErrorAction SilentlyContinue
            $merged++
        }
    }
    if ($merged -gt 0) {
        Add-Content -Path $logFile -Encoding utf8 `
            -Value "==== memory: merged $merged pending record(s) ===="
    }
}

function Remove-WorkspaceJunk {
    # JSON生成ステップが検証用の使い捨てファイルをリポジトリへ書き残すことがある。
    # 放置すると ruff / mypy がそれらを拾って pre-commit が落ちるため毎回消す。
    # 画像とmanifestには触れない。
    $targets = @(
        (Join-Path $root "_*.py"),
        (Join-Path $root "_*.ps1"),
        (Join-Path $root "_*.sh"),
        (Join-Path $root "_*.js"),
        (Join-Path $root "_*.txt"),
        (Join-Path $inbox "_*"),
        (Join-Path $manifestDir "_*"),
        (Join-Path $inbox "Thumbs.db"),
        (Join-Path $manifestDir "Thumbs.db")
    )
    $removed = 0
    foreach ($pattern in $targets) {
        foreach ($item in (Get-ChildItem -Path $pattern -File -ErrorAction SilentlyContinue)) {
            # 画像とmanifestは絶対に消さない。
            if ($item.Extension -in ".png", ".jpg", ".jpeg", ".json") { continue }
            Remove-Item -LiteralPath $item.FullName -Force -ErrorAction SilentlyContinue
            $removed++
        }
    }
    if ($removed -gt 0) {
        Add-Content -Path $logFile -Encoding utf8 -Value "==== cleanup: removed $removed junk file(s) ===="
    }
}

function Remove-OldLogs {
    # ログは1日1本増え続けるため、直近30日分だけ残す。
    $limit = (Get-Date).AddDays(-30)
    $old = @(
        Get-ChildItem -Path $logDir -Filter "*.log" -File -ErrorAction SilentlyContinue |
            Where-Object { $_.LastWriteTime -lt $limit }
    )
    foreach ($item in $old) {
        Remove-Item -LiteralPath $item.FullName -Force -ErrorAction SilentlyContinue
    }
    if ($old.Count -gt 0) {
        Add-Content -Path $logFile -Encoding utf8 -Value "==== cleanup: removed $($old.Count) old log(s) ===="
    }
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
        $needInstagram = $status.NEED_INSTAGRAM
        $pinterestEnabled = $status.PINTEREST_ENABLED -eq 1
        $needPinterest = if ($pinterestEnabled) { $status.NEED_PINTEREST } else { 0 }
        # サービスごとの不足・空き枠は互いに混ぜない。片方が充足していても、
        # もう片方の補充・リトライを止めてはならない。
        $hasFailedBacklog = ($status.MEDIA_FAILED -gt 0) -or ($status.IG_FAILED -gt 0) -or `
            ($pinterestEnabled -and $status.PIN_FAILED -gt 0)
        Add-Content -Path $logFile -Value (
            "==== iteration {0}: instagram(stock={1} room={2} need={3}) pinterest(stock={4} room={5} need={6}) limit={7} failed_backlog={8} ====" -f `
                $iteration, $status.STOCK_INSTAGRAM, $status.ROOM_INSTAGRAM, $needInstagram, `
                $status.STOCK_PINTEREST, $status.ROOM_PINTEREST, $needPinterest, `
                $status.SCHEDULED_LIMIT, $hasFailedBacklog
        )

        if ($needInstagram -le 0 -and -not $hasFailedBacklog) {
            if ($needPinterest -gt 0) {
                # Pinterest専用の補充manifestは未実装（instagram_textが必須のため）。
                # Instagramの需要がない限り、この不足は自動では解消されない。
                $stopReason = "target stock reached (instagram); pinterest-only backfill not implemented, NEED_PINTEREST=$needPinterest remains"
            }
            else {
                $stopReason = "target stock reached"
            }
            break
        }

        $jsonCount = 0
        if ($needInstagram -gt 0) {
            $unprocessedImages = @(
                Get-ChildItem -Path $inbox -File -ErrorAction SilentlyContinue |
                    Where-Object {
                        $_.Extension -in ".png", ".jpg", ".jpeg" -and
                        -not (Test-Path (Join-Path $manifestDir ($_.Name + ".json")))
                    }
            )
            if ($unprocessedImages.Count -eq 0) {
                if (-not $hasFailedBacklog) {
                    $stopReason = "no unprocessed images in input/inbox"
                    break
                }
                Add-Content -Path $logFile -Value "==== no unprocessed images; retrying existing failures only ===="
            }
            else {
                $jsonCount = [Math]::Min($needInstagram, $unprocessedImages.Count)
                $services = if ($needPinterest -gt 0) { "instagram,pinterest" } else { "instagram" }
                $prompt = (Get-Content $promptFile -Raw -Encoding UTF8).
                    Replace("{{COUNT}}", [string]$jsonCount).
                    Replace("{{SERVICES}}", $services)

                # claudeはJSON生成だけを担当し、公開・投稿はPythonを直接実行する。
                Add-Content -Path $logFile -Value "==== step1: json generation (claude), count=$jsonCount, services=$services ===="
                $savedErrorActionPreference = $ErrorActionPreference
                try {
                    $ErrorActionPreference = "Continue"
                    $prompt | claude -p --setting-sources project --add-dir $root `
                        --allowedTools "Read Edit Write Glob" --output-format text 2>&1 |
                        Out-File -FilePath $logFile -Encoding utf8 -Append
                    $claudeExit = $LASTEXITCODE
                }
                finally {
                    $ErrorActionPreference = $savedErrorActionPreference
                }
                if ($claudeExit -ne 0) { throw "claude JSON generation failed (exit=$claudeExit)" }

                Merge-PendingMemory
                Remove-WorkspaceJunk

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
            }
        }

        # MEDIA_FAILED の滞留分は、新規が0件でもリトライ枠(MEDIA_RETRY_SLOTS=1)を
        # 使えるよう最低1件のcountを渡す。新規需要がなければpublish-mediaを呼ばない。
        $mediaCount = if ($jsonCount -gt 0) { $jsonCount } elseif ($status.MEDIA_FAILED -gt 0) { 1 } else { 0 }
        if ($mediaCount -gt 0) {
            Add-Content -Path $logFile -Value "==== step2: publish-media, count=$mediaCount ===="
            $savedErrorActionPreference = $ErrorActionPreference
            try {
                $ErrorActionPreference = "Continue"
                & $python -m social_caster.cli publish-media --count $mediaCount 2>&1 |
                    Out-File -FilePath $logFile -Encoding utf8 -Append
                $mediaExit = $LASTEXITCODE
            }
            finally {
                $ErrorActionPreference = $savedErrorActionPreference
            }
            if ($mediaExit -ne 0) { throw "publish-media failed (exit=$mediaExit)" }
        }

        # publish-social は呼び出しごとにBufferの空き枠を自分で読み、サービス別に
        # 試行を打ち切る（social_caster.cli）。count は新規へ時刻を割り当てる件数だけを
        # 決め、既存の未成立予約のリトライはcountに関わらず毎回走る。
        # ENABLE_TWITTER=false の間はXへ投稿せず、Instagramだけを予約する。
        Add-Content -Path $logFile -Value "==== step3: publish-social, count=$jsonCount ===="
        $savedErrorActionPreference = $ErrorActionPreference
        try {
            $ErrorActionPreference = "Continue"
            & $python -m social_caster.cli publish-social --count $jsonCount 2>&1 |
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
        $finalPinterestEnabled = $finalStatus.PINTEREST_ENABLED -eq 1
        $finalHasFailedBacklog = ($finalStatus.MEDIA_FAILED -gt 0) -or ($finalStatus.IG_FAILED -gt 0) -or `
            ($finalPinterestEnabled -and $finalStatus.PIN_FAILED -gt 0)
        if ($finalStatus.NEED_INSTAGRAM -le 0 -and -not $finalHasFailedBacklog) {
            $stopReason = "target stock reached"
        }
    }
}
catch {
    $automationExit = 1
    $stopReason = $_.Exception.Message
    Add-Content -Path $logFile -Value "==== error: $stopReason ===="
}
finally {
    Merge-PendingMemory
    Remove-WorkspaceJunk
    Remove-OldLogs
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
