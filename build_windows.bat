@echo off
setlocal enabledelayedexpansion

REM --- Change to the directory where this batch file is located ---
cd /d "%~dp0"

REM --- UTF-8 support (optional, won't crash if fails) ---
chcp 65001 >nul 2>&1

title Screen Automator - Windows Build

echo ============================================
echo   Screen Automator - Windows Build Script
echo ============================================
echo.

REM --- Check Python ---
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH.
    echo         Download from: https://www.python.org/downloads/
    echo         Make sure to check "Add Python to PATH" during install.
    echo.
    goto :fail
)

echo [1/6] Python found:
python --version
echo.

REM --- Create virtual environment ---
echo [2/6] Creating virtual environment...
if not exist "venv_win\Scripts\activate.bat" (
    python -m venv venv_win
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to create virtual environment.
        echo         Try: python -m pip install --upgrade pip
        echo.
        goto :fail
    )
)
call venv_win\Scripts\activate.bat
if %errorlevel% neq 0 (
    echo [ERROR] Failed to activate virtual environment.
    echo.
    goto :fail
)
echo    Virtual environment activated.
echo.

REM --- Install dependencies ---
echo [3/6] Installing dependencies...
pip install --upgrade pip >nul 2>&1
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Failed to install dependencies.
    echo         Check your internet connection and try again.
    echo.
    goto :fail
)
echo.

REM --- Build with PyInstaller ---
echo [4/6] Building with PyInstaller... (this may take a few minutes)
pyinstaller --clean --noconfirm ScreenAutomator.spec
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] PyInstaller build failed.
    echo         Check the error messages above.
    echo.
    goto :fail
)
echo.

REM --- Ensure data directories exist in dist ---
echo [5/6] Preparing data directories...
if not exist "dist\ScreenAutomator\config" mkdir "dist\ScreenAutomator\config"
if not exist "dist\ScreenAutomator\templates" mkdir "dist\ScreenAutomator\templates"

REM Copy existing config/templates if any
if exist "config\*" xcopy /Y /E /Q "config" "dist\ScreenAutomator\config\" >nul 2>&1
if exist "templates\*" xcopy /Y /E /Q "templates" "dist\ScreenAutomator\templates\" >nul 2>&1
echo.

REM --- Create desktop shortcut ---
echo [6/6] Creating desktop shortcut...
set "EXE_PATH=%cd%\dist\ScreenAutomator\ScreenAutomator.exe"
set "WORKING_DIR=%cd%\dist\ScreenAutomator"

REM Write a temp PowerShell script (avoids cmd.exe escaping issues)
> "%TEMP%\_create_shortcut.ps1" (
    echo $ws = New-Object -ComObject WScript.Shell
    echo $desktop = $ws.SpecialFolders^('Desktop'^)
    echo $sc = $ws.CreateShortcut^("$desktop\ScreenAutomator.lnk"^)
    echo $sc.TargetPath = '%EXE_PATH%'
    echo $sc.WorkingDirectory = '%WORKING_DIR%'
    echo $sc.Description = 'Screen Automator'
    echo $sc.Save^(^)
    echo Write-Host '   Shortcut created: ScreenAutomator.lnk'
)
powershell -NoProfile -ExecutionPolicy Bypass -File "%TEMP%\_create_shortcut.ps1"
del "%TEMP%\_create_shortcut.ps1" >nul 2>&1

echo.
echo ============================================
echo   BUILD COMPLETE!
echo ============================================
echo.
echo   Executable: dist\ScreenAutomator\ScreenAutomator.exe
echo   Desktop shortcut: ScreenAutomator.lnk
echo.
echo Press any key to exit...
pause >nul
exit /b 0

:fail
echo ============================================
echo   BUILD FAILED - See errors above
echo ============================================
echo.
echo Press any key to exit...
pause >nul
exit /b 1
