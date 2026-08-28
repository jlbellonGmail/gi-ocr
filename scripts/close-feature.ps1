param(
    [Parameter(Mandatory = $true)]
    [string] $Slug,

    [int] $PrNumber = 0,

    [string] $Branch = "",

    [string] $WorktreeDir = "",

    [switch] $SkipLocalCleanup
)

$ErrorActionPreference = "Stop"

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

function Get-CheckedOutput {
    param(
        [Parameter(Mandatory = $true)]
        [string] $FilePath,

        [Parameter(Mandatory = $true)]
        [string[]] $Arguments
    )

    $output = & $FilePath @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed: $FilePath $($Arguments -join ' ')"
    }

    return ($output -join "`n").Trim()
}

function Test-GitSuccess {
    param(
        [Parameter(Mandatory = $true)]
        [string[]] $Arguments
    )

    & git @Arguments *> $null
    return ($LASTEXITCODE -eq 0)
}

function Get-GitHubCliPath {
    $command = Get-Command gh -ErrorAction SilentlyContinue
    if ($command) {
        return $command.Source
    }

    $defaultPath = Join-Path $env:ProgramFiles "GitHub CLI\gh.exe"
    if (Test-Path -LiteralPath $defaultPath) {
        return $defaultPath
    }

    throw "GitHub CLI (gh) no esta disponible. El cierre post-merge requiere confirmar la PR en GitHub."
}

function Assert-CleanWorktree {
    param(
        [Parameter(Mandatory = $true)]
        [string] $Context
    )

    $status = Get-CheckedOutput "git" @("status", "--short")
    if (-not [string]::IsNullOrWhiteSpace($status)) {
        throw "Hay cambios locales incompatibles $Context. No se continua.`n$status"
    }
}

function Get-RoadmapState {
    param(
        [Parameter(Mandatory = $true)]
        [string] $Content,

        [Parameter(Mandatory = $true)]
        [string] $Slug
    )

    $escapedSlug = [regex]::Escape($Slug)
    $suffix = "(?=\s|$)"
    $states = [ordered]@{
        Pending = [regex]::Matches($Content, "(?m)^- \[ \] $escapedSlug$suffix.*").Count
        Ready = [regex]::Matches($Content, "(?m)^- \[-\] $escapedSlug$suffix.*").Count
        Done = [regex]::Matches($Content, "(?m)^- \[x\] $escapedSlug$suffix.*").Count
    }

    return [pscustomobject]$states
}

function Assert-RoadmapClosedOnce {
    param(
        [Parameter(Mandatory = $true)]
        [string] $Content,

        [Parameter(Mandatory = $true)]
        [string] $Slug,

        [Parameter(Mandatory = $true)]
        [string] $Context
    )

    $state = Get-RoadmapState $Content $Slug
    if ($state.Done -ne 1 -or $state.Ready -ne 0) {
        throw "Validacion fallida ${Context}: ROADMAP.md debe contener exactamente una entrada [x] $Slug y ninguna [-] $Slug. Estado: pending=$($state.Pending), ready=$($state.Ready), done=$($state.Done)."
    }
}

function Assert-RoadmapCanClose {
    param(
        [Parameter(Mandatory = $true)]
        [string] $Content,

        [Parameter(Mandatory = $true)]
        [string] $Slug
    )

    $state = Get-RoadmapState $Content $Slug
    $total = $state.Pending + $state.Ready + $state.Done

    if ($total -eq 0) {
        throw "No existe una entrada exacta para '$Slug' en ROADMAP.md."
    }

    if ($total -gt 1) {
        throw "ROADMAP.md contiene mas de una coincidencia exacta para '$Slug'. Estado: pending=$($state.Pending), ready=$($state.Ready), done=$($state.Done)."
    }

    if ($state.Done -eq 1) {
        return "already-closed"
    }

    if ($state.Ready -eq 1) {
        return "ready"
    }

    throw "'$Slug' existe en ROADMAP.md pero no esta en READY_FOR_PR. El cierre post-merge solo cambia [-] a [x]."
}

function Confirm-PrMergedIntoBase {
    param(
        [Parameter(Mandatory = $true)]
        [string] $GitHubCliPath,

        [string] $Branch,

        [int] $PrNumber = 0,

        [Parameter(Mandatory = $true)]
        [string] $BaseBranch
    )

    $prRef = if ($PrNumber -gt 0) { $PrNumber.ToString() } else { $Branch }
    if ([string]::IsNullOrWhiteSpace($prRef)) {
        throw "Debe informarse Branch o PrNumber para confirmar la PR mergeada."
    }

    Write-Host "==> Confirmando en GitHub que la PR '$prRef' esta MERGED contra $BaseBranch..."
    $jsonText = Get-CheckedOutput $GitHubCliPath @(
        "pr", "view", $prRef,
        "--json", "state,mergedAt,baseRefName,headRefName,number"
    )

    $pr = $jsonText | ConvertFrom-Json
    if ($pr.state -ne "MERGED") {
        throw "La PR '$prRef' no esta mergeada. Estado informado por GitHub: $($pr.state)."
    }

    if ($pr.baseRefName -ne $BaseBranch) {
        throw "La PR '$prRef' fue mergeada contra '$($pr.baseRefName)', no contra '$BaseBranch'."
    }

    if ([string]::IsNullOrWhiteSpace($pr.mergedAt)) {
        throw "GitHub informa MERGED para '$prRef' pero no entrego mergedAt. No se continua."
    }

    if (-not [string]::IsNullOrWhiteSpace($Branch) -and $pr.headRefName -ne $Branch) {
        throw "La PR '$prRef' pertenece a head '$($pr.headRefName)', no a '$Branch'."
    }

    Write-Host "==> PR #$($pr.number) confirmada como MERGED en $BaseBranch ($($pr.mergedAt))."
}

function Remove-LocalFeatureArtifacts {
    param(
        [Parameter(Mandatory = $true)]
        [string] $Branch,

        [Parameter(Mandatory = $true)]
        [string] $WorktreeDir
    )

    Write-Host "==> Limpiando worktree y rama local..."
    if (Test-Path -LiteralPath $WorktreeDir) {
        Invoke-Checked "git" @("worktree", "remove", $WorktreeDir)
        Write-Host "==> Worktree eliminado: $WorktreeDir"
    }
    else {
        Write-Host "==> No existe worktree local para eliminar: $WorktreeDir"
    }

    if (Test-GitSuccess @("rev-parse", "--verify", "--quiet", $Branch)) {
        Invoke-Checked "git" @("branch", "-d", $Branch)
        Write-Host "==> Rama local eliminada: $Branch"
    }
    else {
        Write-Host "==> No existe rama local para eliminar: $Branch"
    }
}

if ([string]::IsNullOrWhiteSpace($Branch)) {
    $Branch = "feature/$Slug"
}

$baseBranch = "develop"
$ghPath = Get-GitHubCliPath
$repoRoot = Get-CheckedOutput "git" @("rev-parse", "--show-toplevel")
$repoRoot = [System.IO.Path]::GetFullPath($repoRoot)

if ([string]::IsNullOrWhiteSpace($WorktreeDir)) {
    $worktreesRoot = Join-Path (Split-Path -Parent $repoRoot) "worktrees"
    $WorktreeDir = Join-Path $worktreesRoot $Slug
}

$WorktreeDir = [System.IO.Path]::GetFullPath($WorktreeDir)
$currentDir = [System.IO.Path]::GetFullPath((Get-Location).Path)
if ($currentDir.StartsWith($WorktreeDir, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Estas dentro del worktree de la feature. Sali al checkout principal de develop antes de correr este script."
}

Confirm-PrMergedIntoBase -GitHubCliPath $ghPath -Branch $Branch -PrNumber $PrNumber -BaseBranch $baseBranch

Assert-CleanWorktree "antes de actualizar $baseBranch"

Write-Host "==> Actualizando referencias remotas..."
Invoke-Checked "git" @("fetch", "origin", $baseBranch, "--prune")

Write-Host "==> Cambiando al checkout principal de $baseBranch..."
Invoke-Checked "git" @("checkout", $baseBranch)
Assert-CleanWorktree "antes de sincronizar $baseBranch"

Write-Host "==> Sincronizando $baseBranch con origin/$baseBranch..."
Invoke-Checked "git" @("pull", "--ff-only", "origin", $baseBranch)
Assert-CleanWorktree "despues de sincronizar $baseBranch"

$roadmapPath = "ROADMAP.md"
Write-Host "==> Validando estado de '$Slug' en ROADMAP.md..."
$roadmap = Get-Content -LiteralPath $roadmapPath -Raw -Encoding UTF8
$closeState = Assert-RoadmapCanClose $roadmap $Slug

if ($closeState -eq "already-closed") {
    Write-Host "==> $Slug ya esta marcada exactamente una vez como [x]. Reejecucion segura, sin commit vacio."

    Write-Host "==> Verificando si el commit de cierre local ya llego a origin/$baseBranch..."
    Invoke-Checked "git" @("fetch", "origin", $baseBranch)
    $remoteRoadmapPreCheck = Get-CheckedOutput "git" @("show", "origin/$baseBranch`:ROADMAP.md")
    $remoteStatePreCheck = Get-RoadmapState $remoteRoadmapPreCheck $Slug

    if ($remoteStatePreCheck.Done -ne 1) {
        Write-Host "==> El commit de cierre existe en el checkout local pero no llego a origin/$baseBranch (corte de red u otra interrupcion tras el commit). Reintentando push pendiente..."
        Invoke-Checked "git" @("push", "origin", $baseBranch)
    }
}
else {
    Write-Host "==> Marcando '$Slug' como completada en ROADMAP.md..."
    $escapedSlug = [regex]::Escape($Slug)
    $readyRegex = [regex]::new("(?m)^- \[-\] ($escapedSlug(?=\s|$).*)$")
    $updatedRoadmap = $readyRegex.Replace($roadmap, '- [x] $1', 1)
    Set-Content -LiteralPath $roadmapPath -Value $updatedRoadmap -Encoding UTF8

    $postUpdateRoadmap = Get-Content -LiteralPath $roadmapPath -Raw -Encoding UTF8
    Assert-RoadmapClosedOnce $postUpdateRoadmap $Slug "despues de actualizar ROADMAP.md"

    Invoke-Checked "git" @("add", $roadmapPath)
    & git diff --cached --quiet
    if ($LASTEXITCODE -eq 0) {
        throw "La actualizacion de ROADMAP.md no produjo cambios staged. Se evita crear commit vacio."
    }

    Invoke-Checked "git" @("commit", "-m", "docs: cerrar $Slug en ROADMAP.md")

    Write-Host "==> Pusheando cierre a origin/$baseBranch..."
    Invoke-Checked "git" @("push", "origin", $baseBranch)
}

Write-Host "==> Verificando cierre publicado en origin/$baseBranch..."
Invoke-Checked "git" @("fetch", "origin", $baseBranch)
$remoteRoadmap = Get-CheckedOutput "git" @("show", "origin/$baseBranch`:ROADMAP.md")
Assert-RoadmapClosedOnce $remoteRoadmap $Slug "en origin/$baseBranch"

if ($SkipLocalCleanup) {
    Write-Host "==> Limpieza local omitida por -SkipLocalCleanup. GitHub Actions no puede borrar worktrees del equipo local."
}
else {
    Remove-LocalFeatureArtifacts $Branch $WorktreeDir
}

Assert-CleanWorktree "al finalizar"
Write-Host "==> Listo. $Slug cerrada y validada en origin/$baseBranch."
