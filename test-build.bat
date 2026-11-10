@echo off
rem CMD: test-build.bat  -  PowerShell: .\test-build.bat
call "%~dp0ops\tests.bat" build
exit /b %ERRORLEVEL%
