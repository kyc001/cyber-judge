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

set "PIXI_CMD="
where pixi >nul 2>&1
if not errorlevel 1 set "PIXI_CMD=pixi"
if not defined PIXI_CMD if exist "%USERPROFILE%\.pixi\bin\pixi.exe" set "PIXI_CMD=%USERPROFILE%\.pixi\bin\pixi.exe"
if not defined PIXI_CMD (
    echo [!] pixi is required. Run npm run setup first, then rerun this script.
    exit /b 1
)

echo [*] Packaging desktop app...
"%PIXI_CMD%" run --manifest-path backend\pixi.toml pyinstaller --noconfirm desktop\CyberJudgeDesktop.spec
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
