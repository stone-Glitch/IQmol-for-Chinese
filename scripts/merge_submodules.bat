@echo off
REM ============================================================
REM  IQmol submodule offline package - merge and verify
REM
REM  HOW TO USE
REM    1. Put this .bat into the SAME folder as part_00/01/02
REM    2. Double click it        -> merge + verify only
REM    OR run with a path        -> merge + verify + extract
REM
REM       merge_submodules.bat "D:\path\to\IQmol-for-Chinese"
REM
REM  This file is pure ASCII on purpose. Do NOT add Chinese
REM  comments here, cmd.exe will break on non-ASCII bytes.
REM ============================================================
setlocal EnableDelayedExpansion
cd /d "%~dp0"

echo.
echo ============================================================
echo   IQmol submodule package - merge and verify
echo ============================================================
echo   Working folder: %CD%
echo.

REM ---------- 1. check the three split files ----------
echo [1/4] Checking split files...
set MISSING=0
if not exist part_00 (
    set MISSING=1
    echo   MISSING: part_00
)
if not exist part_01 (
    set MISSING=1
    echo   MISSING: part_01
)
if not exist part_02 (
    set MISSING=1
    echo   MISSING: part_02
)
if "%MISSING%"=="1" (
    echo.
    echo   ERROR: some split files are missing.
    echo   Copy this .bat into the folder containing part_00/01/02.
    echo.
    pause
    exit /b 1
)
for %%F in (part_00) do set Z0=%%~zF
for %%F in (part_01) do set Z1=%%~zF
for %%F in (part_02) do set Z2=%%~zF
echo   part_00 = %Z0% bytes
echo   part_01 = %Z1% bytes
echo   part_02 = %Z2% bytes
set /a ZT=%Z0%+%Z1%+%Z2%
echo   total   = %ZT% bytes  (expected 112618126)
echo.

REM ---------- 2. merge ----------
echo [2/4] Merging into IQmol-submodules.zip ...
if exist IQmol-submodules.zip del /f /q IQmol-submodules.zip
copy /b part_00 + part_01 + part_02 IQmol-submodules.zip >nul
if errorlevel 1 (
    echo   ERROR: merge failed.
    pause
    exit /b 1
)
for %%F in (IQmol-submodules.zip) do set ZF=%%~zF
echo   Done: %ZF% bytes
echo.

REM ---------- 3. verify ----------
echo [3/4] Verifying...
if not "%ZF%"=="112618126" (
    echo   FAILED: size mismatch.
    echo   expected 112618126, got %ZF%
    echo   Re-download the incomplete split file.
    pause
    exit /b 1
)
echo   size OK: 112618126 bytes

set HASH=
for /f "skip=1 tokens=1" %%H in ('certutil -hashfile IQmol-submodules.zip MD5') do (
    if not defined HASH set HASH=%%H
)
echo   MD5: %HASH%
if /i not "%HASH%"=="787d6023c5ec715ec0334427da4baa75" (
    echo.
    echo   FAILED: MD5 mismatch.
    echo   expected 787d6023c5ec715ec0334427da4baa75
    echo   Re-download the incomplete split file.
    pause
    exit /b 1
)
echo   MD5 OK: 787d6023c5ec715ec0334427da4baa75
echo.

REM ---------- 4. extract (optional) ----------
set "DEST=%~1"
if "%DEST%"=="" goto :noextract

echo [4/4] Extracting to %DEST% ...
if not exist "%DEST%" (
    echo   ERROR: folder does not exist: %DEST%
    pause
    exit /b 1
)
tar -xf IQmol-submodules.zip -C "%DEST%"
if errorlevel 1 (
    echo.
    echo   tar failed. Try manually:
    echo     Expand-Archive in PowerShell, or right click -^> Extract All
    pause
    exit /b 1
)
echo   Done.
echo.
echo   Next step:
echo     cd /d "%DEST%"
echo     scripts\build_windows.bat
echo.
pause
exit /b 0

:noextract
echo [4/4] Skipped extraction (no target folder given).
echo.
echo   Merge is complete: %CD%\IQmol-submodules.zip
echo.
echo   To extract automatically, run:
echo     "%~nx0" "D:\path\to\IQmol-for-Chinese"
echo.
echo   Or do it manually - extract to the REPOSITORY ROOT
echo   (not into modules\), so modules\ gets merged:
echo.
echo     PowerShell:  Expand-Archive -Path IQmol-submodules.zip -DestinationPath . -Force
echo     Explorer :  right click -^> Extract All -^> pick repo root -^> Yes to all
echo.
pause
exit /b 0
