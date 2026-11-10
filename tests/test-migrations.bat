@echo off
rem CMD: tests\test-migrations.bat  -  PowerShell: .\tests\test-migrations.bat
call "%~dp0..\ops\tests.bat" migrations
exit /b %ERRORLEVEL%
