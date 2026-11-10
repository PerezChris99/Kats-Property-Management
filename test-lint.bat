@echo off
rem CMD: test-lint.bat  -  PowerShell: .\test-lint.bat
call "%~dp0ops\tests.bat" lint
exit /b %ERRORLEVEL%
