@echo off
title CosmoLights
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
    start "" ".venv\Scripts\pythonw.exe" main.py
) else (
    python main.py
)
exit
