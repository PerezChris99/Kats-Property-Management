@echo off
rem CMD: tests\test-smoke.bat  -  PowerShell: .\tests\test-smoke.bat
call "%~dp0..\ops\tests.bat" smoke
exit /b %ERRORLEVEL%
