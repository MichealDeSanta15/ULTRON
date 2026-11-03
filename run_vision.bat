@echo off
setlocal
cd /d "%~dp0"
set PYTHONPATH=%~dp0src
python -m vision --open-browser
if errorlevel 1 pause
