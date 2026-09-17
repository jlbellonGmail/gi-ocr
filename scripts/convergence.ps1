param(
    [Parameter(Mandatory = $true)] [string] $InputPath,
    [string] $OutputPath = "",
    [int] $MaxIterations = 0
)

$ErrorActionPreference = "Stop"

function Read-JsonFile([string] $Path) {
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { throw "No existe la entrada de convergencia: $Path" }
    try { return Get-Content -LiteralPath $Path -Raw -Encoding UTF8 | ConvertFrom-Json }
    catch { throw "La entrada de convergencia no contiene JSON valido: $Path" }
}

function Get-Assessment($Payload) {
    $assessment = $Payload.assessment
    if ($Payload.assessmentPath) { $assessment = Read-JsonFile ([string]$Payload.assessmentPath) }
    if (-not $assessment) { throw "Falta la salida ASSESS en la entrada de convergencia." }
    if ($assessment.assessment -ne "ASSESS" -or $assessment.deterministic -ne $true) { throw "La convergencia solo consume ASSESS determinista." }
    if ($assessment.depth -notin @("LIGHT", "STANDARD", "FULL")) { throw "ASSESS produjo una profundidad invalida." }
    return $assessment
}

function Get-Depth($Payload, $Assessment) {
    if ($Payload.sdd -and $Payload.sdd.depth) { $depth = [string]$Payload.sdd.depth }
    elseif ($Payload.sddPath) { $depth = [string](Read-JsonFile ([string]$Payload.sddPath)).depth }
    else { $depth = [string]$Assessment.depth }
    if ($depth -notin @("LIGHT", "STANDARD", "FULL")) { throw "La profundidad SDD debe ser LIGHT, STANDARD o FULL." }
    if ($depth -ne [string]$Assessment.depth) { throw "La profundidad SDD no coincide con ASSESS; no se reclasifica." }
    return $depth
}

function Get-Items($Reviewer) {
    if ($Reviewer.findings) { return @($Reviewer.findings) }
    return @()
}

function Get-Fingerprint($Items) {
    $open = @($Items | Where-Object { [string]$_.status -eq "OPEN" } | ForEach-Object {
        $id = if ($_.id) { [string]$_.id } else { [string]$_.description }
        "{0}:{1}:{2}" -f $id, ([string]$_.severity), ([string]$_.description)
    } | Sort-Object)
    return ($open -join "|")
}

$payload = Read-JsonFile $InputPath
$assessment = Get-Assessment $payload
$depth = Get-Depth $payload $assessment
$budget = @{ LIGHT = 2; STANDARD = 4; FULL = 6 }[$depth]
if ($MaxIterations -gt 0) { $budget = $MaxIterations }
$iteration = [int]$payload.iteration
if ($iteration -lt 1) { $iteration = 1 }
$reviewer = $payload.reviewer
if (-not $reviewer) { throw "Falta el resultado independiente del Reviewer." }
$verdict = ([string]$reviewer.verdict).ToUpperInvariant()
$items = Get-Items $reviewer
$open = @($items | Where-Object { [string]$_.status -eq "OPEN" })
$resolved = @($items | Where-Object { [string]$_.status -in @("RESOLVED", "ACCEPTED", "RATIONALE") })
$tests = $payload.tests
$testsGreen = ($tests -and ($tests.status -in @("green", "passed", "approved") -or $tests.passed -eq $true))
$hasMaterialDecision = ($reviewer.needsPlanner -eq $true -or $reviewer.needsHumanDecision -eq $true -or $reviewer.materialDecision -eq $true)
$externalBlock = ($reviewer.blockedExternal -eq $true -or $reviewer.blocked -eq $true -and $reviewer.blockReason -eq "external")
$technicalFailure = ($payload.execution -and [string]$payload.execution.status -in @("failed", "error"))
$previous = $payload.previous
$fingerprint = Get-Fingerprint $items
$sameFindings = ($previous -and [string]$previous.findingsFingerprint -eq $fingerprint -and $fingerprint -ne "")
$progress = (-not $sameFindings) -or ($previous -and [int]$previous.openFindings -gt $open.Count) -or ($tests -and $tests.previouslyFailed -eq $true -and $testsGreen)
$noProgress = ($verdict -eq "CHANGES_REQUESTED" -and -not $progress)
$terminal = $false
$escalation = $null
$nextAction = ""

if ($technicalFailure) { $verdictOut = "FAILED_SAFELY"; $terminal = $true; $escalation = "technical_execution_failure" }
elseif ($externalBlock) { $verdictOut = "BLOCKED"; $terminal = $true; $escalation = "external_dependency" }
elseif ($hasMaterialDecision) { $verdictOut = "NEEDS_HUMAN_DECISION"; $terminal = $true; $escalation = if ($reviewer.needsPlanner -eq $true) { "planner_reentry_required" } else { "material_decision" } }
elseif ($verdict -eq "APPROVED" -and $open.Count -eq 0 -and $testsGreen) { $verdictOut = "APPROVED"; $terminal = $true }
elseif ($verdict -eq "BLOCKED") { $verdictOut = "BLOCKED"; $terminal = $true; $escalation = "reviewer_blocked" }
elseif ($noProgress -or $iteration -ge $budget) { $verdictOut = "FAILED_SAFELY"; $terminal = $true; $escalation = "convergence_stalled" }
else { $verdictOut = "CHANGES_REQUESTED"; $nextAction = "Builder debe resolver los findings OPEN y volver a ejecutar tests y Reviewer." }

$result = [ordered]@{
    schemaVersion = 1; convergence = "CONVERGENCE"; iteration = $iteration; depth = $depth
    verdict = $verdictOut; terminal = $terminal
    budget = [ordered]@{ maxIterations = $budget; policy = "LIGHT=2, STANDARD=4, FULL=6; configurable por MaxIterations" }
    findings = [ordered]@{ open = @($open); resolved = @($resolved); openCount = $open.Count; resolvedCount = $resolved.Count; fingerprint = $fingerprint }
    progress = [bool]$progress; noProgress = [bool]$noProgress; escalation = $escalation; nextAction = $nextAction
    reviewerIndependent = $true; builderMayApprove = $false; providerAgnostic = $true
}
$json = $result | ConvertTo-Json -Depth 12
if ($OutputPath) {
    $parent = Split-Path -Parent $OutputPath
    if (-not (Test-Path -LiteralPath $parent -PathType Container)) { New-Item -ItemType Directory -Path $parent -Force | Out-Null }
    [System.IO.File]::WriteAllText((Join-Path ([System.IO.Path]::GetFullPath($parent)) (Split-Path -Leaf $OutputPath)), $json + [Environment]::NewLine, (New-Object Text.UTF8Encoding($false)))
}
$json
