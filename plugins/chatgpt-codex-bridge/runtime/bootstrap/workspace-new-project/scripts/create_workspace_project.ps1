[CmdletBinding()]
param(
    [switch]$Here,
    [string]$BaseDir = (Join-Path $HOME 'codex-workspace'),
    [string]$Name
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

function Test-FullyQualifiedPath([string]$Path) {
    if ([string]::IsNullOrWhiteSpace($Path) -or -not [IO.Path]::IsPathRooted($Path)) { return $false }
    try {
        $root = [IO.Path]::GetPathRoot($Path)
        [void][IO.Path]::GetFullPath($Path)
    } catch { return $false }
    -not [string]::IsNullOrWhiteSpace($root) -and $root -notin @('\','/') -and $root -notmatch '^[A-Za-z]:$'
}

if ($Here) {
    if ($Name) { throw 'Name is not accepted with -Here.' }
    $projectPath = (Resolve-Path -LiteralPath (Get-Location).Path).ProviderPath
} else {
    if (-not (Test-FullyQualifiedPath $BaseDir) -or -not (Test-Path -LiteralPath $BaseDir -PathType Container)) {
        throw 'BaseDir must be an existing absolute directory.'
    }
    if ([string]::IsNullOrWhiteSpace($Name) -or $Name -in '.', '..' -or $Name.IndexOfAny([IO.Path]::GetInvalidFileNameChars()) -ge 0) {
        throw 'Name is invalid.'
    }
    $projectPath = Join-Path (Resolve-Path -LiteralPath $BaseDir).ProviderPath $Name
    New-Item -ItemType Directory -Path $projectPath -ErrorAction Stop | Out-Null
}

@('docs\specs','docs\adr','src','.project-memory\events','.project-memory\summaries','.project-memory\decisions') |
    ForEach-Object { New-Item -ItemType Directory -Force -Path (Join-Path $projectPath $_) | Out-Null }

$gitignore = Join-Path $projectPath '.gitignore'
if (-not (Test-Path -LiteralPath $gitignore)) { New-Item -ItemType File -Path $gitignore | Out-Null }
$lines = @(Get-Content -LiteralPath $gitignore -ErrorAction SilentlyContinue)
if ($lines -notcontains '.project-memory/') { Add-Content -LiteralPath $gitignore -Value '.project-memory/' }

$files = @{
    'README.md' = "# Project`r`n`r`nSpec-driven project. Start in docs/specs before implementation.`r`n"
    'AGENTS.md' = "# Agent Instructions`r`n`r`nTreat versioned specs as the source of truth.`r`n`r`n- Write requirements, design, and tasks before non-trivial code.`r`n- Record architecture decisions under docs/adr/.`r`n- Work one task at a time and verify before completion.`r`n- Keep .project-memory/ out of Git.`r`n"
    'docs\specs\README.md' = "# Specs`r`n`r`nCreate docs/specs/<feature>/{requirements,design,tasks}.md.`r`n"
    'docs\adr\README.md' = "# ADRs`r`n`r`nUse Context / Decision / Consequences.`r`n"
    '.project-memory\summaries\short.md' = "# Short Summary`r`n`r`nRolling high-signal project summary.`r`n"
}
foreach ($relative in $files.Keys) {
    $target = Join-Path $projectPath $relative
    if (-not (Test-Path -LiteralPath $target)) {
        [IO.File]::WriteAllText($target, $files[$relative], [Text.UTF8Encoding]::new($false))
    }
}

$projectPath
