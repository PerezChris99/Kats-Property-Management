# KATS local development and verification, designed for VS Code integrated terminals.
# Never executes destructive commands against the operational 'db' service.
param(
    [ValidateSet('help','setup','start','owner','test','smoke','browser','browser-full','all','status','logs','stop')]
    [string]$Action = 'help'
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$Root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path

function Invoke-Docker([string[]]$Arguments) {
    & docker @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Docker command failed (exit $LASTEXITCODE): docker $($Arguments -join ' ')"
    }
}
function Test-Docker {
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        throw 'Docker Desktop with Compose is required. Install Docker Desktop and start its engine.'
    }
    & docker info --format '{{.ServerVersion}}' | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'Docker engine is not running. Start Docker Desktop first.' }
}
function New-RandomSecret {
    $bytes = New-Object byte[] 32
    $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    try { $rng.GetBytes($bytes) } finally { $rng.Dispose() }
    return [BitConverter]::ToString($bytes).Replace('-', '')
}
function Initialize-LocalEnvironment {
    if (-not (Test-Path '.env')) {
        $value = [System.IO.File]::ReadAllText((Join-Path $Root '.env.example'))
        $value = $value.Replace('REPLACE_WITH_32_PLUS_RANDOM_CHARACTERS', (New-RandomSecret))
        $value = $value.Replace('REPLACE_WITH_ANOTHER_32_PLUS_RANDOM_CHARACTERS', (New-RandomSecret))
        [System.IO.File]::WriteAllText((Join-Path $Root '.env'), $value)
        Write-Host 'Created local .env with independently generated application secrets. Never commit .env.'
    } else {
        Write-Host 'Using existing .env. No secrets or settings were overwritten.'
    }
}
function Start-LocalStack {
    Test-Docker
    Initialize-LocalEnvironment
    Invoke-Docker @('compose','config','--quiet')
    Invoke-Docker @('compose','up','--build','-d')
    Invoke-Docker @('compose','exec','-T','api','python','-m','flask','--app','wsgi','db','upgrade')
    Invoke-Docker @('compose','exec','-T','api','python','-m','flask','--app','wsgi','seed-permissions')
    Write-Host 'KATS is running locally: http://localhost:5173'
    Write-Host 'Create the first owner interactively with: .\ops\dev.ps1 -Action owner'
}
function Test-LocalStack {
    Test-Docker
    Initialize-LocalEnvironment
    Write-Host 'Running frontend JSX gate, ESLint, JavaScript tests and Vite build, plus backend container build.'
    Invoke-Docker @('compose','build','api','web')
    $compose = @('compose','-f','docker-compose.yml','-f','docker-compose.test.yml')
    Write-Host 'Creating a FRESH disposable, in-memory kats_ci PostgreSQL service. The real db is not used.'
    Invoke-Docker ($compose + @('rm','-s','-f','test-db'))
    Invoke-Docker ($compose + @('up','-d','--wait','test-db'))
    $testUrl = 'postgresql+psycopg://kats_ci:local_test_only@test-db:5432/kats_ci'
    $rlsUrl = 'postgresql://kats_rls_test:rls_ci_password@test-db:5432/kats_ci'
    try {
        Invoke-Docker ($compose + @('run','--rm','--no-deps',
            '-e','APP_ENV=testing', '-e',"DATABASE_URL=$testUrl",
            '-e',"TEST_POSTGRES_URL=$testUrl",'-e',"TEST_DOCUMENT_RLS_URL=$rlsUrl",
            'api','sh','-ec',
            'python -m flask --app wsgi db upgrade && python tests/prepare_postgres.py && python -m pytest -q'))
    } finally {
        Invoke-Docker ($compose + @('stop','test-db'))
    }
    Write-Host 'Frontend, backend, database migrations, RLS and concurrency checks passed.'
}
function Test-LocalSmoke {
    $base = 'http://localhost:5173'
    $landing = Invoke-WebRequest -Uri "$base/" -UseBasicParsing -TimeoutSec 15
    if ($landing.StatusCode -ne 200 -or $landing.Content -notmatch 'Kats') {
        throw 'Frontend landing page failed the smoke check.'
    }
    $ready = Invoke-WebRequest -Uri "$base/readyz" -UseBasicParsing -TimeoutSec 15
    if ($ready.StatusCode -ne 200) { throw 'Backend readiness failed.' }
    $denied = $false
    try {
        $result = Invoke-WebRequest -Uri "$base/api/v1/properties" -UseBasicParsing -TimeoutSec 15
    } catch {
        if ($_.Exception.Response -and [int]$_.Exception.Response.StatusCode -eq 401) {
            $denied = $true
        } else { throw }
    }
    if (-not $denied) { throw 'Security regression: unauthenticated properties must return HTTP 401.' }
    Write-Host 'Live HTTP smoke checks PASSED: frontend, database readiness, anonymous-access denial.'
}
function Test-LocalBrowser {
    $py = Get-Command py -ErrorAction SilentlyContinue
    if ($py) {
        $command = 'py'
        $prefix = @('-3.12')
    } elseif (Get-Command python -ErrorAction SilentlyContinue) {
        $command = 'python'
        $prefix = @()
    } else { throw 'Python 3.12+ is required for local Playwright browser testing.' }
    & $command @prefix -m pip install -r ops/browser-requirements.txt
    if ($LASTEXITCODE -ne 0) { throw 'Browser test dependency install failed.' }
    & $command @prefix -m playwright install chromium
    if ($LASTEXITCODE -ne 0) { throw 'Chromium installation failed.' }
    & $command @prefix -m pytest -v ops/test_browser_e2e.py
    if ($LASTEXITCODE -ne 0) { throw 'Real-browser end-to-end smoke tests failed.' }
}
function Test-IsolatedSixRoleBrowser {
    Test-Docker
    $saved = @{}
    function Set-Temporary([string]$name, [string]$value) {
        $saved[$name] = [Environment]::GetEnvironmentVariable($name, 'Process')
        [Environment]::SetEnvironmentVariable($name, $value, 'Process')
    }
    $compose = @('compose', '-p', 'kats-e2e', '-f', 'compose.e2e.yml')
    Set-Temporary 'KATS_E2E_SECRET_KEY' (New-RandomSecret)
    Set-Temporary 'KATS_E2E_JWT_SECRET_KEY' (New-RandomSecret)
    $password = New-RandomSecret
    Set-Temporary 'KATS_BASE_URL' 'http://localhost:5174'
    foreach ($role in @('OWNER','SUPER_ADMIN','MANAGER','ACCOUNTANT','CARETAKER','TENANT')) {
        Set-Temporary ('KATS_E2E_' + $role + '_EMAIL') ($role.ToLower() + '@e2e.kats.test')
        Set-Temporary ('KATS_E2E_' + $role + '_PASSWORD') $password
        Set-Temporary ('KATS_E2E_' + $role + '_TOTP') ''
    }
    try {
        Write-Host 'Starting isolated browser E2E stack on localhost:5174.'
        Invoke-Docker ($compose + @('down','--remove-orphans'))
        Invoke-Docker ($compose + @('up','--build','-d','--wait'))
        Invoke-Docker ($compose + @('exec','-T','api','python','-m','flask','--app','wsgi','db','upgrade'))
        Invoke-Docker ($compose + @('exec','-T','api','python','-m','flask','--app','wsgi','seed-permissions'))
        Invoke-Docker ($compose + @('exec','-T','-e',"KATS_E2E_PASSWORD=$password",
            'api','python','tests/seed_e2e.py'))
        Test-LocalBrowser
    } finally {
        try { Invoke-Docker ($compose + @('down','--remove-orphans')) }
        finally {
            foreach ($name in $saved.Keys) {
                [Environment]::SetEnvironmentVariable($name, $saved[$name], 'Process')
            }
        }
    }
}

Push-Location $Root
try {
    switch ($Action) {
        'setup' { Test-Docker; Initialize-LocalEnvironment; Invoke-Docker @('compose','config','--quiet') }
        'start' { Start-LocalStack; Test-LocalSmoke }
        'owner' { Test-Docker; Invoke-Docker @('compose','exec','api','python','-m','flask','--app','wsgi','create-user','--role','OWNER') }
        'test' { Test-LocalStack }
        'smoke' { Test-LocalSmoke }
        'browser' { Test-LocalBrowser }
        'browser-full' { Test-IsolatedSixRoleBrowser }
        'all' { Start-LocalStack; Test-LocalStack; Test-LocalSmoke; Test-IsolatedSixRoleBrowser }
        'status' { Test-Docker; Invoke-Docker @('compose','ps') }
        'logs' { Test-Docker; Invoke-Docker @('compose','logs','--follow','--tail','100','api','web','worker','beat') }
        'stop' { Test-Docker; Invoke-Docker @('compose','down'); Write-Host 'Application stopped. Database volumes were preserved.' }
        default {
            Write-Host 'KATS VS Code commands (PowerShell terminal):'
            Write-Host '  .\ops\dev.ps1 -Action setup     # .env + configuration check'
            Write-Host '  .\ops\dev.ps1 -Action start     # build/start/migrate/seed + live smoke'
            Write-Host '  .\ops\dev.ps1 -Action owner     # create initial owner interactively'
            Write-Host '  .\ops\dev.ps1 -Action test      # frontend, backend, disposable PostgreSQL'
            Write-Host '  .\ops\dev.ps1 -Action browser   # Playwright against local app'
            Write-Host '  .\ops\dev.ps1 -Action browser-full   # Disposable six-role E2E stack'
            Write-Host '  .\ops\dev.ps1 -Action all       # start + every automatic local check'
            Write-Host '  .\ops\dev.ps1 -Action logs|status|stop'
        }
    }
} finally { Pop-Location }
