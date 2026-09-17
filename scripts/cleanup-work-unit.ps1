param(
 [Parameter(Mandatory=$true)][string]$Slug,
 [ValidateSet('Feature','Milestone','Maintenance')][string]$Mode='Feature',
 [string]$Version='', [string]$Branch='', [string]$WorktreeDir='', [switch]$Retry,[switch]$Json
)
$ErrorActionPreference='Stop';. (Join-Path $PSScriptRoot 'workunit-lib.ps1')
function G([string[]]$A){$o=& git @A 2>&1;if($LASTEXITCODE){throw "git fallo: $($A -join ' ')"};($o -join [Environment]::NewLine).Trim()}
if(!$Branch){$p=if($Version){"$Version-"}else{''};$Branch=switch($Mode){'Milestone'{"milestone/$p$Slug"};'Maintenance'{"maintenance/$p$Slug"};default{"feature/$p$Slug"}}}
if(!$WorktreeDir){$r=G @('rev-parse','--show-toplevel');$WorktreeDir=Join-Path (Join-Path (Split-Path -Parent $r) 'worktrees') ("$(if($Version){"$Version-"})$Slug")}
$path=[IO.Path]::GetFullPath($WorktreeDir);$registered=(G @('worktree','list','--porcelain')) -match [regex]::Escape($path)
if($registered){try{G @('worktree','remove',$path)|Out-Null}catch{$result=[ordered]@{lifecycle='RESIDUAL_WINDOWS';cleanup='ERROR';classification='WORKTREE_REGISTERED';path=$path;message=$_.Exception.Message};if($Json){$result|ConvertTo-Json}else{Write-Host ($result|ConvertTo-Json)};exit 2}}
G @('worktree','prune')|Out-Null;$classification='A_NOT_EXISTS';$ok=$true
if(Test-Path -LiteralPath $path){$entries=@(Get-ChildItem -LiteralPath $path -Force -ErrorAction SilentlyContinue);if($entries.Count -eq 0){$classification='B_RESIDUAL_WINDOWS_EMPTY';$ok=$false}else{$classification='C_RESIDUAL_WINDOWS_CONTENT';$ok=$false}}
& git show-ref --verify --quiet ('refs/heads/'+$Branch);if($LASTEXITCODE -eq 0){& git branch -d $Branch|Out-Null}
$result=[ordered]@{lifecycle=if($ok){'CLOSED'}else{'RESIDUAL_WINDOWS'};cleanup=if($ok){'CLEAN'}else{'DEFERRED'};classification=$classification;path=$path;retry=$Retry;message=if($ok){'unidad cerrada y artefactos limpiados'}else{'residuo registrado; no se borra contenido'}}
if($Json){$result|ConvertTo-Json}else{Write-Host ($result|ConvertTo-Json)};if(!$ok){exit 4}
