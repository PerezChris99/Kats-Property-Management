@echo off
rem Direct launch: two side-by-side panes in Windows Terminal.
rem Inside VS Code use Terminal > Run Task > KATS: Native start (split in VS Code)
rem to get two VS Code integrated terminal panes instead.
call "%~dp0ops\launch.bat" split %*
exit /b %ERRORLEVEL%
