@echo off
rem CMD: tests\test-all.bat  -  PowerShell: .\tests\test-all.bat
call "%~dp0..\ops\tests.bat" all
exit /b %ERRORLEVEL%
