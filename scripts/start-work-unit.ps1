param(
    [ValidateSet("Feature", "Milestone", "Maintenance")]
    [string] $Mode = "Feature",

    [Parameter(Mandatory = $true)]
    [string] $Slug,

    [string[]] $Items = @(),

    [string] $Title = "",

    [string] $Version = ""
)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "workunit-lib.ps1")
. (Join-Path $PSScriptRoot "feature-contract.ps1")

# -Items acepta tanto "-Items a b c" (varios valores) como
# "-Items a,b,c" (un solo string con comas, comun al invocar el .ps1
# como proceso externo, donde el shell no separa por coma).
$Items = @($Items | ForEach-Object { $_ -split "," } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | ForEach-Object { $_.Trim() })

if ($Mode -eq "Feature" -and $Items.Count -gt 0) {
    throw "-Items no aplica en Mode=Feature: el unico item ES el -Slug."
}

if ($Mode -eq "Milestone" -and $Items.Count -eq 0) {
    throw "-Items es obligatorio en Mode=Milestone (lista de items de ROADMAP.md a agrupar)."
}

$itemSlugs = if ($Mode -eq "Milestone") { @($Items) } else { @($Slug) }

# Duplicados dentro de la lista pedida.
$duplicates = @($itemSlugs | Group-Object | Where-Object { $_.Count -gt 1 } | ForEach-Object { $_.Name })
if ($duplicates.Count -gt 0) {
    throw "Items duplicados en -Items: $($duplicates -join ', ')."
}

$repoRoot = Get-RepositoryRoot
$currentDir = [System.IO.Path]::GetFullPath((Get-Location).Path)
$mainRoot = Split-Path -Parent (Get-GitCommonDir)
$mainRootFull = [System.IO.Path]::GetFullPath($mainRoot)

# Debe correr desde el checkout principal, no desde un worktree de feature
# o milestone existente (mismo patron de deteccion que close-feature.ps1 /
# local-feature-reconcile.ps1: si el cwd no es el checkout principal, es
# un worktree).
if (-not [string]::Equals($currentDir, $mainRootFull, [System.StringComparison]::OrdinalIgnoreCase) `
        -and -not [string]::Equals([System.IO.Path]::GetFullPath($repoRoot), $mainRootFull, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Este script debe correrse desde el checkout principal de develop, no desde un worktree. Directorio actual: $currentDir"
}

$baseBranch = "develop"

Write-Host "==> Sincronizando referencias de $baseBranch..."
Invoke-Checked "git" @("fetch", "origin", $baseBranch, "--prune")

$status = Get-CheckedOutput "git" @("status", "--short")
if (-not [string]::IsNullOrWhiteSpace($status)) {
    throw "Hay cambios locales sin commitear en el checkout principal. No se continua.`n$status"
}

$currentBranch = Get-CheckedOutput "git" @("branch", "--show-current")
if ($currentBranch -ne $baseBranch) {
    Invoke-Checked "git" @("checkout", $baseBranch)
}

$statusAfterCheckout = Get-CheckedOutput "git" @("status", "--short")
if (-not [string]::IsNullOrWhiteSpace($statusAfterCheckout)) {
    throw "Hay cambios locales sin commitear en $baseBranch despues de cambiar de rama. No se continua.`n$statusAfterCheckout"
}

$localHead = Get-CheckedOutput "git" @("rev-parse", $baseBranch)
$remoteHead = Get-CheckedOutput "git" @("rev-parse", "origin/$baseBranch")
if ($localHead -ne $remoteHead) {
    Write-Host "==> $baseBranch local desactualizado respecto de origin/$baseBranch. Sincronizando..."
    Invoke-Checked "git" @("pull", "--ff-only", "origin", $baseBranch)
}

$roadmapPath = "ROADMAP.md"
$roadmap = Get-Content -LiteralPath $roadmapPath -Raw -Encoding UTF8

$itemSlugRegex = "^(?:[0-9]{2}-)?[a-z0-9]+(?:-[a-z0-9]+)*$"
foreach ($item in $itemSlugs) {
    if ($item -notmatch $itemSlugRegex) {
        throw "Slug de item invalido '$item'."
    }

    $state = Get-RoadmapItemStateName -Content $roadmap -ItemSlug $item
    if ($state -eq "Missing") {
        throw "El item '$item' no existe en ROADMAP.md."
    }
    if ($state -eq "Ambiguous") {
        throw "El item '$item' aparece mas de una vez en ROADMAP.md."
    }
    if ($state -ne "Pending") {
        throw "El item '$item' no esta pendiente en ROADMAP.md (estado actual: $state)."
    }
}

# Deteccion de reclamos existentes: otro work unit abierto (manifest bajo
# runs/milestone-*/work-unit.json) que ya incluya alguno de estos items, o
# una rama/worktree feature/<item> ya viva para alguno de ellos. Un
# manifest de milestone vive commiteado en SU PROPIA rama/worktree (no en
# develop), asi que hay que recorrer todos los worktrees existentes, no
# solo el checkout principal.
$worktreeListRaw = Get-CheckedOutput "git" @("worktree", "list", "--porcelain")
$worktreePaths = @($worktreeListRaw -split "`n" | Where-Object { $_ -like "worktree *" } | ForEach-Object { $_.Substring("worktree ".Length).Trim() })

$existingManifests = @()
foreach ($worktreePath in $worktreePaths) {
    $candidateRunsDir = Join-Path $worktreePath "runs"
    if (-not (Test-Path -LiteralPath $candidateRunsDir -PathType Container)) {
        continue
    }
    $existingManifests += @(Get-ChildItem -LiteralPath $candidateRunsDir -Directory -Filter "milestone-*" -ErrorAction SilentlyContinue |
        ForEach-Object { Join-Path $_.FullName "work-unit.json" } |
        Where-Object { Test-Path -LiteralPath $_ -PathType Leaf })
}

foreach ($manifestPath in $existingManifests) {
    $existingManifest = Read-WorkUnitManifest -Path $manifestPath
    foreach ($item in $itemSlugs) {
        if ($existingManifest.Items -contains $item) {
            throw "El item '$item' ya esta reclamado por el work unit 'milestone/$($existingManifest.Slug)' ($manifestPath)."
        }
    }
}

$existingBranches = (Get-CheckedOutput "git" @("branch", "--list", "--format=%(refname:short)")) -split "`n" | Where-Object { $_ }
foreach ($item in $itemSlugs) {
    $itemBranch = "feature/$item"
    if ($existingBranches -contains $itemBranch) {
        throw "Ya existe una rama local para el item '$item': $itemBranch. Ya esta reclamado por otro work unit."
    }
}

$versionPrefix = if ([string]::IsNullOrWhiteSpace($Version)) { "" } else { "$Version-" }
$branch = if ($Mode -eq "Milestone") { "milestone/$versionPrefix$Slug" } elseif ($Mode -eq "Maintenance") { "maintenance/$versionPrefix$Slug" } else { "feature/$versionPrefix$Slug" }
$worktreesRoot = Join-Path (Split-Path -Parent $repoRoot) "worktrees"
$worktreeName = "$versionPrefix$Slug".TrimEnd('-')
$worktreeDir = Join-Path $worktreesRoot $worktreeName

if (Test-Path -LiteralPath $worktreeDir) {
    throw "Ya existe un directorio de worktree para '$Slug': $worktreeDir."
}

if ($existingBranches -contains $branch) {
    throw "Ya existe una rama local '$branch'. Elegi otro slug o limpia la rama existente."
}

Write-Host "==> Creando rama '$branch' y worktree en '$worktreeDir'..."
Invoke-Checked "git" @("worktree", "add", "-b", $branch, $worktreeDir, $baseBranch)

if ($Mode -eq "Milestone") {
    $runRelative = if ([string]::IsNullOrWhiteSpace($Version)) { "runs/milestone-$Slug" } else { "runs/$Version/milestone-$Slug" }
    $runDir = Join-Path $worktreeDir $runRelative
    New-Item -ItemType Directory -Path $runDir -Force | Out-Null
    $manifestPath = Join-Path $runDir "work-unit.json"

    Push-Location $worktreeDir
    try {
        $manifestRelative = if ([string]::IsNullOrWhiteSpace($Version)) { "runs/milestone-$Slug/work-unit.json" } else { "runs/$Version/milestone-$Slug/work-unit.json" }
        Write-WorkUnitManifest -Path $manifestRelative -Mode "milestone" -Slug $Slug -Items $itemSlugs
        Invoke-Checked "git" @("add", $manifestRelative)
        Invoke-Checked "git" @("commit", "-m", "chore: iniciar milestone $Slug con items $($itemSlugs -join ', ')")
    }
    finally {
        Pop-Location
    }
}
else {
    $featureRunRelative = if ([string]::IsNullOrWhiteSpace($Version)) { "runs/$Slug" } else { "runs/$Version/$Slug" }
    New-Item -ItemType Directory -Path (Join-Path $worktreeDir $featureRunRelative) -Force | Out-Null
}

Write-Host ""
Write-Host "==> Work unit '$Slug' ($Mode) listo."
Write-Host "==> Rama: $branch"
Write-Host "==> Worktree: $worktreeDir"
if ($Mode -eq "Milestone") {
    Write-Host "==> Items agrupados: $($itemSlugs -join ', ')"
    Write-Host "==> Manifest: $(if ([string]::IsNullOrWhiteSpace($Version)) { "runs/milestone-$Slug/work-unit.json" } else { "runs/$Version/milestone-$Slug/work-unit.json" })"
}
Write-Host ""
Write-Host "==> Proximo paso: correr analyst-agent en sesion nueva, dentro de $worktreeDir,"
Write-Host "    leyendo AGENTS.md (seccion Modo MILESTONE si $Mode -eq 'Milestone') para producir runs/$(
    if ($Mode -eq 'Milestone') { "milestone-$Slug" } else { if ([string]::IsNullOrWhiteSpace($Version)) { $Slug } else { "$Version/$Slug" } }
)/spec.md."
