[CmdletBinding()]
param(
    [string]$ShareName = "SocialCasterInput"
)

$ErrorActionPreference = "Stop"
$repositoryRoot = Split-Path -Parent $PSScriptRoot
$inputPath = Join-Path $repositoryRoot "input"
$identity = "$env:USERDOMAIN\$env:USERNAME"
$firewallRuleName = "SocialCaster SMB input"

if (-not (Test-Path -LiteralPath $inputPath)) {
    New-Item -ItemType Directory -Path $inputPath -Force | Out-Null
}

$share = Get-SmbShare -Name $ShareName -ErrorAction SilentlyContinue
if ($null -eq $share) {
    New-SmbShare -Name $ShareName -Path $inputPath -ChangeAccess $identity -Description "SocialCaster input folders" | Out-Null
} else {
    if ($share.Path -ne $inputPath) {
        throw "既存の共有 '$ShareName' は別のパスを指しています: $($share.Path)"
    }
    Grant-SmbShareAccess -Name $ShareName -AccountName $identity -AccessRight Change -Force | Out-Null
}

if (-not (Get-NetFirewallRule -DisplayName $firewallRuleName -ErrorAction SilentlyContinue)) {
    New-NetFirewallRule -DisplayName $firewallRuleName -Direction Inbound -Protocol TCP -LocalPort 445 -Action Allow -Profile Private | Out-Null
}

$computerName = (Get-CimInstance Win32_ComputerSystem).Name
Write-Output "SMB共有を設定しました: \\$computerName\$ShareName"
Write-Output "共有先: $inputPath"
Write-Output "接続ユーザー: $identity"
