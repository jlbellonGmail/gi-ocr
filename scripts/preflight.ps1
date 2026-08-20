param(
    [string] $Slug = ""
)

<#
    preflight.ps1 — diagnostico de solo lectura del circuito agentico
    (ver AGENTS.md y runs/03-cierre-operativo-circuito-agentico/spec.md).

    NUNCA muta el repositorio: no commitea, no pushea (salvo 'git fetch',
    de solo lectura), no crea ni borra ramas/worktrees. Toda accion
    destructiva o de recuperacion se delega a los scripts ya existentes
    (close-feature.ps1, start-local-reconciler.ps1, comandos git manuales
    que este mismo reporte sugiere).

    Modo generico (sin -Slug): diagnostica herramientas locales (git, gh,
    PowerShell, Python, .venv) y el estado de 'develop' (limpio,
    sincronizado con origin/develop).

    Modo por feature (-Slug <NN-slug>): ademas del modo generico, evalua
    la matriz de consistencia worktree/rama/ROADMAP.md descrita en el spec,
    el contrato de artefactos (Assert-FeatureContract en modo reporte), el
    estado del reconciliador local, y una foto de PR/CI cuando aplica.

    Exit code 0: no hay problemas BLOCKING (puede haber WARNING).
    Exit code 1: al menos un problema BLOCKING.
#>

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "feature-contract.ps1")

$report = New-Object System.Collections.Generic.List[object]

function Add-Report {
    param(
        [Parameter(Mandatory = $true)] [string] $Section,
        [Parameter(Mandatory = $true)] [string] $Severity,
        [Parameter(Mandatory = $true)] [string] $Message,
        [string] $Action = ""
    )
    $report.Add([pscustomobject]@{
        Section = $Section
        Severity = $Severity
        Message = $Message
        Action = $Action
    })
}

function Write-ReportLine {
    param([Parameter(Mandatory = $true)] $Item)
    $line = "[$($Item.Severity)] $($Item.Message)"
    if (-not [string]::IsNullOrWhiteSpace($Item.Action)) {
        $line += " Accion: $($Item.Action)"
    }
    Write-Host $line
}

function Get-WorktreeEntries {
    <#
        Parsea 'git worktree list --porcelain' en objetos { Path; Branch; Bare }.
        Nunca muta el repo (solo lectura).
    #>
    $raw = ((& git worktree list --porcelain) -join "`n")
    if ($LASTEXITCODE -ne 0) {
        return @()
    }

    $entries = New-Object System.Collections.Generic.List[object]
    $current = $null
    foreach ($line in ($raw -split "`r?`n")) {
        if ($line -match "^worktree (?<path>.+)$") {
            if ($null -ne $current) { $entries.Add($current) }
            $current = [pscustomobject]@{ Path = $Matches["path"]; Branch = $null; Bare = $false }
        }
        elseif ($line -match "^branch refs/heads/(?<branch>.+)$" -and $null -ne $current) {
            $current.Branch = $Matches["branch"]
        }
        elseif ($line -eq "bare" -and $null -ne $current) {
            $current.Bare = $true
        }
    }
    if ($null -ne $current) { $entries.Add($current) }

    return $entries.ToArray()
}

function Get-RoadmapMarkerForSlug {
    param(
        [Parameter(Mandatory = $true)] [string] $Content,
        [Parameter(Mandatory = $true)] [string] $Slug
    )
    $escapedSlug = [regex]::Escape($Slug)
    $suffix = "(?=\s|$)"
    $pending = [regex]::Matches($Content, "(?m)^- \[ \] $escapedSlug$suffix.*").Count
    $ready = [regex]::Matches($Content, "(?m)^- \[-\] $escapedSlug$suffix.*").Count
    $done = [regex]::Matches($Content, "(?m)^- \[x\] $escapedSlug$suffix.*").Count
    $total = $pending + $ready + $done
    if ($total -eq 0) { return "absent" }
    if ($total -gt 1) { return "duplicate" }
    if ($pending -eq 1) { return "pending" }
    if ($ready -eq 1) { return "ready" }
    return "done"
}

function Get-DevelopBranchDiagnostics {
    <#
        Criterio 3: estado de 'develop' (limpio, sincronizado). Solo lectura:
        usa 'git worktree list' para encontrar donde esta 'develop' checked
        out (sin cambiar de rama), y 'git fetch' (de solo lectura) para
        comparar con origin/develop.
    #>
    $rows = New-Object System.Collections.Generic.List[object]
    $baseBranch = "develop"

    $entries = Get-WorktreeEntries
    $developWorktree = $entries | Where-Object { $_.Branch -eq $baseBranch } | Select-Object -First 1

    if (-not $developWorktree) {
        $rows.Add([pscustomobject]@{ Severity = "WARNING"; Message = "Ningun worktree local tiene '$baseBranch' actualmente checked out."; Action = "Si esperabas trabajar sobre '$baseBranch', confirma que el checkout principal la tenga activa." })
    }
    else {
        $statusOutput = ((& git -C $developWorktree.Path status --porcelain) -join "`n")
        if ($LASTEXITCODE -eq 0 -and -not [string]::IsNullOrWhiteSpace($statusOutput)) {
            $rows.Add([pscustomobject]@{ Severity = "BLOCKING"; Message = "'$baseBranch' tiene cambios sin commitear en $($developWorktree.Path)."; Action = "Commitea o descarta los cambios en '$baseBranch' ($($developWorktree.Path)) antes de continuar. preflight.ps1 no modifica el repo automaticamente (ni git stash ni git checkout)." })
        }
        else {
            $rows.Add([pscustomobject]@{ Severity = "OK"; Message = "'$baseBranch' esta limpio en $($developWorktree.Path)."; Action = "" })
        }
    }

    $previousEap = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    $fetchOutput = ((& git fetch origin $baseBranch 2>&1) -join "`n")
    $fetchExit = $LASTEXITCODE
    $ErrorActionPreference = $previousEap

    if ($fetchExit -ne 0) {
        $rows.Add([pscustomobject]@{ Severity = "WARNING"; Message = "No se pudo contactar a origin para sincronizar '$baseBranch' (git fetch origin $baseBranch fallo)."; Action = "Verifica tu conexion de red y reintenta. Los demas chequeos que no requieren red siguen siendo validos." })
    }
    else {
        $localRefExit0 = $true
        $localRef = (& git rev-parse $baseBranch 2>$null)
        if ($LASTEXITCODE -ne 0) { $localRefExit0 = $false }
        $remoteRef = (& git rev-parse "origin/$baseBranch" 2>$null)
        $remoteRefExists = ($LASTEXITCODE -eq 0 -and -not [string]::IsNullOrWhiteSpace($remoteRef))

        if ($localRefExit0 -and $remoteRefExists) {
            $counts = ((& git rev-list --left-right --count "$baseBranch...origin/$baseBranch") -join " ").Trim()
            if ($LASTEXITCODE -eq 0 -and $counts -match "^(?<ahead>\d+)\s+(?<behind>\d+)$") {
                $ahead = [int]$Matches["ahead"]
                $behind = [int]$Matches["behind"]
                if ($behind -gt 0) {
                    $rows.Add([pscustomobject]@{ Severity = "WARNING"; Message = "'$baseBranch' local esta $behind commit(s) detras de origin/$baseBranch."; Action = "Sincroniza (desde el checkout que tiene '$baseBranch' activa): git pull --ff-only origin $baseBranch." })
                }
                if ($ahead -gt 0) {
                    $rows.Add([pscustomobject]@{ Severity = "WARNING"; Message = "'$baseBranch' local tiene $ahead commit(s) que origin/$baseBranch no tiene."; Action = "Verifica si falta pushear (por ejemplo, tras un cierre interrumpido: powershell -File scripts/close-feature.ps1 ...) o si hay commits locales inesperados." })
                }
                if ($ahead -eq 0 -and $behind -eq 0) {
                    $rows.Add([pscustomobject]@{ Severity = "OK"; Message = "'$baseBranch' esta sincronizado con origin/$baseBranch."; Action = "" })
                }
            }
        }
    }

    return $rows.ToArray()
}

function Get-PrCiSnapshotLine {
    param([Parameter(Mandatory = $true)] [string] $Branch)

    $ghPath = Find-GitHubCliPath
    if (-not $ghPath) {
        return "No se pudo consultar el estado de PR/CI: GitHub CLI (gh) no esta disponible."
    }

    $previousEap = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    $viewOutput = (& $ghPath "pr" "view" $Branch "--json" "number,url,state,mergeStateStatus" 2>&1)
    $viewExit = $LASTEXITCODE
    $ErrorActionPreference = $previousEap

    if ($viewExit -ne 0) {
        return "No existe PR para '$Branch' todavia (o no se pudo consultar con gh)."
    }

    try {
        $pr = ((($viewOutput | ForEach-Object { $_.ToString() }) -join "`n")) | ConvertFrom-Json
        return "PR #$($pr.number) ($($pr.url)): estado $($pr.state), mergeStateStatus $($pr.mergeStateStatus). Detalle de checks: scripts/wait-pr-ci.ps1 -Snapshot -PrRef $Branch"
    }
    catch {
        return "Se detecto una PR para '$Branch' pero no se pudo interpretar la respuesta de 'gh pr view'."
    }
}

function Get-ReconcilerDiagnostics {
    param([Parameter(Mandatory = $true)] [string] $Slug)

    $rows = New-Object System.Collections.Generic.List[object]
    $stateDir = Get-FeatureStateDir
    $safeName = $Slug -replace "[^A-Za-z0-9_.-]", "_"
    $lockPath = Join-Path $stateDir "$safeName.pid"
    $errorLogPath = Join-Path $stateDir "$safeName.err.log"

    if (-not (Test-Path -LiteralPath $lockPath -PathType Leaf)) {
        return $rows.ToArray()
    }

    $rawId = [string](Get-Content -LiteralPath $lockPath -Raw -ErrorAction SilentlyContinue)
    $existingId = 0
    $alive = $false
    if ([int]::TryParse($rawId.Trim(), [ref] $existingId)) {
        $existingProcess = Get-Process -Id $existingId -ErrorAction SilentlyContinue
        if ($existingProcess -and $existingProcess.ProcessName -match "^(cmd|powershell|pwsh)$") {
            $alive = $true
        }
    }

    if ($alive) {
        $rows.Add([pscustomobject]@{ Severity = "OK"; Message = "Reconciliador local activo para '$Slug' (PID $existingId)."; Action = "" })
        return $rows.ToArray()
    }

    $errorContent = ""
    if (Test-Path -LiteralPath $errorLogPath -PathType Leaf) {
        $errorContent = (Get-Content -LiteralPath $errorLogPath -Raw -ErrorAction SilentlyContinue)
    }

    if (-not [string]::IsNullOrWhiteSpace($errorContent)) {
        $rows.Add([pscustomobject]@{ Severity = "WARNING"; Message = "El reconciliador local de '$Slug' termino con error (lock obsoleto, PID $existingId ya no esta vivo)."; Action = "Revisa $errorLogPath y relanza si corresponde: powershell -File scripts/start-local-reconciler.ps1 -Slug $Slug." })
    }
    else {
        $rows.Add([pscustomobject]@{ Severity = "WARNING"; Message = "El reconciliador local de '$Slug' tiene un lock obsoleto (PID $existingId ya no esta vivo), sin contenido de error registrado."; Action = "Relanza si corresponde: powershell -File scripts/start-local-reconciler.ps1 -Slug $Slug." })
    }

    return $rows.ToArray()
}

function Get-FeatureMatrixDiagnostics {
    <#
        Evalua la matriz de consistencia worktree/rama/ROADMAP descrita en
        "Contexto" del spec de 03-cierre-operativo-circuito-agentico, como
        comando standalone (nunca invocada por ready-for-pr.ps1 sobre si
        mismo: ver criterio 15 y la "Nota de alcance" del spec).
    #>
    param([Parameter(Mandatory = $true)] [string] $Slug)

    $rows = New-Object System.Collections.Generic.List[object]
    function Add-Row($Severity, $Message, $Action = "") {
        $rows.Add([pscustomobject]@{ Severity = $Severity; Message = $Message; Action = $Action })
    }

    # Slug con formato invalido: reutiliza la misma validacion (y el mismo
    # mensaje) que ya produce Get-FeatureInfo, sin duplicarla.
    $info = Get-FeatureInfo -Slug $Slug

    $roadmapPath = "ROADMAP.md"
    if (-not (Test-Path -LiteralPath $roadmapPath -PathType Leaf)) {
        Add-Row "BLOCKING" "No existe ROADMAP.md en el directorio actual." "Corre preflight.ps1 -Slug desde la raiz de un checkout/worktree del repositorio."
        return $rows.ToArray()
    }

    $roadmapContent = Get-Content -LiteralPath $roadmapPath -Raw -Encoding UTF8
    $marker = Get-RoadmapMarkerForSlug -Content $roadmapContent -Slug $Slug

    if ($marker -eq "absent") {
        Add-Row "BLOCKING" "No hay ninguna entrada '$Slug' en ROADMAP.md (working tree actual)." "Verifica el slug, o agrega la entrada correspondiente en ROADMAP.md antes de continuar."
        return $rows.ToArray()
    }
    if ($marker -eq "duplicate") {
        Add-Row "BLOCKING" "Hay mas de una entrada '$Slug' en ROADMAP.md (working tree actual)." "Deja una sola entrada exacta para '$Slug' en ROADMAP.md."
        return $rows.ToArray()
    }

    $branchName = "feature/$Slug"
    $localBranchExists = -not [string]::IsNullOrWhiteSpace((((& git branch --list $branchName) -join "`n")).Trim())

    $worktreeEntries = Get-WorktreeEntries
    $matchingWorktrees = @($worktreeEntries | Where-Object { $_.Branch -eq $branchName })
    $worktreeExists = $false
    $worktreeOnConvention = $false
    foreach ($entry in $matchingWorktrees) {
        if (-not (Test-Path -LiteralPath $entry.Path)) {
            Add-Row "WARNING" "El worktree registrado para '$Slug' en 'git worktree list' ($($entry.Path)) ya no existe en disco (entrada administrativa huerfana)." "Corre 'git worktree prune' para limpiar la entrada."
            continue
        }
        $worktreeExists = $true
        $normalizedPath = ($entry.Path -replace "\\", "/").TrimEnd("/")
        if ($normalizedPath -match "/worktrees/$([regex]::Escape($Slug))$") {
            $worktreeOnConvention = $true
        }
    }
    if ($worktreeExists -and -not $worktreeOnConvention) {
        Add-Row "WARNING" "El worktree de '$Slug' existe pero no sigue la convencion '../worktrees/$Slug/' de AGENTS.md." "No bloquea, pero conviene migrarlo a la convencion estandar del repo."
    }

    $lsRemoteExit = -1
    $null = (& git ls-remote --exit-code origin "refs/heads/$branchName" 2>&1)
    $lsRemoteExit = $LASTEXITCODE
    $remoteBranchExists = $null
    if ($lsRemoteExit -eq 0) { $remoteBranchExists = $true }
    elseif ($lsRemoteExit -eq 2) { $remoteBranchExists = $false }
    else {
        Add-Row "WARNING" "No se pudo verificar contra origin si existe la rama remota '$branchName' (git ls-remote fallo, posible corte de red)." "Verifica conectividad de red y reintenta; los demas chequeos siguen siendo validos."
    }

    switch ($marker) {
        "pending" {
            if (-not $localBranchExists -and -not $worktreeExists) {
                Add-Row "OK" "Feature no iniciada: '$Slug' en [ ], sin rama ni worktree local." ""
            }
            else {
                Add-Row "OK" "Feature en progreso (normal): '$Slug' en [ ] con rama y/o worktree local." ""
            }
        }
        "ready" {
            if ($localBranchExists -and $worktreeExists -and $remoteBranchExists -eq $true) {
                Add-Row "OK" "'$Slug' en camino a PR/CI: rama y worktree locales, rama remota presente." ""
                Add-Row "OK" (Get-PrCiSnapshotLine -Branch $branchName) ""
            }
            elseif ($localBranchExists -and $worktreeExists -and $remoteBranchExists -eq $false) {
                Add-Row "BLOCKING" "'$Slug' esta en READY_FOR_PR ([-]) pero no existe la rama remota '$branchName'. ready-for-pr.ps1 exige push antes de marcar [-]; algo se hizo a mano o el push se perdio." "Corre: git push -u origin $branchName ; luego re-corre: powershell -File scripts/ready-for-pr.ps1 $Slug (es idempotente: no repite el commit de [-], solo reintenta push/PR)."
            }
            elseif (-not $localBranchExists -and -not $worktreeExists) {
                Add-Row "BLOCKING" "'$Slug' esta en READY_FOR_PR ([-]) pero no hay rama ni worktree local, y la feature todavia no esta cerrada remotamente." "Recrea el worktree: git worktree add ../worktrees/$Slug feature/$Slug (o desde origin si la rama solo existe remota) antes de continuar."
            }
            else {
                Add-Row "WARNING" "'$Slug' esta en READY_FOR_PR ([-]) con una combinacion no estandar de rama/worktree local (rama=$localBranchExists, worktree=$worktreeExists) y rama remota (existe=$remoteBranchExists)." "Revisa manualmente el estado de la rama/worktree antes de continuar."
            }
        }
        "done" {
            if (-not $localBranchExists -and -not $worktreeExists) {
                Add-Row "OK" "'$Slug' completada ([x]) y sin artefactos locales pendientes. Todo limpio." ""
            }
            elseif ($localBranchExists -and $worktreeExists) {
                Add-Row "WARNING" "'$Slug' ya esta [x] pero el worktree y la rama local siguen existiendo (el reconciliador no limpio: interrumpido o nunca se lanzo)." "Corre: powershell -File scripts/start-local-reconciler.ps1 -Slug $Slug (idempotente, no bloqueante) o, si ya confirmaste el merge, borra a mano (git worktree remove, git branch -d)."
            }
            elseif ($localBranchExists -and -not $worktreeExists) {
                Add-Row "WARNING" "'$Slug' ya esta [x] pero quedo una rama local huerfana ($branchName) sin worktree asociado." "Corre: git branch -d $branchName."
            }
            else {
                Add-Row "BLOCKING" "'$Slug' ya esta [x] y existe un worktree sin la rama local asociada (estado roto; no deberia ocurrir via 'git worktree remove' normal)." "Confirma que no haya cambios sin commitear en el worktree y corre: git worktree remove --force <ruta-del-worktree>."
            }
        }
    }

    foreach ($row in (Get-ReconcilerDiagnostics -Slug $Slug)) {
        $rows.Add($row)
    }

    return $rows.ToArray()
}

# ---------------------------------------------------------------------------
# Modo generico: diagnostico de herramientas + estado de 'develop'.
# ---------------------------------------------------------------------------

Write-Host "==> Diagnostico generico de herramientas"
$toolchainResults = Get-ToolchainDiagnostics
foreach ($item in $toolchainResults) {
    Add-Report "toolchain" $item.Severity $item.Message $item.Action
    Write-ReportLine $report[$report.Count - 1]
}

$gitAvailable = -not (@($toolchainResults | Where-Object { $_.Tool -eq "git" -and $_.Severity -eq "BLOCKING" }).Count -gt 0)

Write-Host ""
Write-Host "==> Estado de 'develop'"
if (-not $gitAvailable) {
    Add-Report "develop" "WARNING" "No se pudo evaluar el estado de 'develop': git no esta disponible (ver diagnostico de herramientas arriba)." "Instala git y volve a correr preflight.ps1."
    Write-ReportLine $report[$report.Count - 1]
}
else {
    foreach ($item in (Get-DevelopBranchDiagnostics)) {
        Add-Report "develop" $item.Severity $item.Message $item.Action
        Write-ReportLine $report[$report.Count - 1]
    }
}

# ---------------------------------------------------------------------------
# Modo por feature (-Slug): matriz worktree/rama/ROADMAP + contrato +
# reconciliador + snapshot de PR/CI.
# ---------------------------------------------------------------------------

if (-not [string]::IsNullOrWhiteSpace($Slug)) {
    Write-Host ""
    Write-Host "==> Matriz worktree/rama/ROADMAP para '$Slug'"
    if (-not $gitAvailable) {
        Add-Report "matrix:$Slug" "WARNING" "No se pudo evaluar la matriz worktree/rama/ROADMAP: git no esta disponible (ver diagnostico de herramientas arriba)." "Instala git y volve a correr preflight.ps1 -Slug $Slug."
        Write-ReportLine $report[$report.Count - 1]
    }
    else {
        foreach ($item in (Get-FeatureMatrixDiagnostics -Slug $Slug)) {
            Add-Report "matrix:$Slug" $item.Severity $item.Message $item.Action
            Write-ReportLine $report[$report.Count - 1]
        }
    }

    Write-Host ""
    Write-Host "==> Contrato de artefactos para '$Slug' (docs/decision/indices)"
    # El titulo real de la feature no vive en ningun lado canonico salvo
    # el propio contenido de decision.md ("# Decision: <slug> - <Titulo>").
    # Si existe, se reusa para no reportar falsos WARNING de "enlace no
    # exacto" cuando el titulo elegido difiere del que Get-FeatureInfo
    # derivaria por defecto a partir del slug (caso comun: titulos con
    # tildes/preposiciones, como esta misma feature).
    $decisionTitle = ""
    $decisionPathForTitle = "runs/$Slug/decision.md"
    if (Test-Path -LiteralPath $decisionPathForTitle -PathType Leaf) {
        $firstLine = (Get-Content -LiteralPath $decisionPathForTitle -TotalCount 1 -Encoding UTF8)
        if ($firstLine -match "^#\s*Decision:\s*$([regex]::Escape($Slug))\s*-\s*(?<title>.+)$") {
            $decisionTitle = $Matches["title"].Trim()
        }
    }
    if ([string]::IsNullOrWhiteSpace($decisionTitle)) {
        $contractStatus = Get-FeatureContractStatus -Slug $Slug
    }
    else {
        $contractStatus = Get-FeatureContractStatus -Slug $Slug -Title $decisionTitle
    }
    if ($contractStatus.IsComplete) {
        Add-Report "contract:$Slug" "OK" "El contrato de artefactos de '$Slug' esta completo (spec, audit, test-report, docs, decision, indices)." ""
        Write-ReportLine $report[$report.Count - 1]
    }
    else {
        foreach ($problem in $contractStatus.Problems) {
            Add-Report "contract:$Slug" "WARNING" $problem "Completa el artefacto faltante antes de considerar la feature lista para QA/PR."
            Write-ReportLine $report[$report.Count - 1]
        }
    }
}

# ---------------------------------------------------------------------------
# Resumen final.
# ---------------------------------------------------------------------------

$blockingCount = @($report | Where-Object { $_.Severity -eq "BLOCKING" }).Count
$warningCount = @($report | Where-Object { $_.Severity -eq "WARNING" }).Count

Write-Host ""
if ($blockingCount -eq 0) {
    Write-Host "PREFLIGHT: OK ($warningCount advertencia(s))"
    exit 0
}
else {
    Write-Host "PREFLIGHT: BLOCKING ($blockingCount problema(s) bloqueante(s), $warningCount advertencia(s))"
    exit 1
}
