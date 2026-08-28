@echo off
REM ============================================================
REM  IQmol submodule offline package - verify and extract
REM
REM  HOW TO USE
REM    1. Put this .bat and IQmol-submodules.tar.gz in the SAME folder
REM    2. Double click                     -> verify only
REM    3. Or run with the repo path        -> verify + extract
REM
REM         extract_submodules.bat "D:\IQmol"
REM
REM  NOTE: keep the repo path SHORT (e.g. D:\IQmol).
REM  Windows has a 260-char path limit and some submodule
REM  source trees are very deep.
REM
REM  This file is pure ASCII on purpose. Do NOT add Chinese
REM  comments here, cmd.exe will break on non-ASCII bytes.
REM ============================================================
setlocal EnableDelayedExpansion
cd /d "%~dp0"

set "PKG=IQmol-submodules.tar.gz"
set "EXPSIZE=75759260"
set "EXPMD5=9c0ed6e3527cf0dd1c8d5628cc31538f"

echo.
echo ============================================================
echo   IQmol submodule package - verify and extract
echo ============================================================
echo   Working folder: %CD%
echo.

REM ---------- 1. check package ----------
echo [1/3] Looking for %PKG% ...
if not exist "%PKG%" (
    echo   NOT FOUND: %CD%\%PKG%
    echo.
    echo   Download it from branch "submodules-package", then put it
    echo   in the same folder as this .bat .
    pause
    exit /b 1
)
for %%F in ("%PKG%") do set SIZE=%%~zF
echo   found: %SIZE% bytes
echo.

REM ---------- 2. verify ----------
echo [2/3] Verifying...
if not "%SIZE%"=="%EXPSIZE%" (
    echo   FAILED: size mismatch.
    echo     expected %EXPSIZE%
    echo     actual   %SIZE%
    echo   The download is incomplete, download it again.
    pause
    exit /b 1
)
echo   size OK: %EXPSIZE% bytes

set HASH=
for /f "skip=1 tokens=1" %%H in ('certutil -hashfile "%PKG%" MD5') do (
    if not defined HASH set HASH=%%H
)
echo   MD5: %HASH%
if /i not "%HASH%"=="%EXPMD5%" (
    echo   FAILED: MD5 mismatch.
    echo     expected %EXPMD5%
    echo   The download is corrupt, download it again.
    pause
    exit /b 1
)
echo   MD5 OK
echo.

REM ---------- 3. extract ----------
set "DEST=%~1"
if "%DEST%"=="" goto :noextract

echo [3/3] Extracting to %DEST% ...
if not exist "%DEST%" (
    echo   ERROR: folder does not exist: %DEST%
    echo   Create the repo folder first, or check the path.
    pause
    exit /b 1
)

tar -xzf "%PKG%" -C "%DEST%"
if errorlevel 1 (
    echo.
    echo   Extraction FAILED.
    echo.
    echo   Common causes and fixes:
    echo    1) Long path (260-char limit)
    echo       - use a SHORT repo path, e.g. D:\IQmol
    echo       - or extract with MSYS2:  tar -xzf %PKG% -C /d/IQmol
    echo    2) Old Windows without tar.exe
    echo       - install 7-Zip and extract manually
    echo       - or use MSYS2 terminal
    pause
    exit /b 1
)
echo   Done.
echo.
echo   Checking modules ...
set CNT=0
for /d %%D in ("%DEST%\modules\*") do set /a CNT+=1
echo   %CNT% directories under modules\  (expected 9)
echo.
echo   Next step:
echo     cd /d "%DEST%"
echo     scripts\build_windows.bat
echo.
pause
exit /b 0

:noextract
echo [3/3] Skipped extraction (no target folder given).
echo.
echo   Package is verified and ready: %CD%\%PKG%
echo.
echo   To extract automatically, run in cmd:
echo     "%~nx0" "D:\IQmol"
echo.
echo   Or manually (MSYS2 terminal recommended):
echo     tar -xzf IQmol-submodules.tar.gz -C /d/IQmol
echo.
echo   Extract into the REPOSITORY ROOT, not into modules\.
echo.
pause
exit /b 0
