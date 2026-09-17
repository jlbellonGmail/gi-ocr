$ErrorActionPreference = "Stop"

function Get-SecurityPolicy {
    param([string] $Path = "")
    if ([string]::IsNullOrWhiteSpace($Path)) { $Path = Join-Path $PSScriptRoot "../.agentic/security-policy.json" }
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { throw "No existe la politica de seguridad: $Path" }
    try { $policy = Get-Content -LiteralPath $Path -Raw -Encoding UTF8 | ConvertFrom-Json }
    catch { throw "Politica de seguridad invalida: JSON no valido." }
    if ($policy.schemaVersion -ne 1 -or $policy.defaultDecision -ne "deny") { throw "Politica de seguridad invalida: schema/defaultDecision." }
    foreach ($profile in @("LIGHT", "STANDARD", "FULL")) {
        if ($null -eq $policy.profiles.$profile) { throw "Politica de seguridad incompleta: falta perfil $profile." }
    }
    return $policy
}

function Get-SecurityDecision {
    param(
        [ValidateSet("LIGHT", "STANDARD", "FULL")][string] $Profile,
        [Parameter(Mandatory = $true)][ValidateSet("READ", "MODIFY_LOCAL", "EXECUTE", "NETWORK_READ", "EXTERNAL_WRITE", "GIT_WRITE", "REMOTE_WRITE", "MERGE", "DESTRUCTIVE", "SECRET_ACCESS")][string] $Capability,
        [string] $PolicyPath = ""
    )
    $policy = Get-SecurityPolicy -Path $PolicyPath
    $p = $policy.profiles.$Profile
    if (@($p.autonomous) -contains $Capability) { return [pscustomobject]@{ Decision = "ALLOW"; Reason = "autonomous"; Profile = $Profile; Capability = $Capability } }
    if (@($p.gated) -contains $Capability) { return [pscustomobject]@{ Decision = "GATE"; Reason = [string]$policy.rules.$Capability; Profile = $Profile; Capability = $Capability } }
    return [pscustomobject]@{ Decision = "DENY"; Reason = "not declared by profile"; Profile = $Profile; Capability = $Capability }
}

function Assert-ScopedAuthorization {
    param(
        [Parameter(Mandatory = $true)][string] $Path,
        [Parameter(Mandatory = $true)][string] $ExpectedScope,
        [string] $ExpectedAction = "",
        [string] $ExpectedBranch = "",
        [string] $ExpectedBase = ""
    )
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { throw "No existe la autorizacion scoped: $Path" }
    $text = Get-Content -LiteralPath $Path -Raw -Encoding UTF8
    foreach ($pair in @(@('decision','MERGE'), @('scope',$ExpectedScope))) {
        if ($text -notmatch "(?m)^$([regex]::Escape($pair[0])):\s*$([regex]::Escape($pair[1]))\s*$") { throw "Autorizacion invalida: falta $($pair[0]) scoped." }
    }
    if ($ExpectedAction -and $text -notmatch "(?m)^action:\s*$([regex]::Escape($ExpectedAction))\s*$") { throw "Autorizacion invalida: accion fuera de scope." }
    if ($ExpectedBranch -and $text -notmatch "(?m)^branch:\s*$([regex]::Escape($ExpectedBranch))\s*$") { throw "Autorizacion invalida: rama fuera de scope." }
    if ($ExpectedBase -and $text -notmatch "(?m)^base:\s*$([regex]::Escape($ExpectedBase))\s*$") { throw "Autorizacion invalida: base fuera de scope." }
    if ($text -match '(?im)(token|secret|password|api[_-]?key)\s*:') { throw "Autorizacion invalida: no admite secretos." }
    return $true
}

if ($MyInvocation.InvocationName -ne '.') {
    $policy = Get-SecurityPolicy
    if ($policy) { Write-Output "security-policy: valid" }
}
