$ErrorActionPreference = "Stop"

function Get-McpCatalog {
    param([string] $Path = "")
    if ([string]::IsNullOrWhiteSpace($Path)) { $Path = Join-Path $PSScriptRoot "../.agentic/mcp.json" }
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { throw "No existe el catalogo MCP: $Path" }
    try { $catalog = Get-Content -LiteralPath $Path -Raw -Encoding UTF8 | ConvertFrom-Json }
    catch { throw "Catalogo MCP invalido: JSON no valido." }
    if ($catalog.schemaVersion -ne 1 -or $null -eq $catalog.servers) { throw "Catalogo MCP invalido: schemaVersion/servers." }
    foreach ($property in $catalog.servers.PSObject.Properties) {
        $server = $property.Value
        foreach ($field in @("type", "capability", "mode", "risk", "permissions", "optional", "load")) {
            if ($null -eq $server.$field) { throw "Catalogo MCP invalido: '$($property.Name)' falta '$field'." }
        }
        if ($server.load -ne "on-demand") { throw "Catalogo MCP invalido: '$($property.Name)' debe usar load=on-demand." }
        if ($server.mode -notin @("read-only", "write", "action")) { throw "Catalogo MCP invalido: modo no soportado en '$($property.Name)'." }
        if ($server.type -notin @("local", "remote")) { throw "Catalogo MCP invalido: tipo no soportado en '$($property.Name)'." }
    }
    return $catalog
}

function Get-McpCapabilityDecision {
    param(
        [Parameter(Mandatory = $true)][string] $Server,
        [Parameter(Mandatory = $true)][string] $Scope,
        [ValidateSet("LIGHT", "STANDARD", "FULL")][string] $Profile = "LIGHT",
        [string] $Operation = "read",
        [string] $AuthorizationPath = "",
        [hashtable] $Environment = @{},
        [string] $CatalogPath = ""
    )
    . (Join-Path $PSScriptRoot "security-policy.ps1")
    $catalog = Get-McpCatalog -Path $CatalogPath
    $entry = $catalog.servers.PSObject.Properties[$Server]
    if ($null -eq $entry) { return [pscustomobject]@{ Decision = "FALLBACK"; Reason = "capability_not_configured"; Server = $Server } }
    $definition = $entry.Value
    $capability = if ($definition.mode -eq "read-only") { "NETWORK_READ" } else { "EXTERNAL_WRITE" }
    $security = Get-SecurityDecision -Profile $Profile -Capability $capability
    if ($security.Decision -ne "ALLOW") {
        if ($security.Decision -eq "GATE" -and [string]::IsNullOrWhiteSpace($AuthorizationPath)) { return [pscustomobject]@{ Decision = "DENY"; Reason = "authorization_required"; Server = $Server } }
        if ($AuthorizationPath) { Assert-ScopedAuthorization -Path $AuthorizationPath -ExpectedScope $Scope -ExpectedAction $Operation }
    }
    if ($definition.mode -ne "read-only" -and $Operation -eq "read") { return [pscustomobject]@{ Decision = "DENY"; Reason = "operation_mismatch"; Server = $Server } }
    if ($definition.requirements.secretEnv -and -not $Environment.ContainsKey($definition.requirements.secretEnv)) {
        if ($definition.optional) { return [pscustomobject]@{ Decision = "FALLBACK"; Reason = "secret_missing"; Server = $Server } }
        return [pscustomobject]@{ Decision = "BLOCKED"; Reason = "secret_missing"; Server = $Server }
    }
    return [pscustomobject]@{ Decision = "ALLOW"; Reason = "scoped_capability"; Server = $Server; Scope = $Scope; Operation = $Operation }
}

if ($MyInvocation.InvocationName -ne '.') { $catalog = Get-McpCatalog; Write-Output ("mcp-catalog: valid ({0} server(s), on-demand)" -f @($catalog.servers.PSObject.Properties).Count) }
