param(
    [Parameter(Mandatory = $true)]
    [string] $Slug,

    [string] $Branch = "",

    [string] $WorktreeDir = "",

    [int] $PollSeconds = 60,

    [int] $MaxMinutes = 1440
)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "feature-contract.ps1")

if ([string]::IsNullOrWhiteSpace($Branch)) {
    $Branch = "feature/$Slug"
}

$repoRoot = Get-RepositoryRoot
$mainRoot = Split-Path -Parent (Get-GitCommonDir)
if ([string]::IsNullOrWhiteSpace($WorktreeDir)) {
    $WorktreeDir = (Get-Location).Path
}

$stateDir = Get-FeatureStateDir

$safeName = $Slug -replace "[^A-Za-z0-9_.-]", "_"
$logPath = Join-Path $stateDir "$safeName.log"
$errorLogPath = Join-Path $stateDir "$safeName.err.log"
$lockPath = Join-Path $stateDir "$safeName.pid"

if (Test-Path -LiteralPath $lockPath -PathType Leaf) {
    $existingId = 0
    $rawId = [string](Get-Content -LiteralPath $lockPath -Raw -ErrorAction SilentlyContinue)
    if ([int]::TryParse($rawId.Trim(), [ref] $existingId)) {
        $existing = Get-Process -Id $existingId -ErrorAction SilentlyContinue
        if ($existing -and $existing.ProcessName -match "^(cmd|powershell|pwsh)$") {
            Write-Host "==> Ya existe un reconciliador local para $Slug (PID $existingId). No se inicia otro."
            exit 0
        }
    }
    Remove-Item -LiteralPath $lockPath -Force
}

$scriptPath = Join-Path $PSScriptRoot "reconcile-local-feature.ps1"

$powershell = (Get-Command powershell.exe -ErrorAction SilentlyContinue)
if (-not $powershell) {
    $powershell = Get-Command pwsh -ErrorAction Stop
}

function Convert-ToCmdQuoted {
    param([Parameter(Mandatory = $true)][string] $Value)
    return '"' + $Value + '"'
}

$innerCommand = @(
    (Convert-ToCmdQuoted $powershell.Source),
    "-NoProfile",
    "-ExecutionPolicy", "Bypass",
    "-File", (Convert-ToCmdQuoted $scriptPath),
    "-Slug", $Slug,
    "-Branch", $Branch,
    "-WorktreeDir", (Convert-ToCmdQuoted $WorktreeDir),
    "-PollSeconds", $PollSeconds,
    "-MaxMinutes", $MaxMinutes
) -join " "

$cmdLine = 'cmd.exe /s /c ' + (Convert-ToCmdQuoted ($innerCommand + " 1>" + (Convert-ToCmdQuoted $logPath) + " 2>" + (Convert-ToCmdQuoted $errorLogPath)))

Write-Host "==> Iniciando reconciliador local para $Slug. Log: $logPath"
try {
    $created = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{
        CommandLine = $cmdLine
        CurrentDirectory = $mainRoot
    }
    if ($created.ReturnValue -ne 0) {
        throw "Win32_Process.Create fallo con codigo $($created.ReturnValue)."
    }
    Set-Content -LiteralPath $lockPath -Value $created.ProcessId -Encoding ASCII
}
catch {
    Write-Warning "No pude iniciar el reconciliador local: $($_.Exception.Message)"
    Write-Warning "Esto no bloquea la PR: el cierre remoto lo realiza GitHub Actions y la limpieza local se reconciliara en la proxima ejecucion."
}
