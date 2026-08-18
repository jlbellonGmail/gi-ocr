param(
    [Parameter(Mandatory = $true)]
    [string] $Slug,

    [Parameter(Mandatory = $true)]
    [string] $Title
)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "feature-contract.ps1")

$info = Get-FeatureInfo -Slug $Slug -Title $Title
$changed = $false

if (Update-DocsIndex -IndexPath $info.TechnicalIndex -TargetPath $info.TechnicalDoc -Title $info.Title) {
    Write-Host "==> Agregado enlace tecnico: $($info.TechnicalIndex) -> $($info.DocSlug).md"
    $changed = $true
}

if (Update-DocsIndex -IndexPath $info.UserIndex -TargetPath $info.UserDoc -Title $info.Title) {
    Write-Host "==> Agregado enlace de usuario: $($info.UserIndex) -> $($info.DocSlug).md"
    $changed = $true
}

Assert-IndexLink -IndexPath $info.TechnicalIndex -TargetPath $info.TechnicalDoc -Title $info.Title
Assert-IndexLink -IndexPath $info.UserIndex -TargetPath $info.UserDoc -Title $info.Title

if (-not $changed) {
    Write-Host "==> Indices ya estaban completos para $Slug."
}
