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

function Invoke-Checked {
    param(
        [Parameter(Mandatory = $true)]
        [string] $FilePath,

        [Parameter(Mandatory = $true)]
        [string[]] $Arguments
    )

    & $FilePath @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed: $FilePath $($Arguments -join ' ')"
    }
}

function Test-GitSuccess {
    param([Parameter(Mandatory = $true)][string[]] $Arguments)
    & git @Arguments *> $null
    return ($LASTEXITCODE -eq 0)
}

if ([string]::IsNullOrWhiteSpace($Branch)) {
    $Branch = "feature/$Slug"
}

$repoRoot = Get-RepositoryRoot
if ([string]::IsNullOrWhiteSpace($WorktreeDir)) {
    $WorktreeDir = Join-Path (Join-Path (Split-Path -Parent $repoRoot) "worktrees") $Slug
}

$stateDir = Get-FeatureStateDir
$safeName = $Slug -replace "[^A-Za-z0-9_.-]", "_"
$lockPath = Join-Path $stateDir "$safeName.pid"

$deadline = (Get-Date).AddMinutes($MaxMinutes)
Write-Host "==> Reconciliador local activo para $Slug. Limpia solo si origin/develop contiene [x]."

try {
    while ((Get-Date) -lt $deadline) {
        Invoke-Checked "git" @("fetch", "origin", "develop", "--prune")
        $remoteRoadmap = (& git show "origin/develop`:ROADMAP.md") -join "`n"
        if ($LASTEXITCODE -ne 0) {
            throw "No pude leer origin/develop:ROADMAP.md."
        }

        $escapedSlug = [regex]::Escape($Slug)
        $doneCount = [regex]::Matches($remoteRoadmap, "(?m)^- \[x\] $escapedSlug(?=\s|$).*").Count
        $readyCount = [regex]::Matches($remoteRoadmap, "(?m)^- \[-\] $escapedSlug(?=\s|$).*").Count

        if ($doneCount -eq 1 -and $readyCount -eq 0) {
            Write-Host "==> Cierre remoto detectado para $Slug. Limpiando artefactos locales."
            $mainRoot = Split-Path -Parent (Get-GitCommonDir)
            $worktreeFullPath = [System.IO.Path]::GetFullPath($WorktreeDir)
            $mainRootFullPath = [System.IO.Path]::GetFullPath($mainRoot)
            if ([string]::Equals($worktreeFullPath, $mainRootFullPath, [System.StringComparison]::OrdinalIgnoreCase)) {
                throw "Me niego a remover el checkout principal ($mainRootFullPath) como si fuera un worktree de $Slug."
            }
            Set-Location -LiteralPath $mainRoot
            [Environment]::CurrentDirectory = $mainRoot
            if (Test-Path -LiteralPath $WorktreeDir) {
                Invoke-Checked "git" @("worktree", "remove", $WorktreeDir)
            }
            if (Test-GitSuccess @("rev-parse", "--verify", "--quiet", $Branch)) {
                Invoke-Checked "git" @("branch", "-d", $Branch)
            }
            Write-Host "==> Reconciliacion local completa para $Slug."
            exit 0
        }

        if ($doneCount -gt 1 -or $readyCount -gt 1) {
            throw "Estado remoto ambiguo para $Slug en ROADMAP.md: ready=$readyCount, done=$doneCount."
        }

        Start-Sleep -Seconds $PollSeconds
    }

    throw "Timeout esperando cierre remoto de $Slug en origin/develop."
}
finally {
    if (Test-Path -LiteralPath $lockPath -PathType Leaf) {
        Remove-Item -LiteralPath $lockPath -Force -ErrorAction SilentlyContinue
    }
}
