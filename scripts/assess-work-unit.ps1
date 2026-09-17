param(
 [string[]] $ChangedPath = @(),
 [string] $EvidencePath = "",
 [switch] $NoEvidence
)
$ErrorActionPreference = "Stop"
try {
 $root = (& git rev-parse --show-toplevel).Trim()
 if ($LASTEXITCODE -ne 0) { throw "No pude detectar la raiz del repositorio Git." }
 if ($ChangedPath.Count -eq 0) { throw "Falta evidencia: indica -ChangedPath con las rutas evaluadas." }
 $ChangedPath = @($ChangedPath | ForEach-Object { $_ -split ',' } | ForEach-Object { $_.Trim() } | Where-Object { $_ } | Sort-Object -Unique)
 if ($ChangedPath.Count -eq 0) { throw "La evidencia no contiene archivos cambiados." }
 $high = $false
 $score = 0
 $signals = New-Object System.Collections.Generic.List[object]
 foreach ($path in $ChangedPath) {
  $normalized = $path.Replace('\', '/').ToLowerInvariant()
  if ($normalized -match '(^|/)(security|auth|permissions?|secrets?)(/|\.|$)|(^|/)(migrations?|schema|database|data)(/|\.|$)') {
   $signal = New-Object PSObject
   $signal | Add-Member -MemberType NoteProperty -Name code -Value "sensitive-or-data"
   $signal | Add-Member -MemberType NoteProperty -Name level -Value "high"
   $signal | Add-Member -MemberType NoteProperty -Name weight -Value 5
   $signal | Add-Member -MemberType NoteProperty -Name reason -Value "Ruta sensible, permisos o datos."
   $high = $true
  } elseif ($normalized -match '(^|/)(\.github/workflows|scripts)(/|\.|$)|(^|/)(ci|cd|deploy|release)(/|\.|$)') {
   $signal = New-Object PSObject
   $signal | Add-Member -MemberType NoteProperty -Name code -Value "automation-or-governance"
   $signal | Add-Member -MemberType NoteProperty -Name level -Value "high"
   $signal | Add-Member -MemberType NoteProperty -Name weight -Value 4
   $signal | Add-Member -MemberType NoteProperty -Name reason -Value "Automatizacion o gobernanza puede afectar gates."
   $high = $true
  } elseif ($normalized -match '(^|/)(\.agentic|\.claude|\.opencode|\.codex)(/|\.|$)|(^|/)(config|configuration)(/|\.|$)') {
   $signal = New-Object PSObject
   $signal | Add-Member -MemberType NoteProperty -Name code -Value "agent-or-configuration"
   $signal | Add-Member -MemberType NoteProperty -Name level -Value "medium"
   $signal | Add-Member -MemberType NoteProperty -Name weight -Value 2
   $signal | Add-Member -MemberType NoteProperty -Name reason -Value "Configuracion del circuito."
  } elseif ($normalized -match '(^|/)(docs|tests?)(/|\.|$)|\.(md|rst|txt|json|ya?ml|toml)$') {
   $signal = New-Object PSObject
   $signal | Add-Member -MemberType NoteProperty -Name code -Value "documentation-or-test"
   $signal | Add-Member -MemberType NoteProperty -Name level -Value "low"
   $signal | Add-Member -MemberType NoteProperty -Name weight -Value 0
   $signal | Add-Member -MemberType NoteProperty -Name reason -Value "Documentacion, tests o configuracion declarativa."
  } else {
   $signal = New-Object PSObject
   $signal | Add-Member -MemberType NoteProperty -Name code -Value "implementation"
   $signal | Add-Member -MemberType NoteProperty -Name level -Value "medium"
   $signal | Add-Member -MemberType NoteProperty -Name weight -Value 2
   $signal | Add-Member -MemberType NoteProperty -Name reason -Value "Cambio de implementacion."
  }
  $score += $signal.weight
  [void]$signals.Add($signal)
 }
 if ($ChangedPath.Count -ge 10) { $score += 3; $high = $true }
 elseif ($ChangedPath.Count -ge 4) { $score += 1 }
 if ($high -or $score -ge 5) { $risk = "HIGH"; $depth = "FULL" }
 elseif ($score -ge 2) { $risk = "MEDIUM"; $depth = "STANDARD" }
 else { $risk = "LOW"; $depth = "LIGHT" }
 $result = New-Object PSObject
 $result | Add-Member -MemberType NoteProperty -Name schemaVersion -Value 1
 $result | Add-Member -MemberType NoteProperty -Name assessment -Value "ASSESS"
 $result | Add-Member -MemberType NoteProperty -Name deterministic -Value $true
 $result | Add-Member -MemberType NoteProperty -Name evaluatedAt -Value ((Get-Date).ToUniversalTime().ToString("o"))
 $result | Add-Member -MemberType NoteProperty -Name changedFiles -Value @($ChangedPath)
 $result | Add-Member -MemberType NoteProperty -Name fileCount -Value $ChangedPath.Count
 $result | Add-Member -MemberType NoteProperty -Name score -Value $score
 $result | Add-Member -MemberType NoteProperty -Name risk -Value $risk
 $result | Add-Member -MemberType NoteProperty -Name depth -Value $depth
 $result | Add-Member -MemberType NoteProperty -Name signals -Value $signals.ToArray()
 $result | Add-Member -MemberType NoteProperty -Name rationale -Value "Clasificacion determinista por rutas y amplitud; recomendacion auditable sin activar etapas ni relajar contratos v1."
 $result | Add-Member -MemberType NoteProperty -Name nextAction -Value "Aplicar profundidad recomendada en planificacion vigente y conservar este resultado como evidencia."
 if (-not $NoEvidence) {
  if ([string]::IsNullOrWhiteSpace($EvidencePath)) {
   $EvidencePath = Join-Path $root "runs/assess.jsonl"
  }
  if (-not [System.IO.Path]::IsPathRooted($EvidencePath)) {
   $EvidencePath = Join-Path $root $EvidencePath
  }
  $parent = Split-Path -Parent $EvidencePath
  if (-not (Test-Path -LiteralPath $parent -PathType Container)) {
   New-Item -ItemType Directory -Path $parent | Out-Null
  }
  $writer = New-Object System.IO.StreamWriter($EvidencePath, $true, (New-Object System.Text.UTF8Encoding($false)))
  try {
   $writer.WriteLine(($result | ConvertTo-Json -Depth 20 -Compress))
  } finally {
   $writer.Dispose()
  }
 }
 $result | ConvertTo-Json -Depth 20
 exit 0
} catch {
 [Console]::Error.WriteLine(("{0} (linea {1})" -f $_.Exception.Message, $_.InvocationInfo.ScriptLineNumber))
 exit 1
}
