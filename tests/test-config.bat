@echo off
rem CMD: tests\test-config.bat  -  PowerShell: .\tests\test-config.bat
call "%~dp0..\ops\tests.bat" config
exit /b %ERRORLEVEL%
