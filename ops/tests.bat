@echo off
setlocal EnableExtensions
pushd "%~dp0.." || exit /b 1
set "ACTION=%~1"
if "%ACTION%"=="" set "ACTION=all"
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
  echo [ERROR] Python 3.12+ not found. Install Python and reopen the VS Code terminal.
  popd
  exit /b 1
)
%PYTHON_CMD% "ops\test_windows.py" "%ACTION%"
set "CODE=%ERRORLEVEL%"
popd
endlocal & exit /b %CODE%
