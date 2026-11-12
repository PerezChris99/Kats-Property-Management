@echo off
setlocal EnableExtensions
rem Isolated localhost PostgreSQL demo. Never connects to Neon or production.
set "ACTION=%~1"
if not defined ACTION set "ACTION=setup"
if /I not "%ACTION%"=="setup" if /I not "%ACTION%"=="prepare" if /I not "%ACTION%"=="upgrade" if /I not "%ACTION%"=="verify" if /I not "%ACTION%"=="serve" if /I not "%ACTION%"=="check" (
  echo [ERROR] Use setup, prepare, upgrade, verify, serve or check.
  exit /b 2
)
set "ROOT=%~dp0.."
pushd "%ROOT%"
if errorlevel 1 exit /b 2
set "VENV=%CD%\.venv\Scripts\python.exe"
if not exist "%VENV%" (
  echo [setup] Creating isolated Python environment...
  py -3 -m venv ".venv"
  if errorlevel 1 (popd & exit /b 1)
)
"%VENV%" -c "import psycopg, flask, flask_migrate, argon2"
if errorlevel 1 (
  echo [setup] Installing KATS backend dependencies...
  "%VENV%" -m pip install -r "backend\requirements.txt"
  if errorlevel 1 (popd & exit /b 1)
)
"%VENV%" "ops\local_postgres_demo.py" %ACTION%
set "EXIT=%ERRORLEVEL%"
popd
endlocal & exit /b %EXIT%
