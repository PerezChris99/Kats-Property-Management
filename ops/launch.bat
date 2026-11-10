@echo off
setlocal EnableExtensions
rem Locate the launcher relative to THIS batch file before processing arguments.
rem SHIFT changes %%0 and previously moved the root one directory too high.
set "ACTION=%~1"
if not defined ACTION set "ACTION=start"
for %%I in ("%~dp0..") do set "KATS_ROOT=%%~fI"
set "KATS_SCRIPT=%KATS_ROOT%\ops\run_windows.py"
if not exist "%KATS_SCRIPT%" (
  echo [ERROR] Missing launcher: "%KATS_SCRIPT%"
  echo [ERROR] Check the repository checkout and run git pull origin main.
  endlocal & exit /b 2
)
pushd "%KATS_ROOT%"
if errorlevel 1 (
  echo [ERROR] Could not enter repository: "%KATS_ROOT%"
  endlocal & exit /b 2
)
rem Lightweight PATH-ONLY verification for Windows CI; never runs services.
if /I "%KATS_PATH_CHECK_ONLY%"=="1" (
  echo [PASS] %ACTION% launcher found: "%KATS_SCRIPT%"
  popd
  endlocal & exit /b 0
)
set "PYTHON_CMD="
if defined VIRTUAL_ENV (
  python -c "import sys;sys.exit(0 if sys.version_info >= (3,12) else 1)" >nul 2>&1
  if not errorlevel 1 set "PYTHON_CMD=python"
)
if not defined PYTHON_CMD (
  py -3.12 -c "import sys;sys.exit(0 if sys.version_info >= (3,12) else 1)" >nul 2>&1
  if not errorlevel 1 set "PYTHON_CMD=py -3.12"
)
if not defined PYTHON_CMD (
  py -3 -c "import sys;sys.exit(0 if sys.version_info >= (3,12) else 1)" >nul 2>&1
  if not errorlevel 1 set "PYTHON_CMD=py -3"
)
if not defined PYTHON_CMD (
  python -c "import sys;sys.exit(0 if sys.version_info >= (3,12) else 1)" >nul 2>&1
  if not errorlevel 1 set "PYTHON_CMD=python"
)
if not defined PYTHON_CMD (
  echo [ERROR] Python 3.12+ not found. Install Python and reopen the terminal.
  popd
  endlocal & exit /b 1
)
%PYTHON_CMD% "%KATS_SCRIPT%" "%ACTION%"
set "CODE=%ERRORLEVEL%"
popd
endlocal & exit /b %CODE%
