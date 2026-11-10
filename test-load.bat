@echo off
rem CMD: test-load.bat  -  PowerShell: .\test-load.bat
call "%~dp0ops\tests.bat" load
exit /b %ERRORLEVEL%
