param(
    [string] $ScenarioPath = "",
    [string] $OutputPath = "",
    [ValidateSet("smoke", "normal", "full")]
    [string] $Profile = "normal",
    [string] $RunId = "local",
    [switch] $FailOnFailure
)

$ErrorActionPreference = "Stop"

function Read-Json([string] $Path) {
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { throw "No existe el archivo de escenarios: $Path" }
    try { return Get-Content -LiteralPath $Path -Raw -Encoding UTF8 | ConvertFrom-Json }
    catch { throw "El archivo de escenarios no contiene JSON valido: $Path" }
}

function Get-Value($Object, [string] $Name) {
    $property = $Object.PSObject.Properties[$Name]
    if ($null -eq $property) { return $null }
    return $property.Value
}

function Test-Scenario($Scenario) {
    foreach ($name in @("id", "version", "question", "expected", "actual")) {
        if ($null -eq (Get-Value $Scenario $name)) { throw "Escenario sin campo requerido '$name'." }
    }
    $expected = $Scenario.expected
    $actual = $Scenario.actual
    $mismatches = New-Object System.Collections.Generic.List[string]
    foreach ($property in $expected.PSObject.Properties) {
        $actualProperty = $actual.PSObject.Properties[$property.Name]
        if ($null -eq $actualProperty) {
            [void]$mismatches.Add("actual.$($property.Name) ausente")
            continue
        }
        $expectedJson = $property.Value | ConvertTo-Json -Compress -Depth 10
        $actualJson = $actualProperty.Value | ConvertTo-Json -Compress -Depth 10
        if ($expectedJson -ne $actualJson) { [void]$mismatches.Add("$($property.Name): esperado $expectedJson, actual $actualJson") }
    }
    $passed = $mismatches.Count -eq 0
    [ordered]@{
        schemaVersion = 1
        evalSuite = "agentic-evals"
        suiteVersion = [string]$Scenario.version
        runId = $RunId
        profile = $Profile
        scenario = [string]$Scenario.id
        question = [string]$Scenario.question
        expected = $expected
        actual = $actual
        pass = $passed
        reason = if ($passed) { "La observacion coincide con todos los criterios declarados." } else { $mismatches -join "; " }
        metrics = if ($Scenario.metrics) { $Scenario.metrics } else { [ordered]@{} }
        nondeterminism = if ($Scenario.nondeterminism) { $Scenario.nondeterminism } else { "none" }
        providerAgnostic = $true
        modelAgnostic = $true
    }
}

$root = (& git rev-parse --show-toplevel).Trim()
if ([string]::IsNullOrWhiteSpace($ScenarioPath)) { $ScenarioPath = Join-Path $root "evals/scenarios.json" }
if (-not [System.IO.Path]::IsPathRooted($ScenarioPath)) { $ScenarioPath = Join-Path $root $ScenarioPath }
$document = Read-Json $ScenarioPath
$all = @($document.scenarios)
if ($all.Count -eq 0) { throw "El archivo no declara escenarios." }
$selected = switch ($Profile) {
    "smoke" { @("A-trivial", "C-high-risk", "G-no-progress") }
    "normal" { @("A-trivial", "B-normal", "C-high-risk", "D-ambiguity", "E-technical-retry", "F-external-block", "G-no-progress", "H-stale-review", "I-insufficient-evidence", "J-out-of-scope") }
    "full" { @($all | ForEach-Object { [string]$_.id }) }
}
$scenarios = @($all | Where-Object { $selected -contains [string]$_.id })
if ($scenarios.Count -ne $selected.Count -and $Profile -ne "full") { throw "Faltan escenarios requeridos por el perfil $Profile." }
$ids = @($scenarios | ForEach-Object { [string]$_.id })
if (@($ids | Sort-Object -Unique).Count -ne $ids.Count) { throw "Hay ids de escenario duplicados." }
$results = @($scenarios | ForEach-Object { Test-Scenario $_ })
$passed = @($results | Where-Object { $_.pass }).Count
$failed = $results.Count - $passed
$summary = [ordered]@{
    schemaVersion = 1; evalSuite = "agentic-evals"; suiteVersion = [string]$document.suiteVersion
    runId = $RunId; profile = $Profile; scenarioCount = $results.Count; passed = $passed; failed = $failed
    passRate = if ($results.Count -eq 0) { 0 } else { [math]::Round($passed / $results.Count, 4) }
    metrics = [ordered]@{
        correctDecisions = "$passed/$($results.Count)"; correctEscalations = @($results | Where-Object { $_.metrics.escalation -eq $true -and $_.pass }).Count
        convergenceSuccess = @($results | Where-Object { $_.metrics.convergence -eq "success" -and $_.pass }).Count
        loopsAvoided = @($results | Where-Object { $_.metrics.loopAvoided -eq $true -and $_.pass }).Count
        scopeViolationsDetected = @($results | Where-Object { $_.metrics.scopeViolationDetected -eq $true -and $_.pass }).Count
    }
    providerAgnostic = $true; modelAgnostic = $true
}
$lines = @($results | ForEach-Object { $_ | ConvertTo-Json -Compress -Depth 15 })
$lines += ($summary | ConvertTo-Json -Compress -Depth 15)
if (-not [string]::IsNullOrWhiteSpace($OutputPath)) {
    if (-not [System.IO.Path]::IsPathRooted($OutputPath)) { $OutputPath = Join-Path $root $OutputPath }
    $parent = Split-Path -Parent $OutputPath
    if (-not (Test-Path -LiteralPath $parent -PathType Container)) { New-Item -ItemType Directory -Path $parent -Force | Out-Null }
    [System.IO.File]::WriteAllLines($OutputPath, $lines, (New-Object System.Text.UTF8Encoding($false)))
}
$lines -join [Environment]::NewLine
if ($FailOnFailure -and $failed -gt 0) { exit 1 }
