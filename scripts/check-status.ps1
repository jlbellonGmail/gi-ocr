param([switch]$Json)
$ErrorActionPreference = "Stop"
function Invoke-Git([string[]]$A) { $o = & git @A 2>&1; if ($LASTEXITCODE) { throw "git command failed" }; (($o | ForEach-Object { $_.ToString() }) -join "`n").Trim() }
function Field([string]$B, [string]$N) { $m = [regex]::Match($B, "(?m)^- $([regex]::Escape($N)): (.*)$"); if (!$m.Success) { throw "Falta el campo $N" }; $m.Groups[1].Value.Trim() }
function Optional([string]$F, [string[]]$A) { if (!$F) { return [pscustomobject]@{Code=127;Text=""} }; $o=&$F @A 2>&1; [pscustomobject]@{Code=$LASTEXITCODE;Text=(($o|ForEach-Object {$_.ToString()})-join"`n").Trim()} }
try {
    $root=Invoke-Git @("rev-parse","--show-toplevel");$path=Join-Path $root "STATUS.md"
    if (!(Test-Path -LiteralPath $path -PathType Leaf)) { Write-Host "ERROR ERROR_REAL No existe STATUS.md";exit 1 }
    $content=Get-Content -Raw -Encoding UTF8 $path
    $begin=([regex]::Matches($content,[regex]::Escape("<!-- STATUS:AUTO:BEGIN -->"))).Count;$end=([regex]::Matches($content,[regex]::Escape("<!-- STATUS:AUTO:END -->"))).Count
    if($begin-ne 1-or$end-ne 1){Write-Host "ERROR INCONSISTENTE marcadores AUTO invalidos";exit 1}
    $match=[regex]::Match($content,'(?s)<!-- STATUS:AUTO:BEGIN -->.*?<!-- STATUS:AUTO:END -->');$block=$match.Value
    $branch=Invoke-Git @("branch","--show-current");if(!$branch){$branch="(detached)"};$head=Invoke-Git @("rev-parse","HEAD");$errors=@();$warnings=@()
    if((Field $block "Rama")-ne$branch){$errors+="INCONSISTENTE rama no coincide"}
    if((Field $block "HEAD")-notmatch[regex]::Escape($head)){$warnings+="STALE HEAD: snapshot regenerable"}
    $tree=if((Invoke-Git @("status","--porcelain"))){"dirty"}else{"clean"};if((Field $block "Working tree")-ne$tree){$warnings+="STALE working tree: snapshot regenerable"}
    $gh=if($env:GH_TOKEN){(Get-Command gh -ErrorAction SilentlyContinue).Source}else{$null}
    if(!$gh){$warnings+="TEMPORAL gh no disponible; PR/CI no verificables"}else{
        $pr=Optional $gh @("pr","list","--head",$branch,"--state","open","--json","number,headRefOid","--limit","1")
        if($pr.Code){$warnings+="TEMPORAL error consultando PR"}elseif($pr.Text-and$pr.Text-ne"[]"){$p=$pr.Text|ConvertFrom-Json;if((Field $block "PR activa")-notmatch[regex]::Escape([string]$p[0].number)){$warnings+="STALE PR: snapshot no refleja la PR abierta"}}
        $ci=Optional $gh @("run","list","--branch",$branch,"--limit","1","--json","headSha,status,conclusion")
        if($ci.Code){$warnings+="TEMPORAL error consultando CI"}elseif($ci.Text-and$ci.Text-ne"[]"){$x=$ci.Text|ConvertFrom-Json;if((Field $block "CI")-notmatch[regex]::Escape([string]$x[0].headSha)){$warnings+="STALE CI: corresponde a otro HEAD"}}
    }
    if($Json){[ordered]@{status=if($errors.Count){"INCONSISTENTE"}elseif($warnings.Count){"STALE"}else{"OK"};errors=$errors;warnings=$warnings;branch=$branch;head=$head}|ConvertTo-Json -Depth 5}
    else{$errors|ForEach-Object{Write-Host "ERROR $_"};$warnings|ForEach-Object{Write-Host "WARNING $_"};if($errors.Count){exit 1};Write-Host "PASS STATUS.md coherente (warnings regenerables)"}
    exit 0
}catch{Write-Host "ERROR ERROR_REAL $($_.Exception.Message)";exit 2}
