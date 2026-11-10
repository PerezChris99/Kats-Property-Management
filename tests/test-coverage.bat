@echo off
rem CMD: tests\test-coverage.bat  -  PowerShell: .\tests\test-coverage.bat
call "%~dp0..\ops\tests.bat" coverage
exit /b %ERRORLEVEL%
