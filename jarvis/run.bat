@echo off
setlocal enabledelayedexpansion

title NIVA - Universal AI Computer Control System
color 0B

echo =====================================================================
echo           NIVA - Universal Autonomous Windows AI Agent
echo =====================================================================
echo.

:: Detect Python
set "PYTHON_CMD="

if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" (
    set "PYTHON_CMD=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
) else if exist "C:\Python311\python.exe" (
    set "PYTHON_CMD=C:\Python311\python.exe"
) else if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
    set "PYTHON_CMD=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
) else (
    where python >nul 2>nul
    if %errorlevel% equ 0 (
        set "PYTHON_CMD=python"
    )
)

if "%PYTHON_CMD%"=="" (
    echo [ERROR] Python 3.11+ was not found on your system.
    echo Please install Python 3.11 from https://www.python.org/downloads/
    echo and ensure "Add Python to PATH" is checked.
    pause
    exit /b 1
)

echo [INFO] Using Python: %PYTHON_CMD%
"%PYTHON_CMD%" --version

:: Check .env
if not exist ".env" (
    if exist ".env.example" (
        echo [INFO] Creating .env from .env.example...
        copy ".env.example" ".env" >nul
    )
)

:: Check dependencies
echo [INFO] Checking dependencies...
"%PYTHON_CMD%" -m pip install -r requirements.txt --quiet --no-warn-script-location

:: Launch NIVA
echo.
echo [INFO] Starting NIVA Desktop System...
echo =====================================================================
"%PYTHON_CMD%" main.py %*

if %errorlevel% neq 0 (
    echo.
    echo [WARNING] NIVA encountered an error during execution.
    pause
)
