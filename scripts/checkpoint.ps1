$ErrorActionPreference = "Stop"

Write-Host "== Git branch ==" -ForegroundColor Cyan
git branch --show-current

Write-Host "`n== Git status ==" -ForegroundColor Cyan
git status --short

Write-Host "`n== Project validation ==" -ForegroundColor Cyan
python scripts/validate_project.py

Write-Host "`n== Diff stat ==" -ForegroundColor Cyan
git diff --stat

