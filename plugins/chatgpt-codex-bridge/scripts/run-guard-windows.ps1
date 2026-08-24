[CmdletBinding()]
param([Parameter(Mandatory)][string]$Config)

$ErrorActionPreference = 'Stop'
$configPath = (Resolve-Path -LiteralPath $Config).ProviderPath
$cfg = [IO.File]::ReadAllText($configPath, [Text.Encoding]::UTF8) | ConvertFrom-Json

& $cfg.python_bin $cfg.runtime_guard `
    --workspace $cfg.workspace `
    --codex-bin $cfg.codex_bin `
    --desktop-open-bin $cfg.codex_bin `
    --job-state-dir $cfg.job_state_dir `
    --sandbox $cfg.sandbox `
    --approval-policy $cfg.approval_policy `
    --workspace-new-project-skill $cfg.workspace_new_project_skill
exit $LASTEXITCODE
