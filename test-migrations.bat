@echo off
rem CMD: test-migrations.bat  -  PowerShell: .\test-migrations.bat
call "%~dp0ops\tests.bat" migrations
exit /b %ERRORLEVEL%
