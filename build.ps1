$ErrorActionPreference = "Stop"

uv sync --extra build
uv run pyinstaller `
  --noconfirm `
  --clean `
  --onefile `
  --windowed `
  --name VaultController `
  main.py
