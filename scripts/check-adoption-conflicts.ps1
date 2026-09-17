<#
.SYNOPSIS
    Reporta, de solo lectura, que rutas conocidas de este template ya
    existen en un directorio destino, agrupadas por elemento del
    checklist de docs/tecnica/adopcion-proyecto-existente.md.

.DESCRIPTION
    Herramienta de apoyo OPCIONAL para quien adopta este circuito
    agentico sobre un proyecto existente. No hace diff de contenido, no
    distingue "identico al template" de "solo comparte el nombre", no
    usa historial de git y no resuelve ninguna colision automaticamente
    -- ver la seccion "Limites de scripts/check-adoption-conflicts.ps1"
    en docs/tecnica/adopcion-proyecto-existente.md para el detalle
    completo de estos limites, incluido el caso conocido y no resuelto
    de rutas con acceso denegado (Test-Path puede devolver $false ante
    un permiso denegado, reportandolo como "no existe").

.PARAMETER TargetPath
    Ruta al directorio destino a analizar. Por defecto, el directorio
    actual (".").

.EXAMPLE
    powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\check-adoption-conflicts.ps1 -TargetPath "C:\ruta\al\proyecto-destino"
#>
param(
    [string] $TargetPath = "."
)

$ErrorActionPreference = "Stop"

# Validacion de la ruta destino (caso borde de spec.md: ruta inexistente
# o que no es un directorio no debe reportar "sin colisiones").
if (-not (Test-Path -LiteralPath $TargetPath)) {
    Write-Error "La ruta destino '$TargetPath' no existe."
    exit 2
}

$resolvedTarget = (Resolve-Path -LiteralPath $TargetPath).ProviderPath
$targetItem = Get-Item -LiteralPath $resolvedTarget
if (-not $targetItem.PSIsContainer) {
    Write-Error "La ruta destino '$resolvedTarget' existe pero no es un directorio."
    exit 2
}

# Tabla interna de rutas conocidas por elemento del checklist, alineada
# manualmente con docs/tecnica/adopcion-proyecto-existente.md. Este
# script NO parsea ese Markdown: la lista se mantiene a mano (ver
# "Supuestos" de runs/v1.1.0/03-adopcion-proyecto-existente/spec.md).
$knownPaths = [ordered]@{
    ".agentic/" = @(
        ".agentic"
    )
    "scripts/" = @(
        "scripts/resolve-agentic-model.ps1",
        "scripts/sync-agentic-adapters.ps1",
        "scripts/update-doc-indexes.ps1",
        "scripts/wait-pr-ci.ps1",
        "scripts/start-work-unit.ps1",
        "scripts/workunit-lib.ps1",
        "scripts/local-feature-reconcile.ps1",
        "scripts/close-feature.ps1",
        "scripts/feature-contract.ps1",
        "scripts/complete-approved-pr.ps1",
        "scripts/ready-for-pr.ps1"
    )
    "runs/" = @(
        "runs"
    )
    "docs/tecnica/" = @(
        "docs/tecnica/index.md",
        "docs/tecnica/arquitectura.md",
        "docs/tecnica/circuito-agentico.md"
    )
    "docs/usuario/" = @(
        "docs/usuario/index.md",
        "docs/usuario/circuito-agentico.md"
    )
    "AGENTS.md" = @(
        "AGENTS.md"
    )
    ".github/workflows/ci.yml" = @(
        ".github/workflows/ci.yml"
    )
    ".github/workflows/docs.yml" = @(
        ".github/workflows/docs.yml"
    )
    ".github/workflows/post-hitl-merge-gate.yml" = @(
        ".github/workflows/post-hitl-merge-gate.yml"
    )
    ".github/workflows/post-merge-close-feature.yml" = @(
        ".github/workflows/post-merge-close-feature.yml"
    )
}

Write-Host "==> Analizando colisiones de rutas del template contra: $resolvedTarget"
Write-Host ""

$anyCollision = $false

foreach ($element in $knownPaths.Keys) {
    Write-Host "[$element]"
    foreach ($relativePath in $knownPaths[$element]) {
        $candidate = Join-Path -Path $resolvedTarget -ChildPath $relativePath
        # Solo lectura: Test-Path unicamente comprueba existencia, no lee
        # ni escribe contenido.
        $exists = Test-Path -LiteralPath $candidate
        if ($exists) {
            $anyCollision = $true
            Write-Host "  [COLISION] $relativePath existe"
        }
        else {
            Write-Host "  [ ok ]     $relativePath no existe"
        }
    }
    Write-Host ""
}

if ($anyCollision) {
    Write-Host "==> Resultado: se detectaron colisiones. Revisa docs/tecnica/adopcion-proyecto-existente.md para la estrategia de merge de cada elemento marcado [COLISION]."
    exit 1
}
else {
    Write-Host "==> Resultado: no se detectaron colisiones de rutas conocidas del template."
    exit 0
}
