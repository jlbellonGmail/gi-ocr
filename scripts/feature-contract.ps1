$ErrorActionPreference = "Stop"

function Get-RepositoryRoot {
    $root = (& git rev-parse --show-toplevel) -join "`n"
    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($root)) {
        throw "No pude detectar la raiz del repositorio Git."
    }

    return [System.IO.Path]::GetFullPath($root.Trim())
}

function Get-GitCommonDir {
    $commonDir = (& git rev-parse --git-common-dir) -join "`n"
    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($commonDir)) {
        throw "No pude detectar el git-dir real del repositorio."
    }

    $commonDir = $commonDir.Trim()
    if (-not [System.IO.Path]::IsPathRooted($commonDir)) {
        $commonDir = Join-Path (Get-RepositoryRoot) $commonDir
    }

    $commonDir = [System.IO.Path]::GetFullPath($commonDir)
    if (-not (Test-Path -LiteralPath $commonDir -PathType Container)) {
        throw "El git-dir real no es un directorio accesible: $commonDir"
    }

    return $commonDir
}

function Get-FeatureStateDir {
    $stateDir = Join-Path (Get-GitCommonDir) "feature-reconcilers"
    if (-not (Test-Path -LiteralPath $stateDir -PathType Container)) {
        New-Item -ItemType Directory -Path $stateDir | Out-Null
    }

    return $stateDir
}

function Get-FeatureInfo {
    param(
        [Parameter(Mandatory = $true)]
        [string] $Slug,

        [string] $Title = ""
    )

    if ($Slug -notmatch "^(?<number>[0-9]{2})-(?<docSlug>[a-z0-9]+(?:-[a-z0-9]+)*)$") {
        throw "Slug invalido '$Slug'. Debe tener formato NN-slug-en-minusculas."
    }

    $docSlug = $Matches["docSlug"]
    if ([string]::IsNullOrWhiteSpace($Title)) {
        $Title = ($docSlug -split "-" | ForEach-Object {
            if ($_.Length -eq 0) { $_ } else { $_.Substring(0, 1).ToUpperInvariant() + $_.Substring(1) }
        }) -join " "
    }

    return [pscustomobject]@{
        Slug = $Slug
        Number = $Matches["number"]
        DocSlug = $docSlug
        Title = $Title
        RunDir = "runs/$Slug"
        TechnicalDoc = "docs/tecnica/$docSlug.md"
        UserDoc = "docs/usuario/$docSlug.md"
        TechnicalIndex = "docs/tecnica/index.md"
        UserIndex = "docs/usuario/index.md"
        Decision = "runs/$Slug/decision.md"
    }
}

function Assert-NonEmptyFile {
    param(
        [Parameter(Mandatory = $true)]
        [string] $Path
    )

    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "Falta el archivo requerido: $Path"
    }

    $content = Get-Content -LiteralPath $Path -Raw -Encoding UTF8
    if ([string]::IsNullOrWhiteSpace($content)) {
        throw "El archivo requerido esta vacio: $Path"
    }
}

function Get-FirstExistingArtifact {
    param(
        [Parameter(Mandatory = $true)]
        [string] $Directory,

        [Parameter(Mandatory = $true)]
        [string] $Pattern
    )

    if (-not (Test-Path -LiteralPath $Directory -PathType Container)) {
        return $null
    }

    return Get-ChildItem -LiteralPath $Directory -Filter $Pattern -File |
        Sort-Object Name |
        Select-Object -First 1
}

function Assert-IndexLink {
    param(
        [Parameter(Mandatory = $true)]
        [string] $IndexPath,

        [Parameter(Mandatory = $true)]
        [string] $TargetPath,

        [Parameter(Mandatory = $true)]
        [string] $Title
    )

    if (-not (Test-Path -LiteralPath $TargetPath -PathType Leaf)) {
        throw "No existe el destino requerido por el indice: $TargetPath"
    }

    if (-not (Test-Path -LiteralPath $IndexPath -PathType Leaf)) {
        throw "No existe el indice requerido: $IndexPath"
    }

    $targetName = Split-Path -Leaf $TargetPath
    $content = Get-Content -LiteralPath $IndexPath -Raw -Encoding UTF8
    $escapedTarget = [regex]::Escape($targetName)
    $targetMatches = [regex]::Matches($content, "\]\($escapedTarget\)")

    if ($targetMatches.Count -ne 1) {
        throw "El indice $IndexPath debe contener exactamente un enlace a $targetName. Encontrados: $($targetMatches.Count)."
    }

    $expectedLine = "- [$Title]($targetName)"
    $escapedExpectedLine = [regex]::Escape($expectedLine)
    if ($content -notmatch "(?m)^$escapedExpectedLine\s*$") {
        throw "El indice $IndexPath contiene $targetName, pero no con el enlace exacto '$expectedLine'."
    }
}

function Update-DocsIndex {
    param(
        [Parameter(Mandatory = $true)]
        [string] $IndexPath,

        [Parameter(Mandatory = $true)]
        [string] $TargetPath,

        [Parameter(Mandatory = $true)]
        [string] $Title
    )

    if (-not (Test-Path -LiteralPath $TargetPath -PathType Leaf)) {
        throw "No existe el destino requerido por el indice: $TargetPath"
    }

    if (-not (Test-Path -LiteralPath $IndexPath -PathType Leaf)) {
        throw "No existe el indice requerido: $IndexPath"
    }

    $targetName = Split-Path -Leaf $TargetPath
    $expectedLine = "- [$Title]($targetName)"
    $content = [System.IO.File]::ReadAllText((Resolve-Path -LiteralPath $IndexPath).Path, [System.Text.Encoding]::UTF8)
    $escapedTarget = [regex]::Escape($targetName)
    $targetLines = [regex]::Matches($content, "(?m)^- \[[^\]]+\]\($escapedTarget\)\s*$")
    if ($targetLines.Count -gt 1) {
        throw "Coincidencia ambigua: $IndexPath contiene mas de un enlace a $targetName."
    }

    if ($targetLines.Count -eq 1) {
        if ($targetLines[0].Value.TrimEnd() -ne $expectedLine) {
            throw "Coincidencia ambigua: $IndexPath ya enlaza $targetName con otro titulo: '$($targetLines[0].Value.Trim())'."
        }
        return $false
    }

    $escapedTitle = [regex]::Escape($Title)
    $sameTitleOtherTarget = [regex]::Matches($content, "(?m)^- \[$escapedTitle\]\((?!$escapedTarget\))[^)]+\)\s*$")
    if ($sameTitleOtherTarget.Count -gt 0) {
        throw "Coincidencia ambigua: $IndexPath ya contiene el titulo '$Title' apuntando a otro destino."
    }

    $separator = if ($content.EndsWith("`r`n") -or $content.EndsWith("`n")) { "" } else { [Environment]::NewLine }
    Add-Content -LiteralPath $IndexPath -Value ($separator + $expectedLine) -Encoding UTF8
    return $true
}

function New-DecisionFile {
    param(
        [Parameter(Mandatory = $true)]
        [string] $Slug,

        [Parameter(Mandatory = $true)]
        [string] $Title,

        [Parameter(Mandatory = $true)]
        [string[]] $Decisions
    )

    $info = Get-FeatureInfo -Slug $Slug -Title $Title
    if (-not (Test-Path -LiteralPath $info.RunDir -PathType Container)) {
        New-Item -ItemType Directory -Path $info.RunDir | Out-Null
    }

    if (Test-Path -LiteralPath $info.Decision -PathType Leaf) {
        return $false
    }

    $lines = New-Object System.Collections.Generic.List[string]
    [void] $lines.Add("# Decision: $Slug - $Title")
    [void] $lines.Add("")
    [void] $lines.Add("## Estado")
    [void] $lines.Add("")
    [void] $lines.Add("MERGE aprobado por evidencias del circuito agéntico.")
    [void] $lines.Add("")
    [void] $lines.Add("## Evidencias revisadas")
    [void] $lines.Add("")
    [void] $lines.Add("- ``$($info.RunDir)/spec.md``")
    [void] $lines.Add("- ``$($info.RunDir)/audit-1.md``")
    [void] $lines.Add("- ``$($info.RunDir)/test-report-1.md``")
    [void] $lines.Add("")
    [void] $lines.Add("## Decisiones demostrables")
    [void] $lines.Add("")
    foreach ($decision in $Decisions) {
        [void] $lines.Add("- $decision")
    }
    [void] $lines.Add("")
    [void] $lines.Add("## Resultado")
    [void] $lines.Add("")
    [void] $lines.Add("La feature queda apta para integrarse/cerrarse cuando GitHub confirme merge contra ``develop`` y el cierre automatico marque ``ROADMAP.md``.")
    $content = $lines -join [Environment]::NewLine

    [System.IO.File]::WriteAllText(
        (Join-Path (Get-Location).Path $info.Decision),
        $content + [Environment]::NewLine,
        (New-Object System.Text.UTF8Encoding($false))
    )
    return $true
}

function Get-FeatureContractStatus {
    <#
        Version no-throwing de Assert-FeatureContract: evalua el contrato
        completo de artefactos de una feature y devuelve TODOS los
        problemas encontrados en una sola corrida (no aborta en el primer
        faltante). Assert-FeatureContract es un wrapper delgado sobre esta
        funcion que preserva el comportamiento externo previo (throw en el
        primer problema detectado, mismo texto de mensaje).
    #>
    param(
        [Parameter(Mandatory = $true)]
        [string] $Slug,

        [string] $Title = "",

        [switch] $RequireReadyRoadmap
    )

    $info = Get-FeatureInfo -Slug $Slug -Title $Title
    $problems = New-Object System.Collections.Generic.List[string]

    foreach ($requiredPath in @(
        $info.Decision,
        "$($info.RunDir)/spec.md",
        $info.TechnicalDoc,
        $info.UserDoc
    )) {
        try {
            Assert-NonEmptyFile $requiredPath
        }
        catch {
            [void] $problems.Add($_.Exception.Message)
        }
    }

    $audit = Get-FirstExistingArtifact -Directory $info.RunDir -Pattern "audit-*.md"
    if ($null -eq $audit) {
        [void] $problems.Add("Falta al menos un audit-N.md en $($info.RunDir).")
    }
    else {
        try { Assert-NonEmptyFile $audit.FullName }
        catch { [void] $problems.Add($_.Exception.Message) }
    }

    $testReport = Get-FirstExistingArtifact -Directory $info.RunDir -Pattern "test-report-*.md"
    if ($null -eq $testReport) {
        [void] $problems.Add("Falta al menos un test-report-N.md en $($info.RunDir).")
    }
    else {
        try { Assert-NonEmptyFile $testReport.FullName }
        catch { [void] $problems.Add($_.Exception.Message) }
    }

    try { Assert-IndexLink -IndexPath $info.TechnicalIndex -TargetPath $info.TechnicalDoc -Title $info.Title }
    catch { [void] $problems.Add($_.Exception.Message) }

    try { Assert-IndexLink -IndexPath $info.UserIndex -TargetPath $info.UserDoc -Title $info.Title }
    catch { [void] $problems.Add($_.Exception.Message) }

    if ($RequireReadyRoadmap) {
        try {
            $roadmap = Get-Content -LiteralPath "ROADMAP.md" -Raw -Encoding UTF8
            $escapedSlug = [regex]::Escape($Slug)
            $readyCount = [regex]::Matches($roadmap, "(?m)^- \[-\] $escapedSlug(?=\s|$).*").Count
            $doneCount = [regex]::Matches($roadmap, "(?m)^- \[x\] $escapedSlug(?=\s|$).*").Count
            if ($doneCount -gt 0) {
                [void] $problems.Add("$Slug ya figura como [x]. No se puede preparar PR despues del cierre.")
            }
            elseif ($readyCount -ne 1) {
                [void] $problems.Add("ROADMAP.md debe contener exactamente una entrada READY_FOR_PR para $Slug. Encontradas: $readyCount.")
            }
        }
        catch {
            [void] $problems.Add($_.Exception.Message)
        }
    }

    return [pscustomobject]@{
        Slug = $Slug
        Info = $info
        Problems = $problems.ToArray()
        IsComplete = ($problems.Count -eq 0)
    }
}

function Assert-FeatureContract {
    param(
        [Parameter(Mandatory = $true)]
        [string] $Slug,

        [string] $Title = "",

        [switch] $RequireReadyRoadmap
    )

    $status = Get-FeatureContractStatus -Slug $Slug -Title $Title -RequireReadyRoadmap:$RequireReadyRoadmap
    if (-not $status.IsComplete) {
        throw ($status.Problems -join [Environment]::NewLine)
    }
}

function Find-GitHubCliPath {
    <#
        Version no-throwing de la deteccion de 'gh': devuelve $null si no
        esta disponible, en vez de lanzar excepcion. Get-GitHubCliPath
        (usada por ready-for-pr.ps1/wait-pr-ci.ps1/close-feature.ps1 una
        vez superado el diagnostico) sigue lanzando para no cambiar su
        comportamiento externo.
    #>
    $command = Get-Command gh -ErrorAction SilentlyContinue
    if ($command) {
        return $command.Source
    }

    $defaultPath = Join-Path $env:ProgramFiles "GitHub CLI\gh.exe"
    if (Test-Path -LiteralPath $defaultPath) {
        return $defaultPath
    }

    return $null
}

function Get-GitHubCliPath {
    $path = Find-GitHubCliPath
    if ($path) {
        return $path
    }

    throw "GitHub CLI (gh) no esta disponible. Instalalo y autenticalo para crear/verificar PRs automaticamente."
}

function Find-PowerShellPath {
    <#
        Version no-throwing de la deteccion de PowerShell (powershell.exe o
        pwsh): devuelve $null si ninguna esta disponible.
    #>
    $pwsh = Get-Command pwsh -ErrorAction SilentlyContinue
    if ($pwsh) {
        return $pwsh.Source
    }

    $windowsPowerShell = Get-Command powershell.exe -ErrorAction SilentlyContinue
    if ($windowsPowerShell) {
        return $windowsPowerShell.Source
    }

    return $null
}

function Get-PowerShellPath {
    $path = Find-PowerShellPath
    if ($path) {
        return $path
    }

    throw "PowerShell no esta disponible para iniciar el reconciliador local."
}

function Get-ToolchainDiagnostics {
    <#
        Diagnostico generico de herramientas locales, compartido por
        preflight.ps1 (modo sin -Slug) y ready-for-pr.ps1 (criterio 15):
        git, gh (binario + autenticacion), PowerShell, Python y .venv.
        NO evalua el estado de 'develop' ni la matriz worktree/rama/ROADMAP
        de una feature puntual (eso vive exclusivamente en preflight.ps1,
        ver "Nota de alcance" del spec de 04-cierre-operativo-circuito-agentico).
        Devuelve un arreglo de pscustomobject { Tool; Severity; Message; Action }
        con Severity en OK | BLOCKING.
    #>
    $results = New-Object System.Collections.Generic.List[object]

    function Add-ToolResult {
        param([string] $Tool, [string] $Severity, [string] $Message, [string] $Action = "")
        $results.Add([pscustomobject]@{
            Tool = $Tool
            Severity = $Severity
            Message = $Message
            Action = $Action
        })
    }

    $gitCmd = Get-Command git -ErrorAction SilentlyContinue
    if (-not $gitCmd) {
        Add-ToolResult "git" "BLOCKING" "git no esta disponible en PATH." "Instala Git (https://git-scm.com/) y agregalo al PATH."
    }
    else {
        Add-ToolResult "git" "OK" "git disponible en $($gitCmd.Source)."
    }

    $ghPath = Find-GitHubCliPath
    if (-not $ghPath) {
        Add-ToolResult "gh" "BLOCKING" "GitHub CLI (gh) no esta instalado o no esta en PATH." "Instala GitHub CLI (https://cli.github.com/) y agregalo al PATH."
    }
    else {
        $previousEap = $ErrorActionPreference
        $ErrorActionPreference = "Continue"
        $authOutput = & $ghPath "auth" "status" 2>&1
        $authExit = $LASTEXITCODE
        $ErrorActionPreference = $previousEap
        $authText = (($authOutput | ForEach-Object { $_.ToString() }) -join "`n").Trim()
        if ($authExit -ne 0) {
            Add-ToolResult "gh" "BLOCKING" "gh esta instalado ($ghPath) pero no esta autenticado (o la sesion expiro): $authText" "Corre 'gh auth login' (o 'gh auth refresh' si la sesion expiro) para autenticar GitHub CLI."
        }
        else {
            Add-ToolResult "gh" "OK" "gh disponible en $ghPath y autenticado."
        }
    }

    $psPath = Find-PowerShellPath
    if (-not $psPath) {
        Add-ToolResult "PowerShell" "BLOCKING" "No se encontro powershell.exe ni pwsh en PATH." "Instala PowerShell 7 (https://aka.ms/powershell) o verifica que powershell.exe este en PATH."
    }
    else {
        Add-ToolResult "PowerShell" "OK" "PowerShell disponible en $psPath."
    }

    $repoRoot = $null
    try { $repoRoot = Get-RepositoryRoot } catch { $repoRoot = $null }
    $requirementsPath = $null
    if ($repoRoot) {
        $requirementsPath = Join-Path $repoRoot "backend/requirements.txt"
    }

    if ($requirementsPath -and (Test-Path -LiteralPath $requirementsPath -PathType Leaf)) {
        $pythonCmd = Get-Command python -ErrorAction SilentlyContinue
        if (-not $pythonCmd) {
            $pythonCmd = Get-Command python3 -ErrorAction SilentlyContinue
        }

        if (-not $pythonCmd) {
            Add-ToolResult "python" "BLOCKING" "python no esta disponible en PATH." "Instala Python 3.12+ (https://www.python.org/) y agregalo al PATH."
        }
        else {
            $versionText = ""
            $versionExit = 1
            try {
                $previousEap = $ErrorActionPreference
                $ErrorActionPreference = "Continue"
                $versionRaw = & $pythonCmd.Source "--version" 2>&1
                $versionExit = $LASTEXITCODE
                $ErrorActionPreference = $previousEap
                $versionText = (($versionRaw | ForEach-Object { $_.ToString() }) -join " ").Trim()
            }
            catch {
                $ErrorActionPreference = $previousEap
                $versionExit = 1
                $versionText = $_.Exception.Message
            }
            if ($versionExit -ne 0 -or $versionText -notmatch "(?<major>\d+)\.(?<minor>\d+)") {
                Add-ToolResult "python" "BLOCKING" "No se pudo determinar la version de python ($versionText)." "Verifica la instalacion de Python (>= 3.12)."
            }
            else {
                $major = [int]$Matches["major"]
                $minor = [int]$Matches["minor"]
                if ($major -gt 3 -or ($major -eq 3 -and $minor -ge 12)) {
                    Add-ToolResult "python" "OK" "python $versionText disponible en $($pythonCmd.Source)."
                }
                else {
                    Add-ToolResult "python" "BLOCKING" "python instalado es $versionText, se requiere >= 3.12." "Actualiza Python a 3.12 o superior."
                }
            }
        }

        $venvDir = Join-Path $repoRoot ".venv"
        $venvPythonWindows = Join-Path $venvDir "Scripts/python.exe"
        $venvPythonPosix = Join-Path $venvDir "bin/python"
        $venvPython = if (Test-Path -LiteralPath $venvPythonWindows -PathType Leaf) { $venvPythonWindows } else { $venvPythonPosix }

        if (-not (Test-Path -LiteralPath $venvDir -PathType Container)) {
            Add-ToolResult ".venv" "BLOCKING" ".venv no existe en $repoRoot." "Crea el entorno virtual: python -m venv .venv && .venv/Scripts/pip install -r backend/requirements.txt"
        }
        elseif (-not (Test-Path -LiteralPath $venvPython -PathType Leaf)) {
            Add-ToolResult ".venv" "BLOCKING" ".venv existe pero no tiene un interprete de Python valido ($venvPython)." "El entorno virtual esta corrupto: borralo y recrealo (python -m venv .venv)."
        }
        else {
            $freezeExit = 1
            $freezeOutput = @()
            try {
                $previousEap = $ErrorActionPreference
                $ErrorActionPreference = "Continue"
                $freezeOutput = & $venvPython "-m" "pip" "freeze" 2>&1
                $freezeExit = $LASTEXITCODE
                $ErrorActionPreference = $previousEap
            }
            catch {
                $ErrorActionPreference = $previousEap
                $freezeExit = 1
                $freezeOutput = @()
            }

            if ($freezeExit -ne 0) {
                Add-ToolResult ".venv" "BLOCKING" ".venv existe pero el interprete no arranca correctamente ($venvPython)." "El entorno virtual esta corrupto: borralo y recrealo (python -m venv .venv && .venv/Scripts/pip install -r backend/requirements.txt)."
            }
            else {
                $installedNames = @{}
                foreach ($rawLine in ($freezeOutput | ForEach-Object { $_.ToString() })) {
                    $line = $rawLine.Trim()
                    if ($line -match "^(?<name>[A-Za-z0-9_.\-]+)\s*(==|>=|<=|~=|!=|@)") {
                        $installedNames[$Matches["name"].ToLowerInvariant().Replace("_", "-")] = $true
                    }
                    elseif ($line -match "^(?<name>[A-Za-z0-9_.\-]+)$") {
                        $installedNames[$Matches["name"].ToLowerInvariant().Replace("_", "-")] = $true
                    }
                }

                $requiredNames = New-Object System.Collections.Generic.List[string]
                foreach ($reqLine in (Get-Content -LiteralPath $requirementsPath -Encoding UTF8)) {
                    $trimmed = $reqLine.Trim()
                    if ([string]::IsNullOrWhiteSpace($trimmed) -or $trimmed.StartsWith("#")) { continue }
                    if ($trimmed -match "^(?<name>[A-Za-z0-9_.\-]+)") {
                        [void] $requiredNames.Add($Matches["name"])
                    }
                }

                $missing = @()
                foreach ($name in $requiredNames) {
                    $normalized = $name.ToLowerInvariant().Replace("_", "-")
                    if (-not $installedNames.ContainsKey($normalized)) {
                        $missing += $name
                    }
                }

                if ($missing.Count -gt 0) {
                    Add-ToolResult ".venv" "BLOCKING" ".venv existe pero faltan paquetes de backend/requirements.txt: $($missing -join ', ')." "Instala las dependencias: .venv/Scripts/pip install -r backend/requirements.txt"
                }
                else {
                    Add-ToolResult ".venv" "OK" ".venv contiene los paquetes declarados en backend/requirements.txt."
                }
            }
        }
    }

    return $results.ToArray()
}

function Assert-ToolchainReady {
    <#
        Wrapper throwing sobre Get-ToolchainDiagnostics: usado por
        ready-for-pr.ps1 (criterio 15) al inicio de su ejecucion, antes de
        tocar ROADMAP.md. Aborta con el mismo tipo de mensaje accionable
        que preflight.ps1 reportaria para el/los problemas BLOCKING de
        herramientas.
    #>
    $results = Get-ToolchainDiagnostics
    $blocking = @($results | Where-Object { $_.Severity -eq "BLOCKING" })
    if ($blocking.Count -gt 0) {
        $lines = foreach ($item in $blocking) { "[$($item.Tool)] $($item.Message) Accion: $($item.Action)" }
        throw ("Diagnostico generico de herramientas fallo (correr 'preflight.ps1' para el detalle completo):" + [Environment]::NewLine + ($lines -join [Environment]::NewLine))
    }
}
