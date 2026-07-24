$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot\..
$env:UV_CACHE_DIR = Join-Path (Get-Location) ".uv-cache"
uv run python -m social_caster.cli daily-batch
