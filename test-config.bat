@echo off
rem CMD: test-config.bat  -  PowerShell: .\test-config.bat
call "%~dp0ops\tests.bat" config
exit /b %ERRORLEVEL%
