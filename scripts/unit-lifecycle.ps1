<#
.SYNOPSIS
  Inspecciona y reconcilia una work unit sin depender de nombres auxiliares.
#>
param(
    [Parameter(Mandatory=$true)][ValidateSet('inspect','reconcile','cleanup','retry-cleanup')][string]$Action,
    [Parameter(Mandatory=$true)][string]$Slug,
    [ValidateSet('Feature','Milestone','Maintenance')][string]$Mode='Feature',
    [string]$Version='', [string]$Branch='', [string]$WorktreeDir='',
    [string]$BaseCommit='', [int]$PrNumber=0, [switch]$Json
)
$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot 'workunit-lib.ps1')
function GitOut([string[]]$Arguments) {
    $output=& git @Arguments 2>&1
    if($LASTEXITCODE){throw "git fallo: $($Arguments -join ' ')"}
    ($output -join [Environment]::NewLine).Trim()
}
function Emit-Result($Value) {
    if($Json){$Value|ConvertTo-Json -Depth 12}else{Write-Host "$($Value.lifecycle): $($Value.message)"}
}
if(!$Branch){
    $prefix=if($Version){"$Version-"}else{''}
    $Branch=switch($Mode){'Milestone'{"milestone/$prefix$Slug"};'Maintenance'{"maintenance/$prefix$Slug"};default{"feature/$prefix$Slug"}}
}
if(!$WorktreeDir){$WorktreeDir=(Get-Location).Path}
if($Action -in @('cleanup','retry-cleanup')){
    & (Join-Path $PSScriptRoot 'cleanup-work-unit.ps1') -Slug $Slug -Mode $Mode -Version $Version -Branch $Branch -WorktreeDir $WorktreeDir -Retry:($Action -eq 'retry-cleanup') -Json:$Json
    exit $LASTEXITCODE
}
$head=GitOut @('rev-parse','HEAD');$origin=GitOut @('rev-parse','origin/develop')
if(!$BaseCommit){$BaseCommit=$head}
$identity=Get-WorkUnitIdentity -Slug $Slug -Mode $Mode -Version $Version -Branch $Branch -Worktree $WorktreeDir -BaseCommit $BaseCommit -HeadCommit $head -PrNumber $PrNumber
if($Action -eq 'inspect'){
    & git merge-base --is-ancestor $BaseCommit origin/develop *> $null
    $identity.lifecycle=if($LASTEXITCODE -eq 0 -and $head -ne $BaseCommit){'RECONCILE_REQUIRED'}else{'ACTIVE'}
    $identity.originDevelop=$origin
    $identity.message=if($identity.lifecycle -eq 'ACTIVE'){'unidad aislada y registrada'}else{'develop avanzo desde la base original'}
    Emit-Result $identity;exit 0
}
GitOut @('fetch','origin','develop','--prune')|Out-Null
$origin=GitOut @('rev-parse','origin/develop')
& git merge-base --is-ancestor origin/develop HEAD *> $null;$needsMerge=($LASTEXITCODE -ne 0)
if($needsMerge){
    & git merge --no-edit origin/develop 2>&1|Write-Host
    if($LASTEXITCODE){
        & git merge --abort *> $null
        $identity.lifecycle='BLOCKED';$identity.conflict='SEMANTIC';$identity.message='reconciliacion requiere decision humana'
        Emit-Result $identity;exit 3
    }
    $identity.staleEvidence=@('ci','review','scoped-authorization');$identity.revalidated=$false
}
$identity.currentHead=GitOut @('rev-parse','HEAD');$identity.originDevelop=$origin;$identity.lifecycle='ACTIVE'
$identity.message=if($needsMerge){'reconciliada; evidencia anterior stale'}else{'ya estaba basada en develop actual'}
$root=GitOut @('rev-parse','--show-toplevel');$run=Join-Path (Join-Path (Join-Path $root 'runs') $Version) $Slug
New-Item -ItemType Directory -Force $run|Out-Null
[IO.File]::WriteAllText((Join-Path $run 'work-unit.json'),($identity|ConvertTo-Json -Depth 12)+[Environment]::NewLine,(New-Object Text.UTF8Encoding($false)))
Emit-Result $identity
