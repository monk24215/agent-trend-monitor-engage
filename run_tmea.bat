@echo off
REM =====================================================================
REM  run_tmea.bat — one-click trigger for the TMEA agent.
REM  Double-click this file (or run it from a terminal) to:
REM    1. run today's pipeline  (python -m tmea.run)
REM    2. rebuild the reopenable dashboard (python -m tmea.dashboard)
REM    3. open daily\index.html in your default browser
REM =====================================================================
setlocal enabledelayedexpansion
cd /d "%~dp0"

REM --- load ANTHROPIC_API_KEY from a local .env file, if present -------
REM   .env is gitignored — see .env.example for the format. If no key is
REM   found anywhere (this file or an already-set system env var), the
REM   pipeline runs in mock mode instead of failing.
if exist ".env" (
    for /f "usebackq tokens=1,* delims==" %%A in (".env") do (
        if /i "%%A"=="ANTHROPIC_API_KEY" set "ANTHROPIC_API_KEY=%%B"
    )
)

if "%ANTHROPIC_API_KEY%"=="" (
    echo [tmea] No ANTHROPIC_API_KEY found — running in MOCK mode ^(no real model calls^).
    echo [tmea] To go live: copy .env.example to .env and paste your key in, or run:
    echo [tmea]     setx ANTHROPIC_API_KEY "sk-ant-..."
    echo.
)

REM --- pick a python launcher --------------------------------------------
where python >nul 2>nul
if errorlevel 1 (
    set "PY=py"
) else (
    set "PY=python"
)

echo [tmea] Running today's pipeline...
%PY% -m tmea.run
if errorlevel 1 (
    echo.
    echo [tmea] Run failed — see the error above.
    pause
    exit /b 1
)

echo.
echo [tmea] Generating email bodies...
%PY% -m tmea.bodygen
if errorlevel 1 (
    echo [tmea] Body generation failed — see error above. Continuing; bodies can be regenerated.
)

echo.
echo [tmea] Rebuilding dashboard...
%PY% -m tmea.dashboard

echo [tmea] Opening dashboard...
start "" "daily\index.html"

echo.
echo [tmea] Done.
pause
