[CmdletBinding()]
param(
    [Parameter(Position=0)][ValidateSet('install','doctor','status','restart','stop','uninstall','start-internal')][string]$Action = 'doctor',
    [string]$Profile = 'chatgpt-codex',
    [string]$Workspace = (Join-Path $HOME 'codex-workspace'),
    [string]$CodexBin,
    [ValidateSet('codex','zcode')][string]$Provider = 'codex',
    [string]$ZCodeBin,
    [string]$ZCodeModelBaseUrl,
    [string]$ZCodeModel,
    [string]$ZCodeApiKeyEnv = 'BIGMODEL_API_KEY',
    [string]$TunnelClientBin,
    [string]$PythonBin,
    [ValidateSet('personal-full-control','workspace-safe')][string]$Preset = 'personal-full-control',
    [switch]$NoStart
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$scriptDir = $PSScriptRoot
$pluginRoot = Split-Path $scriptDir -Parent
$sourceGuard = Join-Path $pluginRoot 'bridge\codex-mcp-guard.py'
$sourceRunGuard = Join-Path $scriptDir 'run-guard-windows.ps1'
$sourceController = $PSCommandPath
$sourceSkillDir = Join-Path $pluginRoot 'runtime\bootstrap\workspace-new-project'
$manifestFile = Join-Path $pluginRoot '.codex-plugin\plugin.json'
$stateDir = if ($env:CHATGPT_CODEX_BRIDGE_STATE_DIR) { $env:CHATGPT_CODEX_BRIDGE_STATE_DIR } else { Join-Path $env:LOCALAPPDATA 'chatgpt-codex-bridge' }
$runtimeDir = if ($env:CHATGPT_CODEX_BRIDGE_RUNTIME_DIR) { $env:CHATGPT_CODEX_BRIDGE_RUNTIME_DIR } else { Join-Path $env:LOCALAPPDATA 'chatgpt-codex-bridge\runtime' }
$logDir = if ($env:CHATGPT_CODEX_BRIDGE_LOG_DIR) { $env:CHATGPT_CODEX_BRIDGE_LOG_DIR } else { Join-Path $env:LOCALAPPDATA 'chatgpt-codex-bridge\logs' }
$configFile = Join-Path $stateDir 'config.json'
$startupDir = if ($env:CHATGPT_CODEX_BRIDGE_STARTUP_DIR) { $env:CHATGPT_CODEX_BRIDGE_STARTUP_DIR } else { [Environment]::GetFolderPath('Startup') }
$startupFile = Join-Path $startupDir 'chatgpt-codex-bridge.cmd'

function Write-BridgeLog([string]$Message) { Write-Output "chatgpt-codex-bridge: $Message" }

function Get-GuardHash([string]$Path) {
    (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash
}

function Get-PluginVersion {
    if (-not (Test-Path -LiteralPath $manifestFile -PathType Leaf)) { return 'unknown' }
    ([IO.File]::ReadAllText($manifestFile, [Text.Encoding]::UTF8) | ConvertFrom-Json).version
}

function Set-ConfigValue([object]$Cfg, [string]$Name, [object]$Value) {
    if ($Cfg.PSObject.Properties.Name -contains $Name) { $Cfg.$Name = $Value }
    else { $Cfg | Add-Member -NotePropertyName $Name -NotePropertyValue $Value }
}

function Write-Config([object]$Cfg) {
    [IO.File]::WriteAllText($configFile, ($Cfg | ConvertTo-Json -Depth 6), [Text.UTF8Encoding]::new($false))
}

function Update-RuntimeIdentity([object]$Cfg) {
    Set-ConfigValue $Cfg 'plugin_version' (Get-PluginVersion)
    Set-ConfigValue $Cfg 'source_guard_sha256' (Get-GuardHash $sourceGuard)
    Set-ConfigValue $Cfg 'runtime_guard_sha256' (Get-GuardHash $Cfg.runtime_guard)
    Write-Config $Cfg
}

function Test-FullyQualifiedPath([string]$Path) {
    if ([string]::IsNullOrWhiteSpace($Path) -or -not [IO.Path]::IsPathRooted($Path)) { return $false }
    try {
        $root = [IO.Path]::GetPathRoot($Path)
        [void][IO.Path]::GetFullPath($Path)
    } catch { return $false }
    -not [string]::IsNullOrWhiteSpace($root) -and $root -notin @('\','/') -and $root -notmatch '^[A-Za-z]:$'
}

function Resolve-CanonicalDirectory([string]$Path) {
    if (-not (Test-FullyQualifiedPath $Path) -or -not (Test-Path -LiteralPath $Path -PathType Container)) { throw 'workspace must be an existing absolute directory' }
    (Resolve-Path -LiteralPath $Path).ProviderPath
}

function Resolve-CanonicalFile([string]$Path) {
    if (-not (Test-FullyQualifiedPath $Path) -or -not (Test-Path -LiteralPath $Path -PathType Leaf)) { throw 'executable path is invalid' }
    (Resolve-Path -LiteralPath $Path).ProviderPath
}

function Resolve-Program([string]$Explicit, [string[]]$Names) {
    if ($Explicit) { return Resolve-CanonicalFile $Explicit }
    foreach ($name in $Names) {
        $candidate = Get-Command $name -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($candidate) { return Resolve-CanonicalFile $candidate.Source }
    }
    throw "$($Names[0]) was not found"
}

function Invoke-Checked([string]$File, [string[]]$Arguments, [string]$Failure) {
    if ([IO.Path]::GetExtension($File) -in @('.cmd','.bat')) {
        $command = @('call', (Quote-Cmd $File)) + @($Arguments | ForEach-Object { Quote-Cmd $_ })
        & $env:ComSpec /d /s /c ($command -join ' ') *> $null
    } else {
        & $File @Arguments *> $null
    }
    if ($LASTEXITCODE -ne 0) { throw $Failure }
}

function Read-Config {
    if (-not (Test-Path -LiteralPath $configFile -PathType Leaf)) { throw 'bridge is not installed' }
    [IO.File]::ReadAllText($configFile, [Text.Encoding]::UTF8) | ConvertFrom-Json
}

function Quote-Cmd([string]$Value) {
    if ($Value.Contains('"') -or $Value.Contains("`r") -or $Value.Contains("`n")) { throw 'generated command value is invalid' }
    '"' + $Value + '"'
}

function Stop-Tunnel([object]$Cfg) {
    if (-not (Test-Path -LiteralPath $Cfg.pid_file -PathType Leaf)) { return }
    $rawPid = (Get-Content -LiteralPath $Cfg.pid_file -Raw).Trim()
    $pidValue = 0
    if (-not [int]::TryParse($rawPid, [ref]$pidValue) -or $pidValue -le 0) { throw 'bridge pid record is invalid' }
    $process = Get-CimInstance Win32_Process -Filter "ProcessId = $pidValue" -ErrorAction SilentlyContinue
    if ($process) {
        if ($process.CommandLine.IndexOf($Cfg.runtime_tunnel_cmd, [StringComparison]::OrdinalIgnoreCase) -lt 0) { throw 'bridge process ownership check failed' }
        # taskkill races exiting children of the tunnel retry loop; its stderr
        # must not become a terminating error under Stop error preference.
        $previousEap = $ErrorActionPreference
        $ErrorActionPreference = 'Continue'
        try {
            & (Join-Path $env:SystemRoot 'System32\taskkill.exe') /PID $pidValue /T /F *> $null
        } finally {
            $ErrorActionPreference = $previousEap
        }
    }
    Remove-Item -LiteralPath $Cfg.pid_file -Force -ErrorAction SilentlyContinue
}

function Revoke-Jobs([object]$Cfg, [switch]$Purge) {
    if (-not (Test-Path -LiteralPath $Cfg.job_state_dir -PathType Container)) { return }
    $verb = if ($Purge) { '--purge-jobs' } else { '--revoke-jobs' }
    & $Cfg.python_bin $Cfg.runtime_guard $verb $Cfg.job_state_dir
    if ($LASTEXITCODE -ne 0) { throw 'bridge-owned job lifecycle failed' }
}

function Start-Tunnel([object]$Cfg) {
    if (Test-Path -LiteralPath $Cfg.pid_file -PathType Leaf) {
        $existing = 0
        [void][int]::TryParse((Get-Content -LiteralPath $Cfg.pid_file -Raw).Trim(), [ref]$existing)
        if ($existing -gt 0 -and (Get-Process -Id $existing -ErrorAction SilentlyContinue)) { return }
        Remove-Item -LiteralPath $Cfg.pid_file -Force -ErrorAction SilentlyContinue
    }
    $process = Start-Process -FilePath $env:ComSpec -ArgumentList @('/d','/c', (Quote-Cmd $Cfg.runtime_tunnel_cmd)) -WorkingDirectory $stateDir -WindowStyle Hidden -PassThru
    [IO.File]::WriteAllText($Cfg.pid_file, "$($process.Id)`r`n", [Text.UTF8Encoding]::new($false))
}

function Get-HealthUrl([object]$Cfg) {
    if (-not (Test-Path -LiteralPath $Cfg.health_url_file -PathType Leaf)) { return $null }
    $url = (Get-Content -LiteralPath $Cfg.health_url_file -Raw).Trim()
    if ($url -notmatch '^http://(?:127\.0\.0\.1|localhost):\d+$') { return $null }
    $url
}

function Get-LocalContent([string]$Uri) {
    $client = [Net.WebClient]::new()
    $client.Proxy = $null
    try { $client.DownloadString($Uri) } finally { $client.Dispose() }
}

function Test-Health([object]$Cfg) {
    $url = Get-HealthUrl $Cfg
    if (-not $url) { return $false }
    try {
        Get-LocalContent "$url/healthz" | Out-Null
        Get-LocalContent "$url/readyz" | Out-Null
        return $true
    } catch { return $false }
}

function Test-ControlPlane([object]$Cfg) {
    $url = Get-HealthUrl $Cfg
    if (-not $url) { return $false }
    try { $metrics = Get-LocalContent "$url/metrics" } catch { return $false }
    $match = [regex]::Match($metrics, '(?m)^commands_poll_last_successful_timestamp_seconds(?:\{[^}]*\})?\s+([0-9.eE+-]+)')
    if (-not $match.Success) { return $false }
    $age = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds() - [double]$match.Groups[1].Value
    $age -ge -5 -and $age -le 90
}

function Wait-Ready([object]$Cfg) {
    for ($i = 0; $i -lt 60; $i++) { if (Test-Health $Cfg) { break }; Start-Sleep -Milliseconds 500 }
    if (-not (Test-Health $Cfg)) { throw 'Tunnel did not become locally ready' }
    for ($i = 0; $i -lt 240; $i++) { if (Test-ControlPlane $Cfg) { return }; Start-Sleep -Milliseconds 500 }
    throw 'Tunnel control-plane poll is stale'
}

function Assert-Static([object]$Cfg) {
    $provider = if ($Cfg.PSObject.Properties.Name -contains 'provider') { $Cfg.provider } else { 'codex' }
    $paths = @($Cfg.workspace,$Cfg.tunnel_client_bin,$Cfg.python_bin,$Cfg.runtime_guard,$Cfg.runtime_wrapper_ps1,$Cfg.runtime_wrapper_cmd,$Cfg.runtime_tunnel_cmd,$Cfg.workspace_new_project_skill)
    if ($provider -eq 'zcode') {
        $paths = @($paths) + @($Cfg.zcode_bin,$Cfg.zcode_cjs)
    } else {
        $paths = @($paths) + @($Cfg.codex_bin)
    }
    foreach ($path in $paths) {
        if (-not $path) { throw 'installed path validation failed' }
        if (-not (Test-FullyQualifiedPath $path) -or -not (Test-Path -LiteralPath $path)) { throw 'installed path validation failed' }
    }
    Invoke-Checked $Cfg.tunnel_client_bin @('--version') 'tunnel-client is not usable'
    Invoke-Checked $Cfg.tunnel_client_bin @('doctor','--profile',$Cfg.profile) 'Tunnel profile doctor failed'
    if ($provider -eq 'zcode') {
        # ZCode.exe is an Electron host: never launch it as a health probe.
        if ($Cfg.PSObject.Properties.Name -contains 'zcode_provider_config' -and $Cfg.zcode_provider_config) {
            $modelConfigPath = $Cfg.zcode_provider_config
            $modelConfig = [IO.File]::ReadAllText($modelConfigPath, [Text.Encoding]::UTF8) | ConvertFrom-Json
            $envName = $modelConfig.apiKeyEnv
            $hasKey = $false
            foreach ($scope in @('Process','User','Machine')) {
                if ([Environment]::GetEnvironmentVariable($envName, $scope)) { $hasKey = $true; break }
            }
            if (-not $hasKey) {
                throw "environment variable $envName is not set; put your model provider API key in it before installing the zcode provider"
            }
        } else {
            $modelConfigPath = Join-Path $env:USERPROFILE '.zcode\cli\config.json'
            if (-not (Test-Path -LiteralPath $modelConfigPath -PathType Leaf)) {
                throw 'ZCode CLI model config missing (~/.zcode/cli/config.json); complete ZCode CLI login before installing the zcode provider'
            }
        }
    } else {
        Invoke-Checked $Cfg.codex_bin @('--version') 'Codex is not usable'
    }
    if ($Cfg.PSObject.Properties.Name -contains 'runtime_guard_sha256') {
        if ((Get-GuardHash $Cfg.runtime_guard) -ne $Cfg.runtime_guard_sha256) { throw 'runtime Guard hash mismatch' }
    }
}

function Install-Bridge {
    if ($Profile -notmatch '^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$') { throw 'Tunnel profile name is invalid' }
    $workspacePath = Resolve-CanonicalDirectory $Workspace
    $codexPath = $null
    $zcodePath = $null
    $zcodeCjs = $null
    $zcodeModelFile = $null
    if ($Provider -eq 'zcode') {
        $zcodePath = Resolve-Program $ZCodeBin @('ZCode.exe')
        $zcodeCjs = Resolve-CanonicalFile (Join-Path (Split-Path $zcodePath -Parent) 'resources\glm\zcode.cjs')
        if ([bool]$ZCodeModelBaseUrl -xor [bool]$ZCodeModel) {
            throw '-ZCodeModelBaseUrl and -ZCodeModel must be provided together'
        }
    } else {
        $codexPath = Resolve-Program $CodexBin @('codex.cmd','codex.exe')
    }
    $tunnelPath = Resolve-Program $TunnelClientBin @('tunnel-client.exe','tunnel-client')
    $pythonPath = Resolve-Program $PythonBin @('python.exe','python3.exe')
    Invoke-Checked $tunnelPath @('doctor','--profile',$Profile) 'Tunnel profile doctor failed'
    if ($Provider -eq 'zcode') {
        $modelConfig = Join-Path $env:USERPROFILE '.zcode\cli\config.json'
        if (-not (Test-Path -LiteralPath $modelConfig -PathType Leaf)) {
            throw 'ZCode CLI model config missing (~/.zcode/cli/config.json); complete ZCode CLI login before installing the zcode provider'
        }
    } else {
        Invoke-Checked $codexPath @('--version') 'Codex is not usable'
    }
    Invoke-Checked $pythonPath @('--version') 'Python is not usable'

    if (Test-Path -LiteralPath $configFile) {
        $old = Read-Config
        Stop-Tunnel $old
        Revoke-Jobs $old
    }
    New-Item -ItemType Directory -Force -Path $stateDir,$runtimeDir,$logDir,$startupDir,(Join-Path $runtimeDir 'skills\workspace-new-project\scripts') | Out-Null
    $runtimeGuard = Join-Path $runtimeDir 'codex-mcp-guard.py'
    $runtimeWrapperPs1 = Join-Path $runtimeDir 'run-guard.ps1'
    $runtimeWrapperCmd = Join-Path $runtimeDir 'run-guard.cmd'
    $runtimeTunnelCmd = Join-Path $runtimeDir 'run-tunnel.cmd'
    $runtimeController = Join-Path $runtimeDir 'chatgpt-codex-bridge-windows.ps1'
    $runtimeSkill = Join-Path $runtimeDir 'skills\workspace-new-project\SKILL.md'
    $runtimeSkillScripts = Join-Path $runtimeDir 'skills\workspace-new-project\scripts'
    Copy-Item -LiteralPath $sourceGuard -Destination $runtimeGuard -Force
    Copy-Item -LiteralPath $sourceRunGuard -Destination $runtimeWrapperPs1 -Force
    Copy-Item -LiteralPath $sourceController -Destination $runtimeController -Force
    Copy-Item -LiteralPath (Join-Path $sourceSkillDir 'SKILL.md') -Destination $runtimeSkill -Force
    Copy-Item -LiteralPath (Join-Path $sourceSkillDir 'scripts\create_workspace_project.sh') -Destination $runtimeSkillScripts -Force
    Copy-Item -LiteralPath (Join-Path $sourceSkillDir 'scripts\create_workspace_project.ps1') -Destination $runtimeSkillScripts -Force

    $policy = if ($Preset -eq 'personal-full-control') { @('danger-full-access','never') } else { @('workspace-write','on-request') }
    if ($Provider -eq 'zcode' -and $ZCodeModelBaseUrl) {
        $zcodeModelFile = Join-Path $runtimeDir 'zcode-model.json'
        $zcodeModelPayload = [ordered]@{
            providerId='bridge-managed'; label='Bridge Managed Model Provider'
            baseURL=$ZCodeModelBaseUrl; apiKeyEnv=$ZCodeApiKeyEnv; model=$ZCodeModel
        }
        [IO.File]::WriteAllText($zcodeModelFile, ($zcodeModelPayload | ConvertTo-Json), [Text.UTF8Encoding]::new($false))
    }
    $sourceGuardHash = Get-GuardHash $sourceGuard
    $runtimeGuardHash = Get-GuardHash $runtimeGuard
    $cfg = [ordered]@{
        profile=$Profile; provider=$Provider; workspace=$workspacePath; codex_bin=$codexPath
        zcode_bin=$zcodePath; zcode_cjs=$zcodeCjs; zcode_provider_config=$zcodeModelFile
        tunnel_client_bin=$tunnelPath; python_bin=$pythonPath
        preset=$Preset; sandbox=$policy[0]; approval_policy=$policy[1]
        runtime_guard=$runtimeGuard; runtime_wrapper_ps1=$runtimeWrapperPs1; runtime_wrapper_cmd=$runtimeWrapperCmd
        runtime_tunnel_cmd=$runtimeTunnelCmd; runtime_controller=$runtimeController
        workspace_new_project_skill=$runtimeSkill; job_state_dir=(Join-Path $stateDir 'jobs-v3')
        health_url_file=(Join-Path $stateDir 'health.url'); stdout_log=(Join-Path $logDir 'tunnel.stdout.log')
        stderr_log=(Join-Path $logDir 'tunnel.stderr.log'); pid_file=(Join-Path $stateDir 'tunnel.pid')
        plugin_version=(Get-PluginVersion); source_guard_sha256=$sourceGuardHash; runtime_guard_sha256=$runtimeGuardHash
    }
    [IO.File]::WriteAllText($configFile, ($cfg | ConvertTo-Json -Depth 4), [Text.UTF8Encoding]::new($false))
    $runGuard = "@echo off`r`n@chcp 65001 >nul`r`n" + (Quote-Cmd "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe") + ' -NoProfile -NonInteractive -ExecutionPolicy Bypass -File ' + (Quote-Cmd $runtimeWrapperPs1) + ' -Config ' + (Quote-Cmd $configFile) + "`r`n"
    [IO.File]::WriteAllText($runtimeWrapperCmd, $runGuard, [Text.UTF8Encoding]::new($false))
    $guardInvocation = "& '" + $runtimeWrapperPs1.Replace("'", "''") + "' -Config '" + $configFile.Replace("'", "''") + "'"
    $guardEncoded = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($guardInvocation))
    $mcpCommand = 'powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -EncodedCommand ' + $guardEncoded
    $runTunnel = '@echo off' + "`r`n@chcp 65001 >nul`r`n:cgb_tunnel_retry`r`n" + (Quote-Cmd $tunnelPath) + ' run --profile ' + (Quote-Cmd $Profile) + ' --health.listen-addr 127.0.0.1:0 --health.url-file ' + (Quote-Cmd $cfg.health_url_file) + ' --mcp.command ' + (Quote-Cmd ('command=' + $mcpCommand)) + ' 1>>' + (Quote-Cmd $cfg.stdout_log) + ' 2>>' + (Quote-Cmd $cfg.stderr_log) + "`r`ntimeout /t 5 /nobreak >nul 2>&1`r`ngoto cgb_tunnel_retry`r`n"
    [IO.File]::WriteAllText($runtimeTunnelCmd, $runTunnel, [Text.UTF8Encoding]::new($false))
    $startup = '@echo off' + "`r`n@chcp 65001 >nul`r`n" + 'start "" /min ' + (Quote-Cmd "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe") + ' -NoProfile -NonInteractive -ExecutionPolicy Bypass -File ' + (Quote-Cmd $runtimeController) + " start-internal`r`n"
    [IO.File]::WriteAllText($startupFile, $startup, [Text.UTF8Encoding]::new($false))
    $installed = Read-Config
    Assert-Static $installed
    if ($NoStart) { Write-BridgeLog "installed status=configured preset=$Preset"; return }
    Start-Tunnel $installed
    Wait-Ready $installed
    Write-BridgeLog "installed status=ready preset=$Preset"
}

switch ($Action) {
    'install' { Install-Bridge }
    'start-internal' { $cfg = Read-Config; Start-Tunnel $cfg }
    'doctor' { $cfg = Read-Config; Assert-Static $cfg; $version = if ($cfg.PSObject.Properties.Name -contains 'plugin_version') { $cfg.plugin_version } else { 'unknown' }; if ($NoStart) { Write-BridgeLog "status=configured preset=$($cfg.preset) version=$version runtime_guard_match=true" } else { if (-not (Test-Health $cfg) -or -not (Test-ControlPlane $cfg)) { throw 'Tunnel is not ready' }; Write-BridgeLog "status=ready preset=$($cfg.preset) version=$version runtime_guard_match=true" } }
    'status' { $cfg = Read-Config; Assert-Static $cfg; $version = if ($cfg.PSObject.Properties.Name -contains 'plugin_version') { $cfg.plugin_version } else { 'unknown' }; if (-not (Test-Health $cfg) -or -not (Test-ControlPlane $cfg)) { throw 'Tunnel is not ready' }; Write-BridgeLog "status=ready preset=$($cfg.preset) version=$version runtime_guard_match=true" }
    'restart' { $cfg = Read-Config; Assert-Static $cfg; Stop-Tunnel $cfg; Revoke-Jobs $cfg; Copy-Item -LiteralPath $sourceGuard -Destination $cfg.runtime_guard -Force; Update-RuntimeIdentity $cfg; Start-Tunnel $cfg; Wait-Ready $cfg; Write-BridgeLog "restarted status=ready preset=$($cfg.preset) version=$($cfg.plugin_version) runtime_guard_match=true" }
    'stop' { $cfg = Read-Config; Stop-Tunnel $cfg; Revoke-Jobs $cfg; Write-BridgeLog "status=stopped preset=$($cfg.preset)" }
    'uninstall' { $cfg = Read-Config; Stop-Tunnel $cfg; Revoke-Jobs $cfg; Revoke-Jobs $cfg -Purge; Remove-Item -LiteralPath $startupFile -Force -ErrorAction SilentlyContinue; Remove-Item -LiteralPath $runtimeDir -Recurse -Force; Remove-Item -LiteralPath $configFile -Force; Remove-Item -LiteralPath $cfg.health_url_file,$cfg.stdout_log,$cfg.stderr_log,$cfg.pid_file -Force -ErrorAction SilentlyContinue; Write-BridgeLog 'uninstalled; external Tunnel profile preserved' }
}
