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
    if ($runTunnel -notmatch '(?m)^:cgb_tunnel_retry\r?\n') { throw 'tunnel command does not define the retry loop' }
    if ($runTunnel -notmatch '(?m)^timeout /t 5 /nobreak >nul 2>&1\r?\n') { throw 'tunnel command does not use the bounded retry delay' }
    if ($runTunnel -notmatch '(?m)^goto cgb_tunnel_retry\r?\n') { throw 'tunnel command does not return to the retry loop' }
    $loopProcess = Start-Process -FilePath $env:ComSpec -ArgumentList @('/d','/c',(Quote-Cmd $runTunnelPath)) -WorkingDirectory $state -WindowStyle Hidden -PassThru
    try {
        Start-Sleep -Seconds 1
        if (-not (Get-Process -Id $loopProcess.Id -ErrorAction SilentlyContinue)) { throw 'tunnel retry loop exited after the first client exit' }
        Start-Sleep -Seconds 5
        if (-not (Get-Process -Id $loopProcess.Id -ErrorAction SilentlyContinue)) { throw 'tunnel retry loop did not survive a retry interval' }
    } finally {
        if (Get-Process -Id $loopProcess.Id -ErrorAction SilentlyContinue) {
            & (Join-Path $env:SystemRoot 'System32\taskkill.exe') /PID $loopProcess.Id /T /F *> $null
        }
        for ($attempt = 0; $attempt -lt 20 -and (Get-Process -Id $loopProcess.Id -ErrorAction SilentlyContinue); $attempt++) {
            Start-Sleep -Milliseconds 100
        }
    }
    if (Get-Process -Id $loopProcess.Id -ErrorAction SilentlyContinue) { throw 'tunnel retry loop process tree did not terminate' }
    & $python (Join-Path $PSScriptRoot 'test_guard_windows.py') --guard $config.runtime_guard --workspace $workspace --codex-bin $codex --python-bin $python
    if ($LASTEXITCODE -ne 0) { throw 'Guard MCP test failed' }

    $zcodeDir = Join-Path $buildRoot 'zcode-fake'
    $zcodeExe = Join-Path $zcodeDir 'ZCode.exe'
    $zcodeCjs = Join-Path $zcodeDir 'resources\glm\zcode.cjs'
    New-Item -ItemType Directory -Force -Path (Join-Path $zcodeDir 'resources\glm') | Out-Null
    Copy-Item -LiteralPath $fakeTunnel -Destination $zcodeExe -Force
    [IO.File]::WriteAllText($zcodeCjs, '// fake zcode cli bundle', [Text.ASCIIEncoding]::new())

    $oldHomeDrive = $env:HOMEDRIVE
    $oldHomePath = $env:HOMEPATH
    $oldUserProfile = $env:USERPROFILE
    $fakeHome = Join-Path $testRoot 'fakehome'
    New-Item -ItemType Directory -Force -Path (Join-Path $fakeHome '.zcode\cli') | Out-Null
    $homeRoot = [IO.Path]::GetPathRoot($fakeHome)
    try {
        $env:HOMEDRIVE = $homeRoot.TrimEnd('\')
        $env:HOMEPATH = $fakeHome.Substring($homeRoot.Length)
        $env:USERPROFILE = $fakeHome
        $zcodeRejected = $false
        try {
            & $controller install -Profile windows-zcode -Workspace $workspace -Provider zcode -ZCodeBin $zcodeExe -TunnelClientBin $fakeTunnel -PythonBin $python -Preset workspace-safe -NoStart -ErrorAction Stop
        } catch {
            if ($_.Exception.Message -match 'model config missing') { $zcodeRejected = $true } else { throw }
        }
        if (-not $zcodeRejected) { throw 'zcode install did not fail closed without a ZCode CLI model config' }
        [IO.File]::WriteAllText((Join-Path $fakeHome '.zcode\cli\config.json'), '{"model":{"main":"builtin:bigmodel-start-plan/GLM-5.3-Flash"}}', [Text.ASCIIEncoding]::new())
        & $controller install -Profile windows-zcode -Workspace $workspace -Provider zcode -ZCodeBin $zcodeExe -TunnelClientBin $fakeTunnel -PythonBin $python -Preset workspace-safe -NoStart
        & $controller doctor -NoStart
        $zcodeConfig = [IO.File]::ReadAllText((Join-Path $state 'config.json'), [Text.Encoding]::UTF8) | ConvertFrom-Json
        if ($zcodeConfig.provider -ne 'zcode') { throw 'zcode install did not record the provider' }
        if ($zcodeConfig.zcode_bin -ne $zcodeExe -or $zcodeConfig.zcode_cjs -ne $zcodeCjs) { throw 'zcode install did not record the executor paths' }
        if (([IO.File]::ReadAllText((Join-Path $state 'config.json'), [Text.Encoding]::UTF8)) -match '"codex_bin":\s*"[^"]+"') { throw 'zcode install must not record a codex binary' }
    } finally {
        $env:HOMEDRIVE = $oldHomeDrive
        $env:HOMEPATH = $oldHomePath
        $env:USERPROFILE = $oldUserProfile
    }


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
