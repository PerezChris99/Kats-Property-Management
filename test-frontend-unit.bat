@echo off
rem CMD: test-frontend-unit.bat  -  PowerShell: .\test-frontend-unit.bat
call "%~dp0ops\tests.bat" frontend-unit
exit /b %ERRORLEVEL%
