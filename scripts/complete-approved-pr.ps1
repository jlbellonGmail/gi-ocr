param(
    [Parameter(Mandatory = $true)]
    [string] $Slug,

    [int] $PrNumber = 0,

    [string] $Branch = "",

    [string] $BaseBranch = "",

    [ValidateSet("merge", "squash", "rebase")]
    [string] $MergeMethod = "merge",

    [string] $WorktreeDir = "",

    [int] $CheckPollSeconds = 10,

    [int] $CheckMaxMinutes = 60,

    [string] $IgnoredWorkflowName = "Post-HITL merge gate",

    [int] $LocalCleanupPollSeconds = 10,

    [int] $LocalCleanupMaxMinutes = 30,

    [switch] $SkipLocalCleanup,

    [switch] $CommentOnFailure,

    [ValidateSet("Review", "SingleMaintainer")]
    [string] $Mode = "Review",

    [string] $EventName = "",

    [string] $Actor = "",

    [string] $AuthorizedActors = "",

    [string] $ExpectedHeadSha = "",

    [string] $ExpectedBranch = "",

    [string] $ExpectedBase = "",

    [string] $HitlIntent = "",

    [string] $Confirmation = ""
)

$ErrorActionPreference = "Stop"

function Get-GitHubCliPath {
    $command = Get-Command gh -ErrorAction SilentlyContinue
    if ($command) {
        return $command.Source
    }

    $defaultPath = Join-Path $env:ProgramFiles "GitHub CLI\gh.exe"
    if (Test-Path -LiteralPath $defaultPath) {
        return $defaultPath
    }

    throw "GitHub CLI (gh) no esta disponible. Se requiere para completar una PR aprobada."
}

function Invoke-Gh {
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
        Text = $text.Trim()
    }
}

function Get-NextReportPath {
    param([Parameter(Mandatory = $true)][string] $Slug)

    $runDir = Join-Path "runs" $Slug
    if (-not (Test-Path -LiteralPath $runDir -PathType Container)) {
        New-Item -ItemType Directory -Path $runDir | Out-Null
    }

    $attempt = 1
    while (Test-Path -LiteralPath (Join-Path $runDir "post-hitl-gate-$attempt.md")) {
        $attempt += 1
    }

    return [pscustomobject]@{
        Attempt = $attempt
        Path = Join-Path $runDir "post-hitl-gate-$attempt.md"
    }
}

function Write-GateReport {
    param(
        [Parameter(Mandatory = $true)]
        [string] $Slug,

        [Parameter(Mandatory = $true)]
        [ValidateSet("approved", "rejected")]
        [string] $Status,

        [Parameter(Mandatory = $true)]
        [string[]] $Feedback,

        [string] $Details = ""
    )

    $report = Get-NextReportPath -Slug $Slug
    $lines = New-Object System.Collections.Generic.List[string]
    [void] $lines.Add("status: $Status")
    [void] $lines.Add("attempt: $($report.Attempt)")
    [void] $lines.Add("feedback:")
    foreach ($item in $Feedback) {
        [void] $lines.Add("  - $item")
    }
    [void] $lines.Add("---")
    [void] $lines.Add("")
    [void] $lines.Add("# Post-HITL gate $($report.Attempt): $Slug")
    [void] $lines.Add("")
    if (-not [string]::IsNullOrWhiteSpace($Details)) {
        [void] $lines.Add("## Detalle")
        [void] $lines.Add("")
        [void] $lines.Add('```text')
        [void] $lines.Add($Details.Trim())
        [void] $lines.Add('```')
        [void] $lines.Add("")
    }

    [System.IO.File]::WriteAllText(
        (Join-Path (Get-Location).Path $report.Path),
        ($lines -join [Environment]::NewLine) + [Environment]::NewLine,
        (New-Object System.Text.UTF8Encoding($false))
    )

    return $report.Path
}

function Add-PrComment {
    param(
        [Parameter(Mandatory = $true)]
        [string] $GitHubCliPath,

        [Parameter(Mandatory = $true)]
        [string] $PrRef,

        [Parameter(Mandatory = $true)]
        [string] $ReportPath
    )

    $body = Get-Content -LiteralPath $ReportPath -Raw -Encoding UTF8
    $bodyFileName = "post-hitl-gate-{0}.md" -f ([guid]::NewGuid())
    $bodyPath = Join-Path -Path ([System.IO.Path]::GetTempPath()) -ChildPath $bodyFileName
    try {
        Set-Content -LiteralPath $bodyPath -Value $body -Encoding UTF8
        [void](Invoke-Gh -GitHubCliPath $GitHubCliPath -Arguments @("pr", "comment", $PrRef, "--body-file", $bodyPath))
    }
    finally {
        if (Test-Path -LiteralPath $bodyPath) {
            Remove-Item -LiteralPath $bodyPath -Force
        }
    }
}

function ConvertTo-ObjectArray {
    param($Value)

    if ($null -eq $Value) {
        return @()
    }

    if ($Value -is [array]) {
        return @($Value)
    }

    return @($Value)
}

function Format-Checks {
    param([object[]] $Checks)

    if ($Checks.Count -eq 0) {
        return "No se encontraron checks relevantes para la PR."
    }

    return (($Checks | ForEach-Object {
        $workflow = if ([string]::IsNullOrWhiteSpace($_.workflow)) { "sin workflow" } else { $_.workflow }
        $name = if ([string]::IsNullOrWhiteSpace($_.name)) { "sin nombre" } else { $_.name }
        "- [$($_.bucket)] $workflow / $name ($($_.state)) $($_.link)"
    }) -join [Environment]::NewLine)
}

function Wait-PrChecks {
    param(
        [Parameter(Mandatory = $true)]
        [string] $GitHubCliPath,

        [Parameter(Mandatory = $true)]
        [string] $PrRef,

        [Parameter(Mandatory = $true)]
        [string] $IgnoredWorkflowName,

        [int] $PollSeconds = 10,

        [int] $MaxMinutes = 60
    )

    $deadline = (Get-Date).AddMinutes($MaxMinutes)
    $lastRelevantChecks = @()

    while ((Get-Date) -lt $deadline) {
        $result = Invoke-Gh -GitHubCliPath $GitHubCliPath -Arguments @(
            "pr", "checks", $PrRef,
            "--json", "bucket,completedAt,link,name,startedAt,state,workflow"
        ) -AllowedExitCodes @(0, 1, 8)

        $checks = if ([string]::IsNullOrWhiteSpace($result.Text)) {
            @()
        }
        else {
            ConvertTo-ObjectArray ($result.Text | ConvertFrom-Json)
        }

        $lastRelevantChecks = @($checks | Where-Object { $_.workflow -ne $IgnoredWorkflowName })
        if ($lastRelevantChecks.Count -eq 0) {
            Start-Sleep -Seconds $PollSeconds
            continue
        }

        $failedChecks = @($lastRelevantChecks | Where-Object { $_.bucket -in @("fail", "cancel") })
        if ($failedChecks.Count -gt 0) {
            return [pscustomobject]@{
                Status = "failed"
                Details = Format-Checks $lastRelevantChecks
            }
        }

        $pendingChecks = @($lastRelevantChecks | Where-Object { $_.bucket -eq "pending" })
        if ($pendingChecks.Count -eq 0) {
            return [pscustomobject]@{
                Status = "passed"
                Details = Format-Checks $lastRelevantChecks
            }
        }

        Start-Sleep -Seconds $PollSeconds
    }

    return [pscustomobject]@{
        Status = "timeout"
        Details = Format-Checks $lastRelevantChecks
    }
}

function Get-PrSnapshot {
    param(
        [Parameter(Mandatory = $true)][string] $GitHubCliPath,
        [Parameter(Mandatory = $true)][string] $PrRef
    )

    $result = Invoke-Gh -GitHubCliPath $GitHubCliPath -Arguments @(
        "pr", "view", $PrRef,
        "--json", "number,state,baseRefName,headRefName,headRefOid,url,reviewDecision"
    )
    return $result.Text | ConvertFrom-Json
}

function Assert-ExactSha {
    param([Parameter(Mandatory = $true)][string] $Sha)

    if ($Sha -notmatch "^[0-9a-fA-F]{40}$") {
        throw "expected_head_sha debe ser un SHA completo de 40 caracteres."
    }
}

function Assert-SingleMaintainerAuthorization {
    param(
        [Parameter(Mandatory = $true)][string] $EventName,
        [Parameter(Mandatory = $true)][string] $Actor,
        [Parameter(Mandatory = $true)][string] $AuthorizedActors,
        [Parameter(Mandatory = $true)][string] $HitlIntent,
        [Parameter(Mandatory = $true)][string] $Confirmation
    )

    if ($EventName -ne "workflow_dispatch") {
        throw "Single-maintainer solo puede ejecutarse mediante workflow_dispatch. event_name=$EventName"
    }

    $allowed = @($AuthorizedActors -split "," | ForEach-Object { $_.Trim() } | Where-Object { $_ -ne "" })
    if ($allowed.Count -eq 0) {
        throw "SINGLE_MAINTAINER_HITL_ACTORS no existe, esta vacia o no contiene actores validos."
    }

    if ($allowed -cnotcontains $Actor) {
        throw "El actor '$Actor' no esta autorizado por SINGLE_MAINTAINER_HITL_ACTORS."
    }

    if ($HitlIntent -cne "MERGE") {
        throw "hitl_intent debe ser exactamente MERGE."
    }

    if ($Confirmation -cne "I_CONFIRM_HITL_MERGE") {
        throw "confirmation debe ser exactamente I_CONFIRM_HITL_MERGE."
    }
}

function Get-RequiredCiChecks {
    param(
        [Parameter(Mandatory = $true)][string] $GitHubCliPath,
        [Parameter(Mandatory = $true)][string] $Repository,
        [Parameter(Mandatory = $true)][string] $ExpectedHeadSha
    )

    $required = @(
        @{ Workflow = "CI"; Job = "test"; Id = "CI/test" },
        @{ Workflow = "CI"; Job = "quality"; Id = "CI/quality" }
    )

    $runsResult = Invoke-Gh -GitHubCliPath $GitHubCliPath -Arguments @(
        "run", "list", "--repo", $Repository, "--workflow", "ci.yml",
        "--commit", $ExpectedHeadSha, "--limit", "50",
        "--json", "databaseId,status,conclusion,headSha"
    )
    $runs = if ([string]::IsNullOrWhiteSpace($runsResult.Text)) { @() } else { ConvertTo-ObjectArray ($runsResult.Text | ConvertFrom-Json) }

    $results = foreach ($item in $required) {
        $match = $null
        foreach ($run in ($runs | Sort-Object databaseId -Descending)) {
            if ($run.headSha -ne $ExpectedHeadSha) { continue }
            $runResult = Invoke-Gh -GitHubCliPath $GitHubCliPath -Arguments @(
                "run", "view", "$($run.databaseId)", "--repo", $Repository, "--json", "jobs"
            )
            $jobs = (ConvertFrom-Json $runResult.Text).jobs
            $job = @($jobs | Where-Object { $_.name -eq $item.Job } | Select-Object -First 1)
            if ($job.Count -gt 0) {
                $match = [pscustomobject]@{
                    Id = $item.Id
                    Workflow = $item.Workflow
                    Job = $item.Job
                    Status = [string]$job[0].status
                    Conclusion = [string]$job[0].conclusion
                    HeadSha = [string]$run.headSha
                    RunId = [string]$run.databaseId
                }
                break
            }
        }

        if ($null -eq $match) {
            [pscustomobject]@{ Id = $item.Id; Workflow = $item.Workflow; Job = $item.Job; Status = "missing"; Conclusion = ""; HeadSha = ""; RunId = "" }
        }
        else { $match }
    }

    foreach ($check in $results) {
        if ($check.HeadSha -ne $ExpectedHeadSha -or $check.Status -ne "completed" -or $check.Conclusion -ne "success") {
            throw "Check obligatorio $($check.Id) no valido para ${ExpectedHeadSha}: status=$($check.Status), conclusion=$($check.Conclusion), head_sha=$($check.HeadSha), run=$($check.RunId)."
        }
    }

    return @($results)
}

function Assert-PrSnapshot {
    param(
        [Parameter(Mandatory = $true)]$Pr,
        [Parameter(Mandatory = $true)][int] $ExpectedPrNumber,
        [Parameter(Mandatory = $true)][string] $ExpectedBaseName,
        [Parameter(Mandatory = $true)][string] $ExpectedBranchName,
        [string] $ExpectedHeadSha = ""
    )

    if ($Pr.number -ne $ExpectedPrNumber) { throw "La PR consultada no coincide con pr_number." }
    if ($Pr.state -ne "OPEN") { throw "La PR '$($Pr.number)' debe estar OPEN. Estado actual: $($Pr.state)." }
    if ($Pr.baseRefName -ne $ExpectedBaseName) { throw "La PR apunta a '$($Pr.baseRefName)', no a '$ExpectedBaseName'." }
    if ($Pr.headRefName -ne $ExpectedBranchName) { throw "La PR pertenece a '$($Pr.headRefName)', no a '$ExpectedBranchName'." }
    if (-not [string]::IsNullOrWhiteSpace($ExpectedHeadSha) -and $Pr.headRefOid -ne $ExpectedHeadSha) {
        throw "El HEAD real '$($Pr.headRefOid)' no coincide con expected_head_sha '$ExpectedHeadSha'."
    }
}

function Write-HitlSummary {
    param(
        [Parameter(Mandatory = $true)][string] $ModeName,
        [Parameter(Mandatory = $true)][string] $ActorName,
        [Parameter(Mandatory = $true)][string] $PrNumber,
        [Parameter(Mandatory = $true)][string] $BranchName,
        [Parameter(Mandatory = $true)][string] $BaseName,
        [Parameter(Mandatory = $true)][string] $ExpectedSha,
        [Parameter(Mandatory = $true)][string] $ObservedSha,
        [Parameter(Mandatory = $true)][string] $Intent,
        [Parameter(Mandatory = $true)][string] $Result,
        [object[]] $Checks = @()
    )

    $timestamp = (Get-Date).ToUniversalTime().ToString("o")
    $lines = @(
        "HITL mode: $ModeName",
        "Actor: $ActorName",
        "Timestamp UTC: $timestamp",
        "PR: $PrNumber",
        "Branch: $BranchName",
        "Base: $BaseName",
        "Expected HEAD SHA: $ExpectedSha",
        "Observed HEAD SHA: $ObservedSha",
        "Intent: $Intent",
        "Result: $Result"
    )
    if ($ModeName -eq "single-maintainer") { $lines += "Authorization source: vars.SINGLE_MAINTAINER_HITL_ACTORS" }
    foreach ($check in $Checks) { $lines += "Check $($check.Id): status=$($check.Status), conclusion=$($check.Conclusion), head_sha=$($check.HeadSha), run=$($check.RunId)" }
    $text = $lines -join [Environment]::NewLine
    Write-Host $text
    if (-not [string]::IsNullOrWhiteSpace($env:GITHUB_STEP_SUMMARY)) {
        Add-Content -LiteralPath $env:GITHUB_STEP_SUMMARY -Value ("## HITL`n`n" + $text) -Encoding UTF8
    }
}

if ([string]::IsNullOrWhiteSpace($Branch)) {
    $Branch = "feature/$Slug"
}

if ([string]::IsNullOrWhiteSpace($BaseBranch)) {
    $BaseBranch = if ([string]::IsNullOrWhiteSpace($env:BASE_BRANCH)) { "develop" } else { $env:BASE_BRANCH }
}

$prRef = if ($PrNumber -gt 0) { $PrNumber.ToString() } else { $Branch }
$ghPath = Get-GitHubCliPath

Write-Host "==> Validando autorizacion HITL de PR '$prRef' en modo $Mode..."
$pr = Get-PrSnapshot -GitHubCliPath $ghPath -PrRef $prRef
$checks = @()
$expectedSha = ""
$expectedBranchName = if ([string]::IsNullOrWhiteSpace($ExpectedBranch)) { $Branch } else { $ExpectedBranch }
$expectedBaseName = if ([string]::IsNullOrWhiteSpace($ExpectedBase)) { $BaseBranch } else { $ExpectedBase }

if ($Mode -eq "SingleMaintainer") {
    if ($PrNumber -le 0) { throw "Single-maintainer requiere pr_number exacto mediante -PrNumber." }
    $expectedSha = $ExpectedHeadSha
    Assert-ExactSha -Sha $expectedSha
    Assert-SingleMaintainerAuthorization -EventName $EventName -Actor $Actor -AuthorizedActors $AuthorizedActors -HitlIntent $HitlIntent -Confirmation $Confirmation
    if ($expectedBaseName -ne $BaseBranch) {
        throw "Single-maintainer solo permite la base esperada '$BaseBranch'; se recibio '$expectedBaseName'."
    }
    Assert-PrSnapshot -Pr $pr -ExpectedPrNumber $PrNumber -ExpectedBaseName $expectedBaseName -ExpectedBranchName $expectedBranchName -ExpectedHeadSha $expectedSha
    $repoResult = Invoke-Gh -GitHubCliPath $ghPath -Arguments @("repo", "view", "--json", "nameWithOwner")
    $repository = (ConvertFrom-Json $repoResult.Text).nameWithOwner
    $checks = Get-RequiredCiChecks -GitHubCliPath $ghPath -Repository $repository -ExpectedHeadSha $expectedSha
    Write-HitlSummary -ModeName "single-maintainer" -ActorName $Actor -PrNumber "$($pr.number)" -BranchName $pr.headRefName -BaseName $pr.baseRefName -ExpectedSha $expectedSha -ObservedSha $pr.headRefOid -Intent $HitlIntent -Result "pre-merge validation passed" -Checks $checks
}
else {
    Assert-PrSnapshot -Pr $pr -ExpectedPrNumber $pr.number -ExpectedBaseName $BaseBranch -ExpectedBranchName $Branch
    if ($pr.reviewDecision -ne "APPROVED") {
        throw "La PR '$prRef' todavia no tiene aprobacion HITL. reviewDecision=$($pr.reviewDecision)."
    }
    Write-Host "==> Aprobacion HITL confirmada. Esperando checks post-aprobacion..."
    $checks = Wait-PrChecks `
        -GitHubCliPath $ghPath `
        -PrRef $prRef `
        -IgnoredWorkflowName $IgnoredWorkflowName `
        -PollSeconds $CheckPollSeconds `
        -MaxMinutes $CheckMaxMinutes
}

if ($Mode -eq "Review" -and $checks.Status -ne "passed") {
    $reportPath = Write-GateReport `
        -Slug $Slug `
        -Status "rejected" `
        -Feedback @(
            "Los checks post-HITL de la PR $prRef no terminaron en verde (estado: $($checks.Status)).",
            "Builder-agent debe corregir la rama $Branch y relanzar QA/ready-for-pr sin pedir otro checkpoint humano."
        ) `
        -Details $checks.Details

    if ($CommentOnFailure) {
        Add-PrComment -GitHubCliPath $ghPath -PrRef $prRef -ReportPath $reportPath
    }

    throw "Checks post-HITL fallidos para '$prRef'. Feedback para builder: $reportPath"
}

if ($Mode -eq "SingleMaintainer") {
    $latestPr = Get-PrSnapshot -GitHubCliPath $ghPath -PrRef $prRef
    Assert-PrSnapshot -Pr $latestPr -ExpectedPrNumber $PrNumber -ExpectedBaseName $expectedBaseName -ExpectedBranchName $expectedBranchName -ExpectedHeadSha $expectedSha
    $checks = Get-RequiredCiChecks -GitHubCliPath $ghPath -Repository $repository -ExpectedHeadSha $expectedSha
    Write-HitlSummary -ModeName "single-maintainer" -ActorName $Actor -PrNumber "$($latestPr.number)" -BranchName $latestPr.headRefName -BaseName $latestPr.baseRefName -ExpectedSha $expectedSha -ObservedSha $latestPr.headRefOid -Intent $HitlIntent -Result "final validation passed" -Checks $checks
}

Write-Host "==> Checks verdes. Mergeando PR '$prRef'..."
$mergeFlag = switch ($MergeMethod) {
    "merge" { "--merge" }
    "squash" { "--squash" }
    "rebase" { "--rebase" }
}

$mergeArguments = @("pr", "merge", $prRef, $mergeFlag, "--delete-branch")
if ($Mode -eq "SingleMaintainer") {
    $mergeArguments += @("--match-head-commit", $expectedSha)
}
[void](Invoke-Gh -GitHubCliPath $ghPath -Arguments $mergeArguments)

if ($Mode -eq "SingleMaintainer") {
    Write-HitlSummary -ModeName "single-maintainer" -ActorName $Actor -PrNumber "$($latestPr.number)" -BranchName $latestPr.headRefName -BaseName $latestPr.baseRefName -ExpectedSha $expectedSha -ObservedSha $latestPr.headRefOid -Intent $HitlIntent -Result "merge executed" -Checks $checks
}

$successReport = Write-GateReport `
    -Slug $Slug `
    -Status "approved" `
    -Feedback @(
        "PR $prRef aprobada por HITL, checks post-aprobacion verdes y merge ejecutado.",
        "El cierre remoto de ROADMAP queda a cargo de post-merge-close-feature.yml."
    ) `
    -Details $checks.Details

Write-Host "==> PR mergeada. Evidencia: $successReport"

if ($SkipLocalCleanup -or $env:GITHUB_ACTIONS -eq "true") {
    Write-Host "==> Limpieza local omitida. El runner remoto no debe borrar worktrees locales."
    exit 0
}

$reconciler = Join-Path $PSScriptRoot "reconcile-local-feature.ps1"
if (-not (Test-Path -LiteralPath $reconciler -PathType Leaf)) {
    throw "No existe el reconciliador local esperado: $reconciler"
}

Write-Host "==> Esperando cierre remoto y limpieza local..."
$cleanupArgs = @(
    "-NoProfile",
    "-ExecutionPolicy", "Bypass",
    "-File", $reconciler,
    "-Slug", $Slug,
    "-Branch", $Branch,
    "-PollSeconds", $LocalCleanupPollSeconds,
    "-MaxMinutes", $LocalCleanupMaxMinutes
)
if (-not [string]::IsNullOrWhiteSpace($WorktreeDir)) {
    $cleanupArgs += @("-WorktreeDir", $WorktreeDir)
}

& powershell.exe @cleanupArgs
if ($LASTEXITCODE -ne 0) {
    throw "La PR fue mergeada, pero fallo la limpieza local. Reejecutar reconcile-local-feature.ps1 para $Slug."
}
