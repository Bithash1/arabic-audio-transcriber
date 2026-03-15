@echo off
chcp 65001 >nul
setlocal

if "%~1"=="" (
    python app.py
) else (
    python app.py "%~1"
)

pause
