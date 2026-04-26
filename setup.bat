@echo off
REM Slope-Poke one-command setup (Windows).
REM Installs uv (if missing), syncs Python deps, prints next-step instructions.

setlocal enabledelayedexpansion

where uv >nul 2>&1
if errorlevel 1 (
    echo [setup] Installing uv ...
    powershell -ExecutionPolicy Bypass -Command "irm https://astral.sh/uv/install.ps1 | iex"
    set "PATH=%USERPROFILE%\.local\bin;%PATH%"
)

echo [setup] Syncing Python environment ...
uv sync
if errorlevel 1 (
    echo [setup] uv sync failed.
    exit /b 1
)

echo.
echo [setup] Python ready. Next steps:
echo   1. Install Unity Hub and Unity 6 LTS (HDRP).
echo   2. Open unity-project/ from Unity Hub.
echo   3. In Unity: install NuGetForUnity, then NuGet -^> Install NetMQ.
echo   4. Press Play in Unity, then run:  uv run slope-poke smoke --camera cameraA
echo.
endlocal
