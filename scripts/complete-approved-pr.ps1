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

    [switch] $CommentOnFailure
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

if ([string]::IsNullOrWhiteSpace($Branch)) {
    $Branch = "feature/$Slug"
}

if ([string]::IsNullOrWhiteSpace($BaseBranch)) {
    $BaseBranch = if ([string]::IsNullOrWhiteSpace($env:BASE_BRANCH)) { "develop" } else { $env:BASE_BRANCH }
}

$prRef = if ($PrNumber -gt 0) { $PrNumber.ToString() } else { $Branch }
$ghPath = Get-GitHubCliPath

Write-Host "==> Validando aprobacion humana de PR '$prRef'..."
$viewResult = Invoke-Gh -GitHubCliPath $ghPath -Arguments @(
    "pr", "view", $prRef,
    "--json", "number,state,baseRefName,headRefName,url,reviewDecision"
)
$pr = $viewResult.Text | ConvertFrom-Json

if ($pr.state -ne "OPEN") {
    throw "La PR '$prRef' debe estar OPEN para completar el gate post-HITL. Estado actual: $($pr.state)."
}

if ($pr.baseRefName -ne $BaseBranch) {
    throw "La PR '$prRef' apunta a '$($pr.baseRefName)', no a '$BaseBranch'."
}

if ($pr.headRefName -ne $Branch) {
    throw "La PR '$prRef' pertenece a head '$($pr.headRefName)', no a '$Branch'."
}

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

if ($checks.Status -ne "passed") {
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

Write-Host "==> Checks verdes. Mergeando PR '$prRef'..."
$mergeFlag = switch ($MergeMethod) {
    "merge" { "--merge" }
    "squash" { "--squash" }
    "rebase" { "--rebase" }
}

[void](Invoke-Gh -GitHubCliPath $ghPath -Arguments @(
    "pr", "merge", $prRef, $mergeFlag, "--delete-branch"
))

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
