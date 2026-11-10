@echo off
rem CMD: test-coverage.bat  -  PowerShell: .\test-coverage.bat
call "%~dp0ops\tests.bat" coverage
exit /b %ERRORLEVEL%
