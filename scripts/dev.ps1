# Sync dependencies with the venv kept OUTSIDE OneDrive.
$env:UV_PROJECT_ENVIRONMENT = Join-Path $HOME ".venvs\jobai"
Set-Location (Join-Path $PSScriptRoot "..")
uv sync
