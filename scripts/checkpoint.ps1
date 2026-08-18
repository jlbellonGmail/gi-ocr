$ErrorActionPreference = "Stop"

Write-Host "== Git branch ==" -ForegroundColor Cyan
git branch --show-current

Write-Host "`n== Git status ==" -ForegroundColor Cyan
git status --short

Write-Host "`n== Tests ==" -ForegroundColor Cyan
pytest -q

Write-Host "`n== Diff stat ==" -ForegroundColor Cyan
git diff --stat

