@echo off
REM =============================================================================
REM  IQmol-for-Chinese  Windows one-click build script  (produces IQmol.exe)
REM
REM  Builds IQmol.exe under MSYS2 + MinGW-w64, then:
REM    1) generates zh_CN.qm (Chinese localization)
REM    2) packages Qt runtime via windeployqt
REM    3) copies OpenBabel data files
REM
REM  Prereqs (install once in MINGW64 terminal):
REM    pacman -S --needed mingw-w64-x86_64-gcc mingw-w64-x86_64-cmake ^
REM      mingw-w64-x86_64-make mingw-w64-x86_64-qt5-base mingw-w64-x86_64-qt5-tools ^
REM      mingw-w64-x86_64-boost mingw-w64-x86_64-openssl mingw-w64-x86_64-zlib ^
REM      mingw-w64-x86_64-hdf5
REM
REM  Usage: run  .\scripts\build_windows.bat  from repo root in MINGW64.
REM =============================================================================
setlocal enabledelayedexpansion

REM ---- locate repo root (script lives under scripts/) ----
set "ROOT=%~dp0.."
for %%I in ("%ROOT%") do set "ROOT=%%~fI"

echo ============================================================
echo   IQmol-for-Chinese  Windows build
echo   repo root: %ROOT%
echo ============================================================
echo.

REM ---- check MinGW env ----
where cmake >nul 2>nul || ( echo [ERROR] cmake not found. Run in MSYS2 MINGW64 and install deps first. & exit /b 1 )
where mingw32-make >nul 2>nul || ( echo [ERROR] mingw32-make not found. Make sure you are in MINGW64 env. & exit /b 1 )
where lrelease >nul 2>nul || ( echo [WARN] lrelease not found, UI will fall back to English. Install mingw-w64-x86_64-qt5-tools. )
echo.

REM ---- clean & create build dir ----
set "BUILD=%ROOT%\build_win"
if exist "%BUILD%" (
    echo ==^> cleaning old build dir...
    rmdir /s /q "%BUILD%"
)
mkdir "%BUILD%"

REM ---- configure CMake ----
echo ==^> running CMake configure...
cd /d "%BUILD%"
cmake -G "MinGW Makefiles" ^
    -DCMAKE_BUILD_TYPE=Release ^
    -DCMAKE_MAKE_PROGRAM=mingw32-make ^
    "%ROOT%"
if errorlevel 1 (
    echo [ERROR] CMake configure failed, check dependencies.
    exit /b 1
)

REM ---- compile ----
echo.
echo ==^> compiling (-j parallel, please wait)...
mingw32-make -j%NUMBER_OF_PROCESSORS%
if errorlevel 1 (
    echo [ERROR] build failed.
    exit /b 1
)

REM ---- locate exe ----
set "EXE="
if exist "%BUILD%\IQmol.exe" set "EXE=%BUILD%\IQmol.exe"
if exist "%BUILD%\bin\IQmol.exe" set "EXE=%BUILD%\bin\IQmol.exe"
if "%EXE%"=="" (
    echo [ERROR] IQmol.exe not found.
    exit /b 1
)
echo.
echo ==^> executable: %EXE%

for %%I in ("%EXE%") do set "EXEDIR=%%~dpI"

REM ---- generate zh_CN.qm ----
echo.
echo ==^> generating zh_CN.qm ...
where lrelease >nul 2>nul
if not errorlevel 1 (
    if not exist "%EXEDIR%translations" mkdir "%EXEDIR%translations"
    lrelease "%ROOT%\translations\zh_CN.ts" -qm "%EXEDIR%translations\zh_CN.qm"
    echo [OK] zh_CN.qm -> %EXEDIR%translations\
) else (
    if exist "%ROOT%\translations\zh_CN.qm" (
        if not exist "%EXEDIR%translations" mkdir "%EXEDIR%translations"
        copy /y "%ROOT%\translations\zh_CN.qm" "%EXEDIR%translations\zh_CN.qm" >nul
        echo [OK] copied bundled zh_CN.qm
    )
)

REM ---- windeployqt ----
echo.
echo ==^> packaging Qt runtime...
where windeployqt >nul 2>nul
if not errorlevel 1 (
    windeployqt --release --no-translations --no-compiler-runtime "%EXE%"
    echo [OK] Qt runtime packaged
) else (
    echo [WARN] windeployqt not found, copy Qt DLLs manually.
)

REM ---- copy OpenBabel data ----
echo.
echo ==^> copying OpenBabel data...
if exist "%ROOT%\modules\openbabel\data" (
    if not exist "%EXEDIR%share" mkdir "%EXEDIR%share"
    xcopy /e /i /y "%ROOT%\modules\openbabel\data" "%EXEDIR%share\openbabel" >nul
    echo [OK] OpenBabel data -> %EXEDIR%share\
) else (
    echo [WARN] modules\openbabel\data missing, run: git submodule update --init --recursive
)

echo.
echo ============================================================
echo   Build done!
echo   executable: %EXE%
echo   Ship the exe together with all DLLs and translations\ share\.
echo ============================================================
endlocal
