@echo off
rem CMD: tests\test-load.bat  -  PowerShell: .\tests\test-load.bat
call "%~dp0..\ops\tests.bat" load
exit /b %ERRORLEVEL%
