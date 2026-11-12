# Start the live office dashboard (background, localhost only) and open it in the browser.
# New script for ticket OFF-2. The venv is kept OUTSIDE OneDrive.
$env:UV_PROJECT_ENVIRONMENT = Join-Path $HOME ".venvs\jobai"
Set-Location (Join-Path $PSScriptRoot "..")
uv run python -m jobai.office up @args
