@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
title "VirtualBrowser Local API and MCP Server"

set "PY_EXE=D:\Python313\python.exe"
if not exist "%PY_EXE%" (
    set "PY_EXE=python"
)

echo Starting VirtualBrowser Local API and MCP Server...
echo Using Python: %PY_EXE%
echo.

"%PY_EXE%" server.py

if errorlevel 1 (
    echo.
    echo [ERROR] Server exited with an error.
)
pause
