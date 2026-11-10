@echo off
rem CMD: tests\test-frontend-unit.bat  -  PowerShell: .\tests\test-frontend-unit.bat
call "%~dp0..\ops\tests.bat" frontend-unit
exit /b %ERRORLEVEL%
