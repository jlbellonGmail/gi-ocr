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

function Assert-FeatureContract {
    param(
        [Parameter(Mandatory = $true)]
        [string] $Slug,

        [string] $Title = "",

        [switch] $RequireReadyRoadmap
    )

    $info = Get-FeatureInfo -Slug $Slug -Title $Title
    Assert-NonEmptyFile $info.Decision
    Assert-NonEmptyFile "$($info.RunDir)/spec.md"
    Assert-NonEmptyFile $info.TechnicalDoc
    Assert-NonEmptyFile $info.UserDoc

    $audit = Get-FirstExistingArtifact -Directory $info.RunDir -Pattern "audit-*.md"
    if ($null -eq $audit) {
        throw "Falta al menos un audit-N.md en $($info.RunDir)."
    }
    Assert-NonEmptyFile $audit.FullName

    $testReport = Get-FirstExistingArtifact -Directory $info.RunDir -Pattern "test-report-*.md"
    if ($null -eq $testReport) {
        throw "Falta al menos un test-report-N.md en $($info.RunDir)."
    }
    Assert-NonEmptyFile $testReport.FullName

    Assert-IndexLink -IndexPath $info.TechnicalIndex -TargetPath $info.TechnicalDoc -Title $info.Title
    Assert-IndexLink -IndexPath $info.UserIndex -TargetPath $info.UserDoc -Title $info.Title

    if ($RequireReadyRoadmap) {
        $roadmap = Get-Content -LiteralPath "ROADMAP.md" -Raw -Encoding UTF8
        $escapedSlug = [regex]::Escape($Slug)
        $readyCount = [regex]::Matches($roadmap, "(?m)^- \[-\] $escapedSlug(?=\s|$).*").Count
        $doneCount = [regex]::Matches($roadmap, "(?m)^- \[x\] $escapedSlug(?=\s|$).*").Count
        if ($doneCount -gt 0) {
            throw "$Slug ya figura como [x]. No se puede preparar PR despues del cierre."
        }
        if ($readyCount -ne 1) {
            throw "ROADMAP.md debe contener exactamente una entrada READY_FOR_PR para $Slug. Encontradas: $readyCount."
        }
    }
}
