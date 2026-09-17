param([string]$RepositoryRoot="", [string]$WorktreeDir="", [string]$Version="v2.0.0")
$ErrorActionPreference = "Stop"
function Git([string[]]$Arguments) {
  $gitCommand = Get-Command git -CommandType Application -ErrorAction Stop | Select-Object -First 1
  $out = & $gitCommand.Source @Arguments 2>&1
  if ($LASTEXITCODE) { throw "git fallo: $($Arguments -join ' ')" }
  return ($out -join [Environment]::NewLine).Trim()
}
try {
  $root = if ($RepositoryRoot) { [IO.Path]::GetFullPath($RepositoryRoot) } else { [IO.Path]::GetFullPath((Git @("rev-parse","--show-toplevel"))) }
  Push-Location $root
  try {
    $errors = [Collections.Generic.List[string]]::new()
    $warnings = [Collections.Generic.List[string]]::new()
    $roadmap = Get-Content "ROADMAP.md" -Raw -Encoding UTF8
    if ($Version -notmatch '^v[0-9]+\.[0-9]+\.[0-9]+$') { throw "Version invalida: $Version" }
    $v2 = Join-Path $root (Join-Path "runs" $Version)
    $dirs = @(Get-ChildItem $v2 -Directory -ErrorAction SilentlyContinue)
    $runT = @($dirs | Where-Object { $_.Name -match '^T\d{2}-[a-z0-9]+(?:-[a-z0-9]+)*$' })
    $roadT = @([regex]::Matches($roadmap,'(?m)^-\s+(?:\[[ x-]\]\s+)?(?<id>T\d{2}-[a-z0-9]+(?:-[a-z0-9]+)*)\b.*') | ForEach-Object { $_.Groups["id"].Value })
    if (($roadT | Group-Object | Where-Object Count -gt 1).Count) { [void]$errors.Add("identidad Txx duplicada en ROADMAP.md") }
    $head = Git @("rev-parse","HEAD")
    $runIds = @($runT | ForEach-Object Name)
    foreach ($id in $roadT) {
      if ($runIds -notcontains $id) { [void]$errors.Add("Txx '$id' cerrada o registrada sin run canónico") }
    }
    foreach ($dir in $runT) {
      $id = $dir.Name
      if ($roadT -notcontains $id) { [void]$errors.Add("run Txx '$id' existe pero falta en ROADMAP.md"); continue }
      $summary = Join-Path $dir.FullName "SUMMARY.md"
      if (-not (Test-Path $summary -PathType Leaf)) { [void]$errors.Add("SUMMARY.md faltante para $id") }
      else {
        $summaryText = Get-Content $summary -Raw -Encoding UTF8
        if ([string]::IsNullOrWhiteSpace($summaryText)) { [void]$errors.Add("SUMMARY.md vacio para $id") }
        $shortId = ([regex]::Match($id,'^T\d{2}')).Value
        if ($summaryText -notmatch "(?m)^#\s*$([regex]::Escape($shortId))\b") { [void]$errors.Add("identidad inconsistente: SUMMARY de $id no tiene encabezado $shortId") }
      }
    }
    foreach ($id in $roadT) {
      $line = ([regex]::Match($roadmap,"(?m)^-\s+(?:\[[ x-]\]\s+)?$([regex]::Escape($id))\b.*")).Value
      $dir = $runT | Where-Object Name -eq $id | Select-Object -First 1
      $done = $line -match '^- \[x\]'
      if ($done) {
        if (-not $dir) { continue }
        $summaryPath = Join-Path $dir.FullName "SUMMARY.md"
        if (-not (Test-Path $summaryPath -PathType Leaf)) { continue }
        $evidence = Get-Content $summaryPath -Raw -Encoding UTF8
        $pr = [regex]::Match($evidence,'(?im)^PR\s*:\s*.*#(?<n>\d+)\b')
        $merge = [regex]::Match($evidence,'(?im)^Merge\s*:\s*(?<sha>[0-9a-f]{7,40})\s*$')
        if (-not $pr.Success) { [void]$errors.Add("Txx '$id' cerrada sin PR verificable") }
        if (-not $merge.Success) { [void]$errors.Add("Txx '$id' cerrada sin Merge verificable") }
        if ($merge.Success) {
          $sha = $merge.Groups['sha'].Value
          try { [void](Git @("rev-parse","--verify","$sha^{commit}")) }
          catch { [void]$errors.Add("Txx '$id' referencia un merge inexistente: $sha") }
          try { [void](Git @("merge-base","--is-ancestor",$sha,$head)) }
          catch { [void]$errors.Add("Txx '$id' referencia un merge no alcanzable desde HEAD: $sha") }
        }
      }
    }
    $summaries = @(Get-ChildItem $v2 -Filter SUMMARY.md -File -Recurse -ErrorAction SilentlyContinue)
    foreach ($match in [regex]::Matches($roadmap,'(?m)^- \[x\] (?<id>[a-z0-9]+-[a-z0-9]+(?:-[a-z0-9]+)*)\b.*?Fase\s+(?<n>\d+)')) {
      $phaseId = $match.Groups["id"].Value
      $phaseSummary = Join-Path $v2 (Join-Path $phaseId "SUMMARY.md")
      if (-not (Test-Path $phaseSummary -PathType Leaf) -or [string]::IsNullOrWhiteSpace((Get-Content $phaseSummary -Raw -Encoding UTF8))) {
        $n = [int]$match.Groups["n"].Value
        [void]$errors.Add("ROADMAP F$("{0:D2}" -f $n) [x] sin SUMMARY de cierre: $phaseId")
      }
    }
    $status = Get-Content "STATUS.md" -Raw -Encoding UTF8
    $auto = [regex]::Match($status,'(?s)STATUS:AUTO:BEGIN.*?STATUS:AUTO:END')
    if ($auto.Success) {
      $recordedBranch = [regex]::Match($auto.Value,'(?m)^- Rama: (.+)$').Groups[1].Value.Trim()
      $recordedHead = [regex]::Match($auto.Value,'(?m)^- HEAD: \S+ \((?<sha>[0-9a-f]{40})\)').Groups["sha"].Value
      $branch = Git @("branch","--show-current"); $head = Git @("rev-parse","HEAD")
      if ($recordedBranch -ne $branch -or ($recordedHead -and $recordedHead -ne $head)) { [void]$warnings.Add("STATUS:AUTO stale: snapshot=$recordedBranch/$recordedHead actual=$branch/$head") }
    }
    if ($WorktreeDir) {
      $path = [IO.Path]::GetFullPath($WorktreeDir)
      if ((Git @("worktree","list","--porcelain")) -match "(?m)^worktree\s+$([regex]::Escape($path))$") { [void]$errors.Add("worktree Git activo: $path") }
      elseif (Test-Path $path) {
        if (@(Get-ChildItem $path -Force).Count) { [void]$errors.Add("cleanup incompleto: residual con archivos: $path") }
        else { [void]$warnings.Add("residual fisico vacio (posible lock Windows): $path") }
      }
    }
    $warnings | ForEach-Object { Write-Host "WARNING $_" }
    if ($errors.Count) { $errors | ForEach-Object { Write-Host "ERROR $_" }; exit 1 }
    Write-Host "PASS integridad global ROADMAP/runs/SUMMARY/Git/STATUS"
    exit 0
  } finally { Pop-Location }
} catch { Write-Host "ERROR Error de ejecucion: $($_.Exception.Message)"; exit 2 }
