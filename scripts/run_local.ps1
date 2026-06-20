$ErrorActionPreference = "Stop"

if (Test-Path ".venv\Scripts\Activate.ps1") {
    . ".venv\Scripts\Activate.ps1"
}

python -m uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000