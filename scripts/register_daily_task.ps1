$ErrorActionPreference = "Stop"
$projectRoot = Split-Path $PSScriptRoot -Parent
$runScript = Join-Path $projectRoot "scripts\run_daily.ps1"
$action = New-ScheduledTaskAction -Execute "PowerShell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$runScript`""
$trigger = New-ScheduledTaskTrigger -Daily -At 09:00
Register-ScheduledTask -TaskName "SocialCaster Daily Batch" -Action $action -Trigger $trigger -Description "Run SocialCaster once per day" -Force
