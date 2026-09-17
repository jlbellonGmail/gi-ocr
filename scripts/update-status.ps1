param(
    [string]$RepositoryRoot = "",
    [switch]$Json,
    [string]$MachinePath = ""
)
$ErrorActionPreference = "Stop"
$NL = [Environment]::NewLine

function Invoke-Git([string[]]$Arguments) {
    $output = & git @Arguments 2>&1
    if ($LASTEXITCODE -ne 0) { throw "git command failed: $($Arguments -join ' ')" }
    return (($output | ForEach-Object { $_.ToString() }) -join $NL).Trim()
}
function Invoke-Optional([string]$File, [string[]]$Arguments) {
    if (-not $File) { return [pscustomobject]@{ Code = 127; Text = "" } }
    $psi = [Diagnostics.ProcessStartInfo]::new(); $psi.FileName = $File; $psi.UseShellExecute = $false; $psi.RedirectStandardOutput = $true; $psi.RedirectStandardError = $false
    foreach ($argument in $Arguments) { [void]$psi.ArgumentList.Add($argument) }
    $process = [Diagnostics.Process]::new(); $process.StartInfo = $psi
    if (-not $process.Start()) { return [pscustomobject]@{ Code = 127; Text = "" } }
    if (-not $process.WaitForExit(5000)) { try { $process.Kill() } catch {}; return [pscustomobject]@{ Code = 124; Text = "timeout" } }
    [pscustomobject]@{ Code = $process.ExitCode; Text = $process.StandardOutput.ReadToEnd().Trim() }
}
function Read-Gh([string]$Gh, [string[]]$Arguments) {
    $r = Invoke-Optional $Gh $Arguments
    if ($r.Code -ne 0 -or [string]::IsNullOrWhiteSpace($r.Text)) { return $null }
    try { return ($r.Text | ConvertFrom-Json) } catch { return $null }
}
function Get-Worktrees([string]$Raw) {
    $result = @(); $path = ""
    foreach ($line in ($Raw -split "`r?`n")) {
        if ($line.StartsWith("worktree ")) { $path = $line.Substring(9).Trim() }
        elseif ($line.StartsWith("branch ") -and $path) {
            $result += [ordered]@{ path = $path; branch = ($line.Substring(7).Trim() -replace '^refs/heads/', ''); gitActive = $true }
            $path = ""
        }
    }
    if ($path) { $result += [ordered]@{ path = $path; branch = "(detached)"; gitActive = $true } }
    return @($result)
}
function Replace-Auto([string]$Content, [string]$Block) {
    $pattern = '(?s)<!-- STATUS:AUTO:BEGIN -->.*?<!-- STATUS:AUTO:END -->'
    $count = [regex]::Matches($Content, $pattern).Count
    if ($count -gt 1) { throw "STATUS.md contiene bloques AUTO duplicados" }
    if ($count -eq 1) { return [regex]::Replace($Content, $pattern, [Text.RegularExpressions.MatchEvaluator]{ param($m) $Block }, 1) }
    return $Content.TrimEnd([char]13, [char]10) + $NL + $NL + $Block + $NL
}

try {
    $root = if ($RepositoryRoot) { [IO.Path]::GetFullPath($RepositoryRoot) } else { Invoke-Git @("rev-parse", "--show-toplevel") }
    Push-Location $root
    try {
        $branch = Invoke-Git @("branch", "--show-current"); if (-not $branch) { $branch = "(detached)" }
        $head = Invoke-Git @("rev-parse", "HEAD")
        $trees = Get-Worktrees (Invoke-Git @("worktree", "list", "--porcelain"))
        # GitHub queries are opt-in to an authenticated CLI session. This
        # prevents a broken credential helper from blocking local reentry.
        $gh = if ($env:GH_TOKEN) { (Get-Command gh -ErrorAction SilentlyContinue).Source } else { $null }
        $pr = Read-Gh $gh @("pr", "list", "--head", $branch, "--state", "open", "--json", "number,title,url,headRefOid,baseRefName", "--limit", "1")
        $ci = Read-Gh $gh @("run", "list", "--branch", $branch, "--limit", "1", "--json", "name,status,conclusion,headSha,url")
        $release = Read-Gh $gh @("release", "list", "--limit", "1", "--json", "tagName,name,publishedAt")
        $roadmap = if (Test-Path -LiteralPath "ROADMAP.md") { Get-Content -Raw -Encoding UTF8 ROADMAP.md } else { "" }
        $units = @()
        foreach ($tree in $trees) {
            $mode = ""; $slug = ""; $version = ""
            if ($tree.branch -match '^feature/(?:(?<version>v[0-9]+\.[0-9]+\.[0-9]+)-)?(?<slug>\d{2}-[a-z0-9-]+)$') { $mode = "Feature" }
            elseif ($tree.branch -match '^milestone/(?:(?<version>v[0-9]+\.[0-9]+\.[0-9]+)-)?(?<slug>[a-z0-9-]+)$') { $mode = "Milestone" }
            elseif ($tree.branch -match '^maintenance/(?:(?<version>v[0-9]+\.[0-9]+\.[0-9]+)-)?(?<slug>T[0-9]{2}-[a-z0-9-]+)(?:-fix)?$') { $mode = "Maintenance" }
            if ($mode) {
                $line = [regex]::Match($roadmap, "(?m)^- \[(?<state>[ x-])\] $([regex]::Escape($slug))\b")
                $state = if ($line.Success) { switch ($line.Groups.state.Value) { ' ' { 'pending' } '-' { 'ready' } 'x' { 'done' } } } else { 'unknown' }
                $lifecycle = if ($state -eq "done") { "CLOSED" } elseif ($state -eq "ready") { "PR_OPEN" } else { "ACTIVE" }
                $identityRelative = if($version){"runs/$version/$slug/work-unit.json"}else{"runs/$slug/work-unit.json"}
                $identityPath = Join-Path $tree.path $identityRelative
                $identity = if(Test-Path -LiteralPath $identityPath -PathType Leaf) { try { Get-Content $identityPath -Raw | ConvertFrom-Json } catch { $null } } else { $null }
                $units += [ordered]@{ unitId = $slug; canonicalSlug = if($identity){$identity.canonicalSlug}else{$slug}; mode = $mode; version = $version; branch = $tree.branch; worktree = $tree.path; state = $state; lifecycle = $lifecycle; baseCommit = if($identity){$identity.baseCommit}else{$null}; currentHead = if($identity){$identity.currentHead}else{$null}; pr = if($identity){$identity.pr}else{$null}; source = "git-worktree" }
            }
        }
        $workingTree = if (Invoke-Git @("status", "--porcelain")) { "dirty" } else { "clean" }
        $remoteResult = Invoke-Optional "git" @("remote", "get-url", "origin")
        $remote = if ($remoteResult.Code -eq 0 -and $remoteResult.Text) { $remoteResult.Text } else { "UNKNOWN / sin remoto" }
        $snapshot = [ordered]@{ schemaVersion = 1; generatedAt = [DateTime]::UtcNow.ToString('o'); version = 'v2.0.0'; branch = $branch; head = $head; remote = $remote; workingTree = $workingTree; worktrees = $trees; activeUnits = $units; pullRequest = $pr; ci = $ci; release = $release }
        $jsonText = $snapshot | ConvertTo-Json -Depth 12
        if ($MachinePath) { [IO.File]::WriteAllText([IO.Path]::GetFullPath($MachinePath), $jsonText + $NL, (New-Object Text.UTF8Encoding($false))) }
        if ($Json) { Write-Output $jsonText; exit 0 }
        $prText = if ($pr) { "#$($pr.number) $($pr.url)" } else { "UNKNOWN / sin PR abierta" }
        $ciText = if ($ci) { "$($ci.conclusion) @ $($ci.headSha)" } else { "UNKNOWN / sin CI verificable" }
        $unitText = if ($units.Count) { ($units | ForEach-Object { "$($_.slug)=$($_.state) [$($_.branch)]" }) -join '; ' } else { 'ninguna' }
        $block = @("<!-- STATUS:AUTO:BEGIN -->", "", "## Estado verificado automáticamente", "", "- Actualizado: $([DateTime]::UtcNow.ToString('yyyy-MM-ddTHH:mm:ssZ'))", "- Versión: v2.0.0", "- Rama: $branch", "- HEAD: $head", "- Remoto: $($snapshot.remote)", "- Working tree: $workingTree", "- Worktrees: $($trees.Count)", "- Worktrees Git: $($trees.Count)", "- Unidades activas: $unitText", "- PR activa: $prText", "- CI: $ciText", "- CI vigente: $ciText", "- Última release: $(if ($release) { $release.tagName } else { 'UNKNOWN / no disponible' })", "", "<!-- STATUS:AUTO:END -->") -join $NL
        $status = Join-Path $root "STATUS.md"
        $content = [IO.File]::ReadAllText($status, [Text.Encoding]::UTF8)
        [IO.File]::WriteAllText($status, (Replace-Auto $content $block), (New-Object Text.UTF8Encoding($false)))
        # La escritura del propio STATUS cambia el working tree; registrar el
        # estado final evita que una consulta deje un snapshot autocontradictorio.
        $finalTree = if (Invoke-Git @("status", "--porcelain")) { "dirty" } else { "clean" }
        if ($finalTree -ne $workingTree) {
            $updated = [IO.File]::ReadAllText($status, [Text.Encoding]::UTF8) -replace "- Working tree: $workingTree", "- Working tree: $finalTree"
            [IO.File]::WriteAllText($status, $updated, (New-Object Text.UTF8Encoding($false)))
        }
    } finally { Pop-Location }
    Write-Host "PASS STATUS.md actualizado"; exit 0
} catch { Write-Host ("ERROR " + $_.Exception.Message); exit 2 }
