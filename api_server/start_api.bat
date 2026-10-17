@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
title "VirtualBrowser Local API and MCP Server"

rem Override anytime with:  set VB_PY=D:\path\to\python.exe
rem This interpreter must have fastapi / uvicorn / websockets / "mcp<2" installed.
set "PY_EXE=%VB_PY%"
if not defined PY_EXE set "PY_EXE=D:\Program Files\anaconda3\python.exe"
if not exist "%PY_EXE%" set "PY_EXE=python"

echo Starting VirtualBrowser Local API and MCP Server...
echo Using Python: %PY_EXE%
echo.

"%PY_EXE%" server.py

if errorlevel 1 (
    echo.
    echo [ERROR] Server exited with an error.
)
pause
