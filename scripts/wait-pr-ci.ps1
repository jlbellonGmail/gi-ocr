param(
    [string] $PrRef = "",

    [switch] $Snapshot
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

function Invoke-GhCaptured {
    param(
        [Parameter(Mandatory = $true)]
        [string] $GitHubCliPath,

        [Parameter(Mandatory = $true)]
        [string[]] $Arguments
    )

    $previousErrorActionPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        $output = & $GitHubCliPath @Arguments 2>&1
        $exitCode = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $previousErrorActionPreference
    }
    $text = (($output | ForEach-Object { $_.ToString() }) -join "`n").Trim()

    return [pscustomobject]@{
        ExitCode = $exitCode
        Text = $text
    }
}

$ghPath = Get-GitHubCliPath

if ([string]::IsNullOrWhiteSpace($PrRef)) {
    $PrRef = ((& git branch --show-current) -join "`n").Trim()
    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($PrRef)) {
        throw "No pude detectar la rama actual para ubicar la PR."
    }
}

if ($Snapshot) {
    # Modo no bloqueante: una sola consulta puntual de PR/CI, sin --watch.
    # Siempre exit 0, salvo que la PR no exista todavia para $PrRef.
    Write-Host "==> Consultando snapshot de PR/CI para '$PrRef' (no bloqueante)..."

    $view = Invoke-GhCaptured -GitHubCliPath $ghPath -Arguments @(
        "pr", "view", $PrRef,
        "--json", "number,url,state,mergeStateStatus"
    )

    if ($view.ExitCode -ne 0) {
        Write-Host "==> No existe PR para '$PrRef' todavia (gh no pudo resolverla)."
        if (-not [string]::IsNullOrWhiteSpace($view.Text)) {
            Write-Host $view.Text
        }
        exit 1
    }

    try {
        $pr = $view.Text | ConvertFrom-Json
        Write-Host "==> PR #$($pr.number): $($pr.url)"
        Write-Host "==> Estado: $($pr.state) | mergeStateStatus: $($pr.mergeStateStatus)"
    }
    catch {
        Write-Host "==> PR encontrada para '$PrRef', pero no se pudo interpretar el JSON de 'gh pr view':"
        Write-Host $view.Text
    }

    $checks = Invoke-GhCaptured -GitHubCliPath $ghPath -Arguments @("pr", "checks", $PrRef)
    Write-Host "==> Checks (snapshot, sin --watch):"
    if ([string]::IsNullOrWhiteSpace($checks.Text)) {
        Write-Host "(sin checks reportados todavia)"
    }
    else {
        Write-Host $checks.Text
    }
    if ($checks.ExitCode -ne 0) {
        Write-Host "==> Nota: 'gh pr checks' devolvio codigo $($checks.ExitCode) (puede indicar checks en rojo o pendientes; esto es solo informativo, no bloquea -Snapshot)."
    }

    exit 0
}

Write-Host "==> Esperando checks de CI para PR/rama '$PrRef'..."
& $ghPath pr checks $PrRef --watch
if ($LASTEXITCODE -ne 0) {
    throw "Los checks de CI no terminaron en verde para '$PrRef'."
}

Write-Host "==> CI verde para '$PrRef'."
