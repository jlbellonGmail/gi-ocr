[CmdletBinding()]
param([string] $Root = (Get-Location).Path)
$ErrorActionPreference = "Stop"
$Root = (Resolve-Path -LiteralPath $Root).Path
$failures = [System.Collections.Generic.List[string]]::new()
function Add-Failure([string] $Message) { [void] $failures.Add($Message) }
$workflowDir = Join-Path $Root ".github/workflows"
$workflows = Get-ChildItem -LiteralPath $workflowDir -File | Where-Object { $_.Extension -in ".yml", ".yaml" }
foreach ($workflow in $workflows) {
    $content = Get-Content -LiteralPath $workflow.FullName -Raw
    if ($content -notmatch '(?m)^permissions:') { Add-Failure "$($workflow.Name): falta permissions explícito" }
    if ($content -match '(?im)write-all') { Add-Failure "$($workflow.Name): write-all no permitido" }
    foreach ($match in [regex]::Matches($content, '(?m)^\s*-?\s*uses:\s*([^\s#]+)')) {
        $reference = $match.Groups[1].Value
        if ($reference -notmatch '@[0-9a-fA-F]{40}$') { Add-Failure "$($workflow.Name): acción sin SHA inmutable: $reference" }
    }
    if ($content -match 'upload-artifact|download-artifact' -and $content -notmatch 'retention-days:\s*[1-9][0-9]*') { Add-Failure "$($workflow.Name): artifact sin retention-days" }
}
foreach ($fileName in @("requirements-dev.txt", "requirements-docs.txt")) {
    $path = Join-Path $Root $fileName
    if (-not (Test-Path -LiteralPath $path)) { Add-Failure "${fileName}: falta manifiesto"; continue }
    foreach ($line in Get-Content -LiteralPath $path) {
        $trimmed = $line.Trim()
        if ($trimmed -and $trimmed -notmatch '^#' -and $trimmed -notmatch '^-r\s+' -and $trimmed -notmatch '==') { Add-Failure "${fileName}: dependencia no fijada: $trimmed" }
    }
}
$tracked = & git -C $Root ls-files
foreach ($relative in $tracked) {
    if ($relative -match '^(\.git/|\.audit/|runs/.*(jsonl|md)$)') { continue }
    $path = Join-Path $Root $relative
    if (Test-Path -LiteralPath $path -PathType Leaf) {
        $text = Get-Content -LiteralPath $path -Raw -ErrorAction SilentlyContinue
        if ($text -match '-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----|ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}') { Add-Failure "posible secreto en $relative" }
    }
}
if ($failures.Count) { $failures | ForEach-Object { Write-Error $_ }; exit 1 }
Write-Output "Supply chain OK: $($workflows.Count) workflows, acciones SHA-pinned, permisos explícitos y dependencias fijadas."
