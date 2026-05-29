@echo off
setlocal
chcp 65001 >nul

cd /d "%~dp0\.."

echo ========================================
echo   Cyber Judge Desktop Windows Build
echo ========================================
echo.

if not exist "frontend\node_modules" (
    echo [*] Installing frontend dependencies...
    pushd frontend
    call npm install
    if errorlevel 1 exit /b 1
    popd
)

echo [*] Building frontend static assets...
call npm run build
if errorlevel 1 (
    echo [!] Frontend build failed.
    exit /b 1
)

where pixi >nul 2>&1
if errorlevel 1 (
    echo [!] pixi is required. Install Pixi first, then rerun this script.
    exit /b 1
)

echo [*] Packaging desktop app...
pixi run --manifest-path backend\pixi.toml pyinstaller --noconfirm desktop\CyberJudgeDesktop.spec
if errorlevel 1 (
    echo [!] Desktop packaging failed.
    exit /b 1
)

echo.
echo ========================================
echo   Build complete
echo   Output: dist\CyberJudgeDesktop.exe
echo ========================================
echo.
