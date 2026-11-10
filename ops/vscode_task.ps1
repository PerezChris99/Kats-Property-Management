# Safely execute known KATS .bat entrypoints from VS Code PROCESS tasks.
# Avoid nested cmd.exe /c command strings through PowerShell's task shell.
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('frontend', 'backend-stack', 'backend', 'owner', 'stop', 'setup', 'doctor', 'test-all', 'test-frontend', 'test-frontend-unit', 'test-lint', 'test-build', 'test-backend', 'test-api', 'test-security', 'test-database', 'test-migrations', 'test-performance', 'test-e2e', 'test-smoke', 'test-config', 'test-coverage', 'test-load')]
    [string]$Target
)
$ErrorActionPreference = 'Stop'
$Root = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$Entrypoints = @{
    'setup' = @{ Script = 'ops/launch.bat'; Args = @('setup') }
    'doctor' = @{ Script = 'ops/launch.bat'; Args = @('doctor') }
    'frontend' = @{ Script = 'start-frontend.bat'; Args = @() }
    'backend-stack' = @{ Script = 'ops/launch.bat'; Args = @('backend-stack') }
    'backend' = @{ Script = 'start-backend.bat'; Args = @() }
    'owner' = @{ Script = 'create-owner.bat'; Args = @() }
    'stop' = @{ Script = 'stop.bat'; Args = @() }
    'test-all' = @{ Script = 'tests/test-all.bat'; Args = @() }
    'test-frontend' = @{ Script = 'tests/test-frontend.bat'; Args = @() }
    'test-frontend-unit' = @{ Script = 'tests/test-frontend-unit.bat'; Args = @() }
    'test-lint' = @{ Script = 'tests/test-lint.bat'; Args = @() }
    'test-build' = @{ Script = 'tests/test-build.bat'; Args = @() }
    'test-backend' = @{ Script = 'tests/test-backend.bat'; Args = @() }
    'test-api' = @{ Script = 'tests/test-api.bat'; Args = @() }
    'test-security' = @{ Script = 'tests/test-security.bat'; Args = @() }
    'test-database' = @{ Script = 'tests/test-database.bat'; Args = @() }
    'test-migrations' = @{ Script = 'tests/test-migrations.bat'; Args = @() }
    'test-performance' = @{ Script = 'tests/test-performance.bat'; Args = @() }
    'test-e2e' = @{ Script = 'tests/test-e2e.bat'; Args = @() }
    'test-smoke' = @{ Script = 'tests/test-smoke.bat'; Args = @() }
    'test-config' = @{ Script = 'tests/test-config.bat'; Args = @() }
    'test-coverage' = @{ Script = 'tests/test-coverage.bat'; Args = @() }
    'test-load' = @{ Script = 'tests/test-load.bat'; Args = @() }
}
$Entry = $Entrypoints[$Target]
$Batch = Join-Path $Root $Entry.Script
if (-not (Test-Path -LiteralPath $Batch -PathType Leaf)) {
    [Console]::Error.WriteLine('[ERROR] Missing KATS batch file: ' + $Batch)
    exit 2
}
Push-Location -LiteralPath $Root
try {
    $BatchArgs = @($Entry.Args)
    & $Batch @BatchArgs
    $Code = $LASTEXITCODE
    if ($null -eq $Code) { $Code = 1 }
} catch {
    [Console]::Error.WriteLine('[ERROR] KATS task failed: ' + $_.Exception.Message)
    $Code = 1
} finally {
    Pop-Location
}
exit $Code
