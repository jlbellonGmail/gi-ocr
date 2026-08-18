param(
    [string] $PrRef = ""
)

$ErrorActionPreference = "Stop"

function Get-GitHubCliPath {
    $command = Get-Command gh -ErrorAction SilentlyContinue
    if ($command) {
        return $command.Source
    }

    $defaultPath = Join-Path $env:ProgramFiles "GitHub CLI\gh.exe"
    if (Test-Path -LiteralPath $defaultPath) {
        return $defaultPath
    }

    throw "GitHub CLI (gh) no esta disponible. Instalalo y autenticalo para verificar CI automaticamente."
}

$ghPath = Get-GitHubCliPath

if ([string]::IsNullOrWhiteSpace($PrRef)) {
    $PrRef = ((& git branch --show-current) -join "`n").Trim()
    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($PrRef)) {
        throw "No pude detectar la rama actual para ubicar la PR."
    }
}

Write-Host "==> Esperando checks de CI para PR/rama '$PrRef'..."
& $ghPath pr checks $PrRef --watch
if ($LASTEXITCODE -ne 0) {
    throw "Los checks de CI no terminaron en verde para '$PrRef'."
}

Write-Host "==> CI verde para '$PrRef'."
