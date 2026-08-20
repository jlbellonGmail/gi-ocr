param(
    [Parameter(Mandatory = $true)]
    [string] $Slug,

    [string] $Title = ""
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

# Get-GitHubCliPath y Get-PowerShellPath se reutilizan de feature-contract.ps1
# (dot-sourced arriba), en vez de redefinirlas aca (ver criterio 15 de
# runs/04-cierre-operativo-circuito-agentico/spec.md).

function Invoke-GhJson {
    param(
        [Parameter(Mandatory = $true)]
        [string] $GitHubCliPath,

        [Parameter(Mandatory = $true)]
        [string[]] $Arguments,

        [int[]] $AllowedExitCodes = @(0)
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
    $text = ($output | ForEach-Object { $_.ToString() }) -join "`n"

    if ($AllowedExitCodes -notcontains $exitCode) {
        throw "Command failed: gh $($Arguments -join ' ')`n$text"
    }

    return [pscustomobject]@{
        ExitCode = $exitCode
        StdOut = if ($exitCode -eq 0) { $text.Trim() } else { "" }
        StdErr = if ($exitCode -eq 0) { "" } else { $text.Trim() }
    }
}

function Get-ExistingPr {
    param(
        [Parameter(Mandatory = $true)]
        [string] $GitHubCliPath,

        [Parameter(Mandatory = $true)]
        [string] $Branch
    )

    $result = Invoke-GhJson -GitHubCliPath $GitHubCliPath -Arguments @(
        "pr", "view", $Branch,
        "--json", "number,url,baseRefName,state",
        "--jq", "."
    ) -AllowedExitCodes @(0, 1)

    if ($result.ExitCode -eq 0 -and -not [string]::IsNullOrWhiteSpace($result.StdOut)) {
        return ($result.StdOut | ConvertFrom-Json)
    }

    $notFound = $result.StdErr -match "no pull requests found|not found|Could not resolve to a PullRequest"
    if ($notFound -or [string]::IsNullOrWhiteSpace($result.StdErr)) {
        return $null
    }

    throw "Error real consultando PR existente con gh: $($result.StdErr)"
}

# Criterio 15: diagnostico generico de herramientas (git, gh binario +
# autenticacion, PowerShell, Python, .venv) de preflight.ps1, corrido al
# inicio, antes de cualquier verificacion propia de rama/commits y en
# particular antes de tocar ROADMAP.md. Deliberadamente NO reutiliza la
# matriz worktree/rama/ROADMAP de 'preflight.ps1 -Slug' (ver "Nota de
# alcance" del spec de 04-cierre-operativo-circuito-agentico): esa matriz
# depende de la rama remota, que en el camino feliz de este script todavia
# no existe entre marcar ROADMAP.md [-] y pushear.
Assert-ToolchainReady

if ([string]::IsNullOrWhiteSpace($Title)) {
    $Title = "Feature $Slug"
}

$baseBranch = if ([string]::IsNullOrWhiteSpace($env:BASE_BRANCH)) { "develop" } else { $env:BASE_BRANCH }
$currentBranch = Get-CheckedOutput "git" @("branch", "--show-current")
$contractTitle = $Title -replace "^Feature [0-9]{2}-", ""
$info = Get-FeatureInfo -Slug $Slug -Title $contractTitle

if ($currentBranch -eq $baseBranch -or $currentBranch -eq "main") {
    throw "Este script debe correr en una rama de feature, no en $currentBranch."
}

if (-not $currentBranch.StartsWith("feature/")) {
    throw "La rama actual debe empezar con 'feature/'. Rama actual: $currentBranch"
}

& git diff --quiet
$unstagedStatus = $LASTEXITCODE
& git diff --cached --quiet
$stagedStatus = $LASTEXITCODE
if ($unstagedStatus -ne 0 -or $stagedStatus -ne 0) {
    throw "Hay cambios sin commitear antes de marcar READY_FOR_PR. Commit de implementacion, tests y docs requerido."
}

$roadmapPath = "ROADMAP.md"
$roadmap = Get-Content -LiteralPath $roadmapPath -Raw -Encoding UTF8
$escapedSlug = [regex]::Escape($Slug)

if ($roadmap -match "(?m)^- \[x\] $escapedSlug\b") {
    throw "$Slug ya figura como [x]. No se puede marcar READY_FOR_PR despues del cierre."
}

if ($roadmap -match "(?m)^- \[-\] $escapedSlug\b") {
    Write-Host "==> $Slug ya esta en READY_FOR_PR."
}
else {
    $pendingPattern = "(?m)^- \[[ ~]\] ($escapedSlug.*)$"
    if ($roadmap -notmatch $pendingPattern) {
        throw "No encontre '$Slug' pendiente en ROADMAP.md."
    }

    Write-Host "==> Marcando '$Slug' como READY_FOR_PR en ROADMAP.md..."
    $pendingRegex = [regex]::new($pendingPattern)
    $updatedRoadmap = $pendingRegex.Replace($roadmap, '- [-] $1', 1)
    Set-Content -LiteralPath $roadmapPath -Value $updatedRoadmap -Encoding UTF8
    Invoke-Checked "git" @("add", $roadmapPath)
    Invoke-Checked "git" @("commit", "-m", "docs: marcar $Slug como ready for PR")
}

Assert-FeatureContract -Slug $Slug -Title $info.Title -RequireReadyRoadmap

Write-Host "==> Pusheando $currentBranch..."
Invoke-Checked "git" @("push", "-u", "origin", $currentBranch)

$ghPath = Get-GitHubCliPath
$powerShellPath = Get-PowerShellPath
$existingPr = Get-ExistingPr -GitHubCliPath $ghPath -Branch $currentBranch
if ($null -ne $existingPr) {
    if ($existingPr.baseRefName -ne $baseBranch) {
        throw "La PR existente #$($existingPr.number) apunta a '$($existingPr.baseRefName)', no a '$baseBranch'."
    }
    Write-Host "==> PR existente: #$($existingPr.number) $($existingPr.url)"
    & $powerShellPath -NoProfile -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot "start-local-reconciler.ps1") -Slug $Slug -Branch $currentBranch -WorktreeDir (Get-Location).Path
    exit 0
}

$bodyPath = Join-Path ([System.IO.Path]::GetTempPath()) ("pr-body-{0}.md" -f ([guid]::NewGuid()))
$body = @"
## Resumen

- Feature: $Slug
- Rama: $currentBranch
- Estado de roadmap: READY_FOR_PR, sin marcar [x]

## Evidencias

- Spec: $($info.RunDir)/spec.md
- Decision: $($info.Decision)
- Auditoria: $($info.RunDir)/audit-N.md
- QA: $($info.RunDir)/test-report-N.md
- Documentacion tecnica: $($info.TechnicalDoc)
- Documentacion de usuario: $($info.UserDoc)
- Indices: $($info.TechnicalIndex), $($info.UserIndex)

## Checklist

- [ ] CI verde en GitHub Actions
- [ ] Tests reportados en $($info.RunDir)/test-report-N.md
- [ ] Criterios de aceptacion cubiertos
- [ ] Decisiones documentadas en $($info.Decision)
- [ ] Indices de documentacion enlazan el servicio una sola vez
- [ ] Roadmap en READY_FOR_PR, no [x]

## Post-merge

El cierre remoto de ROADMAP.md lo ejecuta GitHub Actions con `scripts/close-feature.ps1`.
El reconciliador local iniciado por `ready-for-pr.ps1` solo limpia worktree/rama cuando
`origin/develop` ya contiene `[x] $Slug`.
"@

try {
    Set-Content -LiteralPath $bodyPath -Value $body -Encoding UTF8
    Write-Host "==> Creando PR hacia $baseBranch..."
    # 'gh pr create' no soporta --json/--jq en todas las versiones de gh
    # (a diferencia de 'gh pr view'/'gh pr list'). En su forma normal
    # (sin --json), 'gh pr create' imprime unicamente la URL de la PR
    # creada en stdout; se parsea el numero desde ahi. No hace falta una
    # consulta aparte: si 'gh pr create' no lanzo error, el --base que le
    # pasamos ya fue aceptado por GitHub.
    $createResult = Invoke-GhJson -GitHubCliPath $ghPath -Arguments @(
        "pr", "create",
        "--base", $baseBranch,
        "--head", $currentBranch,
        "--title", $Title,
        "--body-file", $bodyPath
    )
    $prUrl = $createResult.StdOut.Trim()
    if ($prUrl -notmatch "/pull/(\d+)\s*$") {
        throw "No se pudo interpretar la URL de la PR creada por 'gh pr create': '$prUrl'"
    }
    Write-Host "==> PR creada: #$($Matches[1]) $prUrl"
}
finally {
    if (Test-Path -LiteralPath $bodyPath) {
        Remove-Item -LiteralPath $bodyPath -Force
    }
}

& $powerShellPath -NoProfile -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot "start-local-reconciler.ps1") -Slug $Slug -Branch $currentBranch -WorktreeDir (Get-Location).Path
