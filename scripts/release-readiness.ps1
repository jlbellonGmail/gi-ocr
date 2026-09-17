[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string] $Version,
    [string] $CandidateBranch = "develop",
    [string] $TargetBranch = "main",
    [string] $RepositoryRoot = "",
    [switch] $DryRun
)

$ErrorActionPreference = "Stop"

function Invoke-Git([string[]] $Arguments) {
    $value = & git @Arguments 2>&1
    if ($LASTEXITCODE -ne 0) { throw "git fallo: git $($Arguments -join ' ')" }
    return (($value | ForEach-Object { $_.ToString() }) -join "`n").Trim()
}

function Invoke-Optional([string] $File, [string[]] $Arguments) {
    $value = & $File @Arguments 2>&1
    [pscustomobject]@{ Code = $LASTEXITCODE; Text = (($value | ForEach-Object { $_.ToString() }) -join "`n").Trim() }
}

function Assert-Condition([bool] $Condition, [string] $Message) {
    if (-not $Condition) { throw $Message }
}

try {
    $root = if ($RepositoryRoot) { [IO.Path]::GetFullPath($RepositoryRoot) } else { Invoke-Git @("rev-parse", "--show-toplevel") }
    Push-Location $root
    try {
        Assert-Condition ($Version -match '^v(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$') "Version invalida: '$Version'. Se exige SemVer vMAJOR.MINOR.PATCH."
        $roadmapPath = Join-Path $root "ROADMAP.md"
        Assert-Condition (Test-Path -LiteralPath $roadmapPath -PathType Leaf) "ROADMAP.md inexistente."
        $roadmap = Get-Content -LiteralPath $roadmapPath -Raw -Encoding UTF8
        $required = @("18-status-observabilidad", "19-unidades-paralelizacion", "20-releases-evolucion", "21-validacion-integral-v2", "22-auditoria-release-v2")
        foreach ($item in $required) {
            $match = [regex]::Match($roadmap, "(?m)^- \[(?<state>[ x-])\] $([regex]::Escape($item))\b")
            Assert-Condition $match.Success "ROADMAP incompleto: falta '$item'."
            Assert-Condition ($match.Groups["state"].Value -eq "x") "ROADMAP incompleto: '$item' no esta cerrado."
        }

    Assert-Condition ($CandidateBranch -notin @("", "main")) "La candidata debe provenir de una rama de integracion distinta de main."
    $current = Invoke-Git @("branch", "--show-current")
        Assert-Condition ($current -eq $CandidateBranch) "Rama incorrecta: se esperaba '$CandidateBranch' y se obtuvo '$current'."
        $dirty = Invoke-Git @("status", "--porcelain")
        Assert-Condition ([string]::IsNullOrWhiteSpace($dirty)) "Working tree dirty: la release exige arbol limpio."
        $candidateSha = Invoke-Git @("rev-parse", "$CandidateBranch^{commit}")
        $developSha = Invoke-Git @("rev-parse", "develop^{commit}")
        Assert-Condition ($candidateSha -eq $developSha) "La candidata no coincide con el HEAD local de develop."

        $run = Join-Path $root "runs\$Version\22-auditoria-release-v2"
        Assert-Condition (Test-Path -LiteralPath $run -PathType Container) "Falta la auditoria de release para $Version (F17)."
        foreach ($file in @("SUMMARY.md", "audit-1.md", "test-report-1.md", "code-review-1.md")) {
            Assert-Condition (Test-Path -LiteralPath (Join-Path $run $file) -PathType Leaf) "Falta evidencia de release: $run\$file."
        }
        $audit = Get-Content (Join-Path $run "audit-1.md") -Raw
        Assert-Condition ($audit -match '(?m)^status:\s*approved\s*$') "La auditoria de release no esta aprobada."

        $integrity = Join-Path $PSScriptRoot "check-integrity.ps1"
        $integrityResult = Invoke-Optional "pwsh" @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $integrity, "-RepositoryRoot", $root)
        Assert-Condition ($integrityResult.Code -eq 0) "Integridad FAIL: $($integrityResult.Text)"

        $gh = Get-Command gh -ErrorAction SilentlyContinue
        Assert-Condition ($null -ne $gh) "No se puede verificar CI remoto: gh no esta disponible."
        $ci = Invoke-Optional $gh.Source @("run", "list", "--branch", $CandidateBranch, "--limit", "50", "--json", "headSha,status,conclusion,workflowName,createdAt")
        Assert-Condition ($ci.Code -eq 0) "No se pudo consultar CI: $($ci.Text)"
        # Una misma revision puede tener una ejecucion push fallida y otra
        # pull_request exitosa (por carreras/reintentos del proveedor). La
        # evidencia vigente es la ultima ejecucion de cada workflow.
        $runs = @($ci.Text | ConvertFrom-Json | Where-Object { $_.headSha -eq $candidateSha } | Sort-Object createdAt -Descending)
        Assert-Condition ($runs.Count -gt 0) "CI no encontrado para el commit candidato $candidateSha."
        $latestRuns = @($runs | Where-Object { $_.workflowName -eq "CI" } | Group-Object workflowName | ForEach-Object { $_.Group | Select-Object -First 1 })
        Assert-Condition ($latestRuns.Count -gt 0) "CI requerido no encontrado para el commit candidato $candidateSha."
        $failed = @($latestRuns | Where-Object { $_.status -ne "completed" -or $_.conclusion -ne "success" })
        Assert-Condition ($failed.Count -eq 0) "CI no verde para el commit candidato $candidateSha."

        $remote = Invoke-Git @("ls-remote", "origin", "refs/heads/$TargetBranch", "refs/heads/$CandidateBranch")
        $remoteMain = [regex]::Match($remote, "(?m)^(?<sha>[0-9a-f]{40})\s+refs/heads/$([regex]::Escape($TargetBranch))$")
        $remoteDev = [regex]::Match($remote, "(?m)^(?<sha>[0-9a-f]{40})\s+refs/heads/$([regex]::Escape($CandidateBranch))$")
        Assert-Condition $remoteDev.Success "No existe origin/$CandidateBranch."
        Assert-Condition ($remoteDev.Groups["sha"].Value -eq $candidateSha) "origin/$CandidateBranch no coincide con el commit candidato."
        if ($remoteMain.Success) {
            $mainSha = $remoteMain.Groups["sha"].Value
            $ancestor = Invoke-Optional "git" @("merge-base", "--is-ancestor", $mainSha, $candidateSha)
            Assert-Condition ($ancestor.Code -eq 0) "$TargetBranch y $CandidateBranch incoherentes: main no es ancestro de la candidata."
        }

        $tag = Invoke-Optional "git" @("rev-parse", "$Version^{commit}")
        Assert-Condition ($tag.Code -ne 0) "Tag $Version ya existe; se rechaza cualquier overwrite."
        $oldTag = Invoke-Optional "git" @("rev-parse", "v1.1.0^{commit}")
        Assert-Condition ($oldTag.Code -eq 0 -and $oldTag.Text -eq "d13ffcf34b6d982a7b3b89a364c17762f5efad70") "v1.1.0 no coincide con su commit historico inmutable."
        $oldTagType = Invoke-Git @("cat-file", "-t", "v1.1.0")
        Assert-Condition ($oldTagType -eq "tag") "v1.1.0 debe conservar un objeto tag anotado."

        $mode = if ($DryRun) { "DRY-RUN" } else { "READINESS-ONLY" }
        Write-Output "PASS ${mode}: $Version candidata en $candidateSha; sin publicaciones ni cambios remotos."
        exit 0
    } finally { Pop-Location }
} catch {
    Write-Error "RELEASE REJECTED: $($_.Exception.Message)"
    exit 1
}
