@echo off
REM =============================================================================
REM  IQmol-for-Chinese  git mirror speedup script
REM
REM  Speed up git clone of the repo (including submodules) via China mirrors.
REM  The mirror rule (url.insteadOf) applies to BOTH main repo and submodules.
REM
REM  Usage: double-click, or run  .\scripts\speedup_clone.bat
REM =============================================================================
setlocal enabledelayedexpansion

echo ============================================================
echo   IQmol-for-Chinese  mirror-accelerated clone
echo ============================================================
echo.

REM ---- candidate mirrors (tried in order until one works) ----
set "MIRRORS=https://ghfast.top/ https://gh-proxy.com/"

where git >nul 2>nul
if errorlevel 1 (
    echo [ERROR] git not found. Install Git for Windows or MSYS2 first.
    pause
    exit /b 1
)

REM ---- rewrite github.com to mirror. NOTE: mirror prefix MUST include
REM      the full https:// URL, otherwise insteadOf drops the scheme -> 403
for %%M in (%MIRRORS%) do (
    echo ==&gt; trying mirror: %%M
    git config --global url."%%Mhttps://github.com/".insteadOf "https://github.com/"
    git ls-remote --heads "%%Mhttps://github.com/stone-Glitch/IQmol-for-Chinese.git" >nul 2>&1
    if not errorlevel 1 (
        echo [OK] mirror %%M works
        goto :clone
    )
    echo [SKIP] mirror %%M unreachable, trying next...
    git config --global --unset url."%%Mhttps://github.com/".insteadOf 2>nul
)

echo [ERROR] no mirror reachable, check network.
pause
exit /b 1

:clone
echo.
echo ==&gt; cloning main repo with submodules...
git clone --recursive https://github.com/stone-Glitch/IQmol-for-Chinese.git
if errorlevel 1 (
    echo [ERROR] clone failed, please retry.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo   Done! Repo dir: IQmol-for-Chinese
echo.
echo   Note: global mirror rule is set. To restore direct access, run:
echo     git config --global --unset-all url."https://ghfast.top/https://github.com/".insteadOf
echo     git config --global --unset-all url."https://gh-proxy.com/https://github.com/".insteadOf
echo ============================================================
pause
endlocal
