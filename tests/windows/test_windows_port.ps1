param([switch]$PathValidationOnly)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
if ($PSVersionTable.PSVersion.Major -ne 5 -or $PSVersionTable.PSEdition -ne 'Desktop') { throw 'run this test with Windows PowerShell 5.1' }

$repo = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).ProviderPath
$plugin = Join-Path $repo 'plugins\chatgpt-codex-bridge'
$controller = Join-Path $plugin 'scripts\chatgpt-codex-bridge-windows.ps1'
$controllerSource = [IO.File]::ReadAllText($controller, [Text.Encoding]::UTF8)
if ($controllerSource -match '\[IO\.Path\]::IsPathFullyQualified') { throw 'controller still depends on an API missing from Windows PowerShell 5.1' }
$bootstrapScript = Join-Path $plugin 'runtime\bootstrap\workspace-new-project\scripts\create_workspace_project.ps1'
$bootstrapSource = [IO.File]::ReadAllText($bootstrapScript, [Text.Encoding]::UTF8)
if ($bootstrapSource -match '\[IO\.Path\]::IsPathFullyQualified') { throw 'bootstrap still depends on an API missing from Windows PowerShell 5.1' }
$testBase = Join-Path ([Environment]::GetFolderPath('LocalApplicationData')) 'Temp'
New-Item -ItemType Directory -Force -Path $testBase | Out-Null
$testRoot = Join-Path $testBase ('chatgpt-codex-bridge-windows-测试-' + [guid]::NewGuid().ToString('N'))
$state = Join-Path $testRoot 'state'
$runtime = Join-Path $testRoot 'runtime'
$logs = Join-Path $testRoot 'logs'
$startup = Join-Path $testRoot 'startup'
$workspace = Join-Path $testRoot 'workspace'
$buildRoot = Join-Path ([IO.Path]::GetTempPath()) ('cgb-cli-' + [guid]::NewGuid().ToString('N'))
$fakeTunnel = Join-Path $buildRoot 'fake-cli.exe'
New-Item -ItemType Directory -Force -Path $testRoot,$workspace,$startup,$buildRoot | Out-Null
$fakeSource = Join-Path $buildRoot 'fake-cli.cs'
[IO.File]::WriteAllText($fakeSource, 'public static class P { public static int Main(string[] args) { return 0; } }', [Text.ASCIIEncoding]::new())
$compiler = @(
    (Join-Path $env:WINDIR 'Microsoft.NET\Framework64\v4.0.30319\csc.exe'),
    (Join-Path $env:WINDIR 'Microsoft.NET\Framework\v4.0.30319\csc.exe')
) | Where-Object { Test-Path -LiteralPath $_ -PathType Leaf } | Select-Object -First 1
if (-not $compiler) { throw 'Windows .NET Framework compiler was not found' }
& $compiler /nologo /target:exe "/out:$fakeTunnel" $fakeSource
if ($LASTEXITCODE -ne 0) { throw 'fake Windows CLI compilation failed' }

$env:CHATGPT_CODEX_BRIDGE_STATE_DIR = $state
$env:CHATGPT_CODEX_BRIDGE_RUNTIME_DIR = $runtime
$env:CHATGPT_CODEX_BRIDGE_LOG_DIR = $logs
$env:CHATGPT_CODEX_BRIDGE_STARTUP_DIR = $startup
try {
    $tokens = $null
    $errors = $null
    $ast = [Management.Automation.Language.Parser]::ParseFile($controller, [ref]$tokens, [ref]$errors)
    if ($errors.Count -ne 0) { throw $errors[0].Message }
foreach ($functionName in @('Test-FullyQualifiedPath','Quote-Cmd','Invoke-Checked')) {
    $functionAst = $ast.Find({
        param($node)
        $node -is [Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -eq $functionName
    }, $true)
        if (-not $functionAst) { throw "$functionName was not found" }
        . ([scriptblock]::Create($functionAst.Extent.Text))
    }
    if (-not (Test-FullyQualifiedPath $workspace)) { throw 'absolute path was rejected' }
    foreach ($relativePath in @('.\relative-workspace','C:relative-workspace','\root-relative-workspace')) {
        if (Test-FullyQualifiedPath $relativePath) { throw "relative path was accepted: $relativePath" }
    }
    Invoke-Checked $fakeTunnel @('--version') 'Windows CLI invocation failed'
    if ($PathValidationOnly) { Write-Output 'PASS: Windows PowerShell 5.1 path validation'; return }

    $codex = (Get-Command codex.cmd -CommandType Application).Source
    $python = (Get-Command python.exe -CommandType Application | Select-Object -First 1).Source
    & $controller install -Profile windows-fixture -Workspace $workspace -CodexBin $fakeTunnel -TunnelClientBin $fakeTunnel -PythonBin $python -Preset workspace-safe -NoStart
    & $controller doctor -NoStart
    $config = [IO.File]::ReadAllText((Join-Path $state 'config.json'), [Text.Encoding]::UTF8) | ConvertFrom-Json
    [string]$runTunnelPath = $config.runtime_tunnel_cmd
    if (-not (Test-Path -LiteralPath $runTunnelPath -PathType Leaf)) { throw 'runtime tunnel script is missing' }
    $runTunnel = [IO.File]::ReadAllText($runTunnelPath, [Text.Encoding]::UTF8)
    if ($runTunnel -notmatch '--mcp\.command "command=powershell\.exe .* -EncodedCommand [A-Za-z0-9+/=]+"') { throw 'tunnel command does not use the Unicode-safe encoded launcher' }
    & $python (Join-Path $PSScriptRoot 'test_guard_windows.py') --guard $config.runtime_guard --workspace $workspace --codex-bin $codex --python-bin $python
    if ($LASTEXITCODE -ne 0) { throw 'Guard MCP test failed' }

    $bootstrapRoot = Join-Path $testRoot 'bootstrap'
    New-Item -ItemType Directory -Path $bootstrapRoot | Out-Null
    Push-Location $bootstrapRoot
    try { & (Join-Path $runtime 'skills\workspace-new-project\scripts\create_workspace_project.ps1') -Here | Out-Null } finally { Pop-Location }
    foreach ($required in @('AGENTS.md','README.md','.gitignore','docs\specs','docs\adr','src','.project-memory')) {
        if (-not (Test-Path -LiteralPath (Join-Path $bootstrapRoot $required))) { throw "bootstrap missing $required" }
    }
    Write-Output 'PASS: Windows isolated install/doctor/bootstrap'
} finally {
    Remove-Item Env:CHATGPT_CODEX_BRIDGE_STATE_DIR,Env:CHATGPT_CODEX_BRIDGE_RUNTIME_DIR,Env:CHATGPT_CODEX_BRIDGE_LOG_DIR,Env:CHATGPT_CODEX_BRIDGE_STARTUP_DIR -ErrorAction SilentlyContinue
    $allowedCleanupRoots = @(
        [IO.Path]::GetFullPath($testBase).TrimEnd('\') + '\',
        [IO.Path]::GetFullPath([IO.Path]::GetTempPath()).TrimEnd('\') + '\'
    )
    foreach ($cleanupRoot in @($testRoot,$buildRoot)) {
        $resolvedCleanupRoot = [IO.Path]::GetFullPath($cleanupRoot)
        if ($allowedCleanupRoots | Where-Object { $resolvedCleanupRoot.StartsWith($_, [StringComparison]::OrdinalIgnoreCase) }) {
            try {
                Get-ChildItem -LiteralPath $resolvedCleanupRoot -Recurse -Force -ErrorAction SilentlyContinue | ForEach-Object { $_.IsReadOnly = $false }
                Remove-Item -LiteralPath $resolvedCleanupRoot -Recurse -Force -ErrorAction Stop
            } catch { }
        }
    }
}
