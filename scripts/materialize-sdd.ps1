param(
    [Parameter(Mandatory = $true)]
    [string] $AssessmentPath,

    [Parameter(Mandatory = $true)]
    [string] $Objective,

    [string] $OutputPath = "",

    [string] $EvidencePath = ""
)

$ErrorActionPreference = "Stop"

function Read-Assessment {
    param([Parameter(Mandatory = $true)][string] $Path)

    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "No existe la evidencia ASSESS: $Path"
    }

    $lines = @(Get-Content -LiteralPath $Path -Encoding UTF8 |
        Where-Object { -not [string]::IsNullOrWhiteSpace($_) })
    if ($lines.Count -eq 0) {
        throw "La evidencia ASSESS esta vacia: $Path"
    }

    # ASSESS puede emitir un JSON unico o JSONL. En JSONL se consume la
    # observacion mas reciente; no se vuelve a ejecutar ni a reinterpretar la
    # heuristica de clasificacion.
    try {
        $assessment = $lines[-1] | ConvertFrom-Json
    }
    catch {
        throw "La evidencia ASSESS no contiene JSON valido: $Path"
    }

    if ($assessment.assessment -ne "ASSESS" -or $assessment.deterministic -ne $true) {
        throw "La evidencia no es una salida determinista de ASSESS."
    }
    if ($assessment.depth -notin @("LIGHT", "STANDARD", "FULL")) {
        throw "ASSESS no produjo una profundidad valida: $($assessment.depth)"
    }
    if ([string]::IsNullOrWhiteSpace([string]$assessment.risk)) {
        throw "La evidencia ASSESS no contiene riesgo."
    }
    if (@($assessment.changedFiles).Count -eq 0) {
        throw "La evidencia ASSESS no contiene archivos evaluados."
    }

    return $assessment
}

if ([string]::IsNullOrWhiteSpace($Objective)) {
    throw "El objetivo no puede estar vacio."
}

$assessment = Read-Assessment -Path $AssessmentPath
$depth = [string]$assessment.depth

$steps = switch ($depth) {
    "LIGHT" { @("objective", "mini-spec", "build", "tests", "review") }
    "STANDARD" { @("objective", "light-plan", "spec", "plan/tasks-proportional", "build", "tests", "review") }
    "FULL" { @("objective", "planning", "spec", "plan", "tasks", "validations", "build", "tests", "review", "gates") }
}

$artifacts = switch ($depth) {
    "LIGHT" { @("objective", "mini-spec", "test-evidence", "review") }
    "STANDARD" { @("objective", "spec", "light-plan", "plan", "tasks", "test-evidence", "review") }
    "FULL" { @("objective", "spec", "plan", "tasks", "decision", "validation-evidence", "test-evidence", "review", "gates") }
}

$gates = New-Object System.Collections.Generic.List[string]
if ($depth -eq "FULL") {
    [void]$gates.Add("required-validations")
    [void]$gates.Add("contract-proportional")
}
$root = (& git rev-parse --show-toplevel).Trim()
$result = [ordered]@{
    schemaVersion = 1
    sdd = "ADAPTIVE"
    deterministic = $true
    objective = $Objective.Trim()
    sourceAssessment = (Resolve-Path -LiteralPath $AssessmentPath).Path
    assessmentRisk = [string]$assessment.risk
    depth = $depth
    steps = $steps
    requiredArtifacts = $artifacts
    gates = $gates
    changedFiles = @($assessment.changedFiles)
    rationale = "La profundidad es la producida por ASSESS; este materializador solo traduce la salida a un contrato SDD proporcional."
}

$json = $result | ConvertTo-Json -Depth 10 -Compress
if (-not [string]::IsNullOrWhiteSpace($OutputPath)) {
    if (-not [System.IO.Path]::IsPathRooted($OutputPath)) { $OutputPath = Join-Path $root $OutputPath }
    $parent = Split-Path -Parent $OutputPath
    if (-not (Test-Path -LiteralPath $parent -PathType Container)) { New-Item -ItemType Directory -Path $parent | Out-Null }
    [System.IO.File]::WriteAllText((Resolve-Path $parent).Path + [System.IO.Path]::DirectorySeparatorChar + (Split-Path -Leaf $OutputPath), $json + [Environment]::NewLine, (New-Object System.Text.UTF8Encoding($false)))
}
if (-not [string]::IsNullOrWhiteSpace($EvidencePath)) {
    if (-not [System.IO.Path]::IsPathRooted($EvidencePath)) { $EvidencePath = Join-Path $root $EvidencePath }
    $parent = Split-Path -Parent $EvidencePath
    if (-not (Test-Path -LiteralPath $parent -PathType Container)) { New-Item -ItemType Directory -Path $parent | Out-Null }
    $writer = New-Object System.IO.StreamWriter($EvidencePath, $true, (New-Object System.Text.UTF8Encoding($false)))
    try { $writer.WriteLine($json) } finally { $writer.Dispose() }
}
$result | ConvertTo-Json -Depth 10
