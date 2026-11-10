@echo off
rem CMD: tests\test-lint.bat  -  PowerShell: .\tests\test-lint.bat
call "%~dp0..\ops\tests.bat" lint
exit /b %ERRORLEVEL%
