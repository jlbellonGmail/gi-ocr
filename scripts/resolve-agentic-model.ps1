param(
    [Parameter(Mandatory = $true)]
    [string] $Role,

    [string] $Stage = "",

    [string] $Feature = "",

    [string] $RunFile = "",

    [string] $Model = "",

    [string] $Variant = "",

    [string[]] $Fallback = @(),

    [string] $FailedModel = "",

    [string] $FailureReason = "",

    [string] $EvidencePath = "",

    [switch] $AllowMissingCredentials,

    [switch] $NoEvidence,

    [switch] $UseLiveCatalog
)

$ErrorActionPreference = "Stop"
$stopwatch = [System.Diagnostics.Stopwatch]::StartNew()
$selectedForEvidence = $null
$selectionOriginForEvidence = "unresolved"

function Get-RepositoryRoot {
    $root = (& git rev-parse --show-toplevel) -join "`n"
    if ($LASTEXITCODE -eq 0 -and -not [string]::IsNullOrWhiteSpace($root)) {
        return [System.IO.Path]::GetFullPath($root.Trim())
    }

    return [System.IO.Path]::GetFullPath((Get-Location).Path)
}

function Read-JsonFile {
    param(
        [Parameter(Mandatory = $true)]
        [string] $Path
    )

    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "No existe el archivo canonico requerido: $Path"
    }

    return (Get-Content -LiteralPath $Path -Raw -Encoding UTF8 | ConvertFrom-Json)
}

function ConvertFrom-MinimalRunYaml {
    param(
        [Parameter(Mandatory = $true)]
        [string] $Path
    )

    $execution = [ordered] @{
        model = "default"
        variant = "default"
        fallback = @()
    }

    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        return [pscustomobject] $execution
    }

    $inExecution = $false
    $inFallback = $false
    foreach ($line in Get-Content -LiteralPath $Path -Encoding UTF8) {
        $withoutComment = ($line -replace '\s+#.*$', '').TrimEnd()
        if ([string]::IsNullOrWhiteSpace($withoutComment)) {
            continue
        }

        if ($withoutComment -match '^execution:\s*$') {
            $inExecution = $true
            $inFallback = $false
            continue
        }

        if (-not $inExecution) {
            continue
        }

        if ($withoutComment -match '^\s{2}model:\s*(.+?)\s*$') {
            $execution.model = ConvertFrom-YamlScalar $Matches[1]
            $inFallback = $false
            continue
        }

        if ($withoutComment -match '^\s{2}variant:\s*(.+?)\s*$') {
            $execution.variant = ConvertFrom-YamlScalar $Matches[1]
            $inFallback = $false
            continue
        }

        if ($withoutComment -match '^\s{2}fallback:\s*$') {
            $inFallback = $true
            continue
        }

        if ($inFallback -and $withoutComment -match '^\s{4}-\s*(.+?)\s*$') {
            $execution.fallback += ,(ConvertFrom-YamlScalar $Matches[1])
            continue
        }

        throw "run.yaml contiene una clave no soportada por la interfaz minima del punto 1: '$line'"
    }

    return [pscustomobject] $execution
}

function ConvertFrom-YamlScalar {
    param(
        [Parameter(Mandatory = $true)]
        [string] $Value
    )

    $trimmed = $Value.Trim()
    if (($trimmed.StartsWith("'") -and $trimmed.EndsWith("'")) -or
        ($trimmed.StartsWith('"') -and $trimmed.EndsWith('"'))) {
        return $trimmed.Substring(1, $trimmed.Length - 2)
    }

    return $trimmed
}

function Split-ModelRef {
    param(
        [Parameter(Mandatory = $true)]
        [string] $ModelRef
    )

    $parts = $ModelRef.Split("/", 2)
    if ($parts.Count -ne 2 -or [string]::IsNullOrWhiteSpace($parts[0]) -or [string]::IsNullOrWhiteSpace($parts[1])) {
        throw "Modelo invalido '$ModelRef'. Usa opencode-go/<modelo>, opencode/<modelo> u openrouter/<proveedor>/<modelo>."
    }

    return [pscustomobject] @{
        Provider = $parts[0]
        Model = $parts[1]
        Ref = $ModelRef
    }
}

function Get-ProviderConfig {
    param(
        [Parameter(Mandatory = $true)]
        [object] $Models,

        [Parameter(Mandatory = $true)]
        [string] $Provider
    )

    $property = $Models.providers.PSObject.Properties[$Provider]
    if ($null -eq $property) {
        throw "Proveedor desconocido o no autorizado: $Provider"
    }

    return $property.Value
}

function Assert-ModelAllowed {
    param(
        [Parameter(Mandatory = $true)]
        [object] $Models,

        [Parameter(Mandatory = $true)]
        [string] $ModelRef
    )

    $split = Split-ModelRef $ModelRef
    $providerConfig = Get-ProviderConfig -Models $Models -Provider $split.Provider
    $allowed = @($providerConfig.models)
    if ($allowed -notcontains $split.Model) {
        throw "Modelo no autorizado o inexistente para $($split.Provider): $($split.Model)"
    }

    return [pscustomobject] @{
        Provider = $split.Provider
        Model = $split.Model
        Ref = $split.Ref
        ProviderConfig = $providerConfig
    }
}

function Test-ProviderCredentials {
    param(
        [Parameter(Mandatory = $true)]
        [object] $ProviderConfig
    )

    if ($AllowMissingCredentials) {
        return $true
    }

    foreach ($name in @($ProviderConfig.credentialEnv)) {
        $value = [Environment]::GetEnvironmentVariable($name)
        if (-not [string]::IsNullOrWhiteSpace($value)) {
            return $true
        }
    }

    return $false
}

function Get-FallbackLabels {
    param(
        [Parameter(Mandatory = $true)]
        [object] $Declaration,

        [string[]] $ExplicitFallback
    )

    if ($ExplicitFallback.Count -gt 0) {
        $labels = New-Object System.Collections.Generic.List[string]
        foreach ($value in $ExplicitFallback) {
            foreach ($label in ($value -split ",")) {
                $trimmed = $label.Trim()
                if (-not [string]::IsNullOrWhiteSpace($trimmed)) {
                    [void] $labels.Add($trimmed)
                }
            }
        }
        return @($labels)
    }

    if ($Declaration.fallback -and @($Declaration.fallback).Count -gt 0) {
        return @($Declaration.fallback)
    }

    return @("go", "zen")
}

function New-Candidate {
    param(
        [Parameter(Mandatory = $true)]
        [string] $ModelRef,

        [Parameter(Mandatory = $true)]
        [string] $Variant,

        [Parameter(Mandatory = $true)]
        [string] $Origin,

        [string] $Label = ""
    )

    return [pscustomobject] @{
        ModelRef = $ModelRef
        Variant = $Variant
        Origin = $Origin
        Label = $Label
    }
}

function Add-Candidate {
    param(
        [System.Collections.Generic.List[object]] $Candidates,

        [Parameter(Mandatory = $true)]
        [object] $Candidate
    )

    foreach ($existing in $Candidates) {
        if ($existing.ModelRef -eq $Candidate.ModelRef -and $existing.Variant -eq $Candidate.Variant) {
            return
        }
    }
    [void] $Candidates.Add($Candidate)
}

function Write-Evidence {
    param(
        [Parameter(Mandatory = $true)]
        [object] $Event,

        [string] $Path
    )

    if ($NoEvidence) {
        return
    }

    if ([string]::IsNullOrWhiteSpace($Path)) {
        throw "Para registrar evidencia, indica -Feature o -EvidencePath. Usa -NoEvidence solo en validaciones sin ejecucion."
    }

    $parent = Split-Path -Parent $Path
    if (-not [string]::IsNullOrWhiteSpace($parent) -and -not (Test-Path -LiteralPath $parent -PathType Container)) {
        New-Item -ItemType Directory -Path $parent | Out-Null
    }

    $json = $Event | ConvertTo-Json -Depth 50 -Compress
    $writer = New-Object System.IO.StreamWriter($Path, $true, (New-Object System.Text.UTF8Encoding($false)))
    try {
        $writer.WriteLine($json)
    }
    finally {
        $writer.Dispose()
    }
}

try {
    if ($UseLiveCatalog) {
        if ($env:AGENTIC_TEST_MODE -eq "1") {
            throw "AGENTIC_TEST_MODE impide consultas de catalogo o llamadas que puedan consumir creditos reales."
        }
        throw "La interfaz minima del punto 1 no consulta catalogos remotos. Actualiza .agentic/models.json tras revisar disponibilidad oficial."
    }

    $root = Get-RepositoryRoot
    $models = Read-JsonFile (Join-Path $root ".agentic/models.json")

    $roleProperty = $models.roles.PSObject.Properties[$Role]
    if ($null -eq $roleProperty) {
        throw "Rol desconocido: $Role"
    }
    $roleConfig = $roleProperty.Value

    if ([string]::IsNullOrWhiteSpace($Stage)) {
        $Stage = $Role
    }

    if ([string]::IsNullOrWhiteSpace($RunFile) -and -not [string]::IsNullOrWhiteSpace($Feature)) {
        $RunFile = Join-Path $root ("runs/$Feature/run.yaml" -replace '/', [System.IO.Path]::DirectorySeparatorChar)
    }
    elseif (-not [string]::IsNullOrWhiteSpace($RunFile) -and -not [System.IO.Path]::IsPathRooted($RunFile)) {
        $RunFile = Join-Path $root $RunFile
    }

    $declaration = [pscustomobject] @{
        model = "default"
        variant = "default"
        fallback = @()
    }
    if (-not [string]::IsNullOrWhiteSpace($RunFile)) {
        $declaration = ConvertFrom-MinimalRunYaml -Path $RunFile
    }

    $selectedModel = $roleConfig.default.model
    $modelOrigin = "role-default"
    if ($declaration.model -and $declaration.model -ne "default") {
        $selectedModel = $declaration.model
        $modelOrigin = "run-yaml"
    }
    if (-not [string]::IsNullOrWhiteSpace($Model)) {
        $selectedModel = $Model
        $modelOrigin = "explicit-parameter"
    }

    $selectedVariant = $roleConfig.default.variant
    $variantOrigin = "role-default"
    if ($declaration.variant -and $declaration.variant -ne "default") {
        $selectedVariant = $declaration.variant
        $variantOrigin = "run-yaml"
    }
    if (-not [string]::IsNullOrWhiteSpace($Variant)) {
        $selectedVariant = $Variant
        $variantOrigin = "explicit-parameter"
    }

    if (@($models.validVariants) -notcontains $selectedVariant) {
        throw "Variante invalida o no autorizada: $selectedVariant"
    }

    $primary = Assert-ModelAllowed -Models $models -ModelRef $selectedModel
    $selectedForEvidence = $primary
    $selectionOriginForEvidence = $modelOrigin
    $fallbackLabels = Get-FallbackLabels -Declaration $declaration -ExplicitFallback $Fallback
    $candidates = New-Object System.Collections.Generic.List[object]
    Add-Candidate -Candidates $candidates -Candidate (New-Candidate -ModelRef $selectedModel -Variant $selectedVariant -Origin $modelOrigin)

    foreach ($label in $fallbackLabels) {
        $fallbackMatch = $null
        foreach ($candidate in @($roleConfig.fallback)) {
            if ($candidate.label -eq $label) {
                $fallbackMatch = $candidate
                break
            }
        }

        if ($null -eq $fallbackMatch) {
            throw "Fallback no autorizado para ${Role}: $label"
        }

        if (@($models.validVariants) -notcontains $fallbackMatch.variant) {
            throw "Variante invalida en fallback $label para ${Role}: $($fallbackMatch.variant)"
        }

        $allowedCandidate = Assert-ModelAllowed -Models $models -ModelRef $fallbackMatch.model
        if ($allowedCandidate.ProviderConfig.requiresExplicitFallback -and @($fallbackLabels) -notcontains $label) {
            throw "El proveedor $($allowedCandidate.Provider) requiere fallback explicito."
        }

        Add-Candidate -Candidates $candidates -Candidate (New-Candidate -ModelRef $fallbackMatch.model -Variant $fallbackMatch.variant -Origin "fallback:$label" -Label $label)
    }

    $unavailable = New-Object System.Collections.Generic.List[string]
    $chosen = $null
    foreach ($candidate in $candidates) {
        if (-not [string]::IsNullOrWhiteSpace($FailureReason)) {
            $modelToSkip = if ([string]::IsNullOrWhiteSpace($FailedModel)) { $selectedModel } else { $FailedModel }
            if ($candidate.ModelRef -eq $modelToSkip) {
                [void] $unavailable.Add("$($candidate.ModelRef): $FailureReason")
                continue
            }
        }

        $allowed = Assert-ModelAllowed -Models $models -ModelRef $candidate.ModelRef
        if (-not (Test-ProviderCredentials -ProviderConfig $allowed.ProviderConfig)) {
            $envNames = @($allowed.ProviderConfig.credentialEnv) -join ", "
            [void] $unavailable.Add("$($candidate.ModelRef): faltan credenciales o marca de disponibilidad ($envNames)")
            continue
        }

        $chosen = [pscustomobject] @{
            Candidate = $candidate
            Allowed = $allowed
        }
        break
    }

    if ($null -eq $chosen) {
        $details = if ($unavailable.Count -gt 0) { " Detalle: $($unavailable -join '; ')" } else { "" }
        throw "No hay modelos disponibles con el fallback autorizado para $Role.$details"
    }

    $stopwatch.Stop()
    $fallbackApplied = $chosen.Candidate.ModelRef -ne $selectedModel -or -not [string]::IsNullOrWhiteSpace($FailureReason)
    $event = [ordered] @{
        execution_id = [guid]::NewGuid().ToString("N")
        feature = if ([string]::IsNullOrWhiteSpace($Feature)) { "ad-hoc" } else { $Feature }
        agent = $Role
        stage = $Stage
        provider = $chosen.Allowed.Provider
        model = $chosen.Allowed.Model
        model_ref = $chosen.Allowed.Ref
        variant = $chosen.Candidate.Variant
        model_selection_origin = $chosen.Candidate.Origin
        variant_selection_origin = $variantOrigin
        fallback_applied = [bool] $fallbackApplied
        fallback_from = if ($fallbackApplied) { if ([string]::IsNullOrWhiteSpace($FailedModel)) { $selectedModel } else { $FailedModel } } else { $null }
        fallback_reason = if ([string]::IsNullOrWhiteSpace($FailureReason)) { $null } else { $FailureReason }
        date = (Get-Date).ToUniversalTime().ToString("o")
        duration_ms = [int] $stopwatch.ElapsedMilliseconds
        result = "resolved"
        cost = $null
        opencode = [ordered] @{
            model = $chosen.Allowed.Model
            variant = $chosen.Candidate.Variant
            args = @("--model", $chosen.Allowed.Model)
        }
    }

    if ([string]::IsNullOrWhiteSpace($EvidencePath) -and -not [string]::IsNullOrWhiteSpace($Feature)) {
        $EvidencePath = Join-Path $root ("runs/$Feature/model-routing.jsonl" -replace '/', [System.IO.Path]::DirectorySeparatorChar)
    }
    elseif (-not [string]::IsNullOrWhiteSpace($EvidencePath) -and -not [System.IO.Path]::IsPathRooted($EvidencePath)) {
        $EvidencePath = Join-Path $root $EvidencePath
    }

    Write-Evidence -Event ([pscustomobject] $event) -Path $EvidencePath
    $event | ConvertTo-Json -Depth 50
    exit 0
}
catch {
    $stopwatch.Stop()
    $failureEvent = [ordered] @{
        execution_id = [guid]::NewGuid().ToString("N")
        feature = if ([string]::IsNullOrWhiteSpace($Feature)) { "ad-hoc" } else { $Feature }
        agent = $Role
        stage = if ([string]::IsNullOrWhiteSpace($Stage)) { $Role } else { $Stage }
        provider = if ($selectedForEvidence) { $selectedForEvidence.Provider } else { $null }
        model = if ($selectedForEvidence) { $selectedForEvidence.Model } else { $Model }
        model_ref = if ($selectedForEvidence) { $selectedForEvidence.Ref } else { $Model }
        variant = $Variant
        model_selection_origin = $selectionOriginForEvidence
        fallback_applied = -not [string]::IsNullOrWhiteSpace($FailureReason)
        fallback_from = if ([string]::IsNullOrWhiteSpace($FailedModel)) { $null } else { $FailedModel }
        fallback_reason = if ([string]::IsNullOrWhiteSpace($FailureReason)) { $_.Exception.Message } else { $FailureReason }
        date = (Get-Date).ToUniversalTime().ToString("o")
        duration_ms = [int] $stopwatch.ElapsedMilliseconds
        result = "failed"
        error = $_.Exception.Message
        cost = $null
    }

    if ([string]::IsNullOrWhiteSpace($EvidencePath) -and -not [string]::IsNullOrWhiteSpace($Feature)) {
        $rootForFailure = Get-RepositoryRoot
        $EvidencePath = Join-Path $rootForFailure ("runs/$Feature/model-routing.jsonl" -replace '/', [System.IO.Path]::DirectorySeparatorChar)
    }
    elseif (-not [string]::IsNullOrWhiteSpace($EvidencePath) -and -not [System.IO.Path]::IsPathRooted($EvidencePath)) {
        $rootForFailure = Get-RepositoryRoot
        $EvidencePath = Join-Path $rootForFailure $EvidencePath
    }

    if (-not $NoEvidence -and -not [string]::IsNullOrWhiteSpace($EvidencePath)) {
        Write-Evidence -Event ([pscustomobject] $failureEvent) -Path $EvidencePath
    }

    [Console]::Error.WriteLine($_.Exception.Message)
    exit 1
}
