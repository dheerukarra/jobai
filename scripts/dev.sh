#!/usr/bin/env sh
# Sync dependencies with the venv kept OUTSIDE OneDrive.
export UV_PROJECT_ENVIRONMENT="${UV_PROJECT_ENVIRONMENT:-$HOME/.venvs/jobai}"
cd "$(dirname "$0")/.." && uv sync
