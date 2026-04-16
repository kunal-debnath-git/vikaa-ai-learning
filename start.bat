@echo off
cd /d "%~dp0"
title VikaaAI — Leadership Prep

echo.
echo  ================================================
echo    VikaaAI  ^|  Leadership Interview Prep
echo  ================================================
echo.

:: ── 1. Python check ──────────────────────────────────────────────────────────
where python >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Python not found. Install Python 3.10+ and add it to PATH.
    pause
    exit /b 1
)

:: ── 2. Create venv if missing ────────────────────────────────────────────────
if not exist "venv\Scripts\activate.bat" (
    echo  [Setup] Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo  [ERROR] Failed to create venv.
        pause
        exit /b 1
    )
)

:: ── 3. Sync dependencies (fast no-op if already up to date) ──────────────────
echo  [Setup] Checking dependencies...
venv\Scripts\pip install --quiet --upgrade pip
venv\Scripts\pip install --quiet -r requirements.txt
if errorlevel 1 (
    echo  [ERROR] pip install failed. Check requirements.txt and your internet connection.
    pause
    exit /b 1
)
echo  [Setup] OK.
echo.

:: ── 4. Check .env exists ──────────────────────────────────────────────────────
if not exist ".env" (
    echo  [WARN] No .env file found. Create one with:
    echo         SUPABASE_URL=...
    echo         SUPABASE_KEY=...
    echo         GEMINI_API_KEY=...
    echo         ANTHROPIC_API_KEY=...
    echo.
    echo  Press any key to start anyway ^(bypass test mode will still work^)...
    pause >nul
)

:: ── 5. Open browser after server is ready ────────────────────────────────────
start /b powershell -NoProfile -Command "Start-Sleep 3; Start-Process 'http://localhost:9000'"

:: ── 6. Start server ───────────────────────────────────────────────────────────
echo  [Start] Server starting at http://localhost:9000
echo  [Start] Press Ctrl+C to stop.
echo.
venv\Scripts\uvicorn main:app --host 0.0.0.0 --port 9000

echo.
echo  Server stopped.
pause
