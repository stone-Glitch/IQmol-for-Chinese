@echo off
REM =============================================================================
REM  IQmol-for-Chinese  dependency installer  (installs MSYS2 to D: drive)
REM
REM  Installs MSYS2 to D:\msys64 and installs all build dependencies:
REM  MinGW-w64 gcc, cmake, make, Qt5, Boost, OpenSSL, zlib, HDF5, git.
REM
REM  Usage: right-click -> Run as administrator.
REM         After done, double-click D:\msys64\mingw64.exe to open MINGW64.
REM =============================================================================
setlocal enabledelayedexpansion

set "MSYS2_ROOT=D:\msys64"

echo ============================================================
echo   IQmol-for-Chinese  dependency installer
echo   target: %MSYS2_ROOT%
echo ============================================================
echo.

REM ---- check admin rights ----
net session >nul 2>&1
if errorlevel 1 (
    echo [WARN] recommend running as administrator.
    echo.
)

REM ---- 1. skip if already installed ----
if exist "%MSYS2_ROOT%\usr\bin\bash.exe" (
    echo [SKIP] %MSYS2_ROOT% already exists, going straight to deps...
    goto :install_deps
)

REM ---- 2. download self-extracting archive (via China mirror for speed) ----
echo ==^> downloading MSYS2 archive (~100MB, via mirror)...
set "DL=%TEMP%\msys2-base-x86_64-latest.sfx.exe"
set "GH=https://github.com/msys2/msys2-installer/releases/download/nightly-x86_64/msys2-base-x86_64-latest.sfx.exe"

where curl >nul 2>nul
if not errorlevel 1 (
    REM try mirrors first (gh-proxy.com fastest, ghfast.top fallback), then direct
    curl -L --fail --output "%DL%" "https://gh-proxy.com/%GH%"
    if not exist "%DL%" (
        curl -L --fail --output "%DL%" "https://ghfast.top/%GH%"
    )
    if not exist "%DL%" (
        curl -L --fail --output "%DL%" "%GH%"
    )
) else (
    powershell -NoProfile -Command "[Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -UseBasicParsing -Uri 'https://gh-proxy.com/%GH%' -OutFile '%DL%'"
)
if not exist "%DL%" (
    echo [ERROR] download failed. Download manually from https://www.msys2.org/ and install to %MSYS2_ROOT%
    pause
    exit /b 1
)

REM ---- 3. extract to D: drive ----
echo.
echo ==^> extracting to D:\ ...
if not exist "D:\" (
    echo [ERROR] D: drive not found. Edit MSYS2_ROOT at top of script.
    pause
    exit /b 1
)
"%DL%" -y -o"D:\"
if errorlevel 1 (
    echo [ERROR] extraction failed.
    pause
    exit /b 1
)
del /q "%DL%" >nul 2>nul

if exist "D:\msys64\usr\bin\bash.exe" set "MSYS2_ROOT=D:\msys64"

:install_deps

if not exist "%MSYS2_ROOT%\usr\bin\bash.exe" (
    echo [ERROR] bash.exe not found under %MSYS2_ROOT%, install failed.
    pause
    exit /b 1
)

set "BASH=%MSYS2_ROOT%\usr\bin\bash.exe"

REM ---- 4. init + system update ----
echo.
echo ==^> updating MSYS2 (may take minutes)...
"%BASH%" -lc "pacman --noconfirm -Syuu"
"%BASH%" -lc "pacman --noconfirm -Syuu"

REM ---- 5. install build deps ----
echo.
echo ==^> installing build dependencies...
"%BASH%" -lc "pacman --noconfirm -S --needed mingw-w64-x86_64-gcc mingw-w64-x86_64-cmake mingw-w64-x86_64-make mingw-w64-x86_64-qt5-base mingw-w64-x86_64-qt5-tools mingw-w64-x86_64-boost mingw-w64-x86_64-openssl mingw-w64-x86_64-zlib mingw-w64-x86_64-hdf5 mingw-w64-x86_64-git"

if errorlevel 1 (
    echo [ERROR] dependency install failed, check network and retry.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo   Done!  MSYS2 at: %MSYS2_ROOT%
echo
echo   Next steps:
echo     1) double-click %MSYS2_ROOT%\mingw64.exe
echo     2) run:
echo          git clone --recursive https://github.com/stone-Glitch/IQmol-for-Chinese.git
echo          cd IQmol-for-Chinese
echo          scripts\build_windows.bat
echo ============================================================
echo.
pause
endlocal
