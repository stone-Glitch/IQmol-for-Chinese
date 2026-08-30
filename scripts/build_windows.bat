@echo off
REM =============================================================================
REM  IQmol-for-Chinese  Windows one-click build  (produces IQmol.exe)
REM
REM  Builds IQmol.exe under MSYS2 + MinGW-w64, then:
REM    1) generates zh_CN.qm (Chinese UI)
REM    2) packages Qt runtime via windeployqt
REM    3) copies OpenBabel data files
REM
REM  IMPORTANT - read before running:
REM  A) Use CMake 3.x (3.27~3.31), NOT 4.x.
REM     This codebase (2022-2024) declares cmake_minimum_required < 3.5 in
REM     several submodules and uses "cmake_policy(SET CMP0042 OLD)" in OpenBabel.
REM     CMake 4.0+ removes compatibility with < 3.5 and forbids OLD for CMP0042,
REM     so the configure step WILL fail hard on CMake 4.x.
REM     Get the official portable CMake 3.31 (zip, no install) from cmake.org,
REM     unzip it, and put its bin/ FIRST on PATH before running this script.
REM  B) Build in a SHORT, ASCII-ONLY path (e.g. D:\iqmol).
REM     Windows 260-char path limit + non-ASCII chars => "file name too long"
REM     errors deep inside the submodule trees. Avoid paths like D:\desktop\hanhua.
REM  C) Extract IQmol-submodules.tar.gz into repo root first (modules/ with 9 dirs),
REM     then extract IQmol-openbabel-deps.tar.gz into modules\openbabel\ (adds external/).
REM
REM  Prereqs (MINGW64 terminal, once):
REM    pacman -S --needed mingw-w64-x86_64-gcc mingw-w64-x86_64-cmake ^
REM      mingw-w64-x86_64-make mingw-w64-x86_64-qt5-base mingw-w64-x86_64-qt5-tools ^
REM      mingw-w64-x86_64-boost mingw-w64-x86_64-openssl mingw-w64-x86_64-zlib
REM
REM  Usage: from repo root in MINGW64:  scripts\build_windows.bat
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

REM ---- CMake version gate (warn on 4.x) ----
for /f "tokens=3" %%v in ('cmake --version 2^>nul ^| findstr /i "version"') do set "CMAKE_VER=%%v"
set "CMAKE_MAJOR=%CMAKE_VER:~0,1%"
if "%CMAKE_MAJOR%"=="4" (
  echo [WARN] Detected CMake %CMAKE_VER% (4.x). This project's submodules use
  echo [WARN] cmake_minimum_required ^< 3.5 and OpenBabel uses CMP0042 OLD, both of
  echo [WARN] which CMake 4.0+ rejects. Configure will likely FAIL.
  echo [WARN] Recommended: use portable CMake 3.31 (unzip, put bin/ first on PATH).
  echo.
) else if "%CMAKE_MAJOR%"=="5" (
  echo [WARN] Detected CMake %CMAKE_VER% (5.x) - same 3.5/CMP0042 incompatibility as 4.x.
  echo [WARN] Recommended: use portable CMake 3.31.
  echo.
) else (
  echo [OK] CMake %CMAKE_VER% (3.x is what this project expects)
  echo.
)

REM ---- check submodules extracted ----
if not exist "%ROOT%\modules\openbabel" (
  echo [ERROR] modules\openbabel not found. Extract IQmol-submodules.tar.gz into repo root first.
  exit /b 1
)

REM ---- check OpenBabel external deps (offline build) ----
set "OBEXT=%ROOT%\modules\openbabel\external"
set "MISSING_DEPS=0"
if not exist "%OBEXT%\maeparser-v1.2.3\maeparser\CMakeLists.txt" set "MISSING_DEPS=1"
if not exist "%OBEXT%\coordgen-master\coordgen\CMakeLists.txt"   set "MISSING_DEPS=1"
if not exist "%OBEXT%\rapidjson-1.1.0\CMakeLists.txt"            set "MISSING_DEPS=1"
if "%MISSING_DEPS%"=="1" (
  echo [WARN] OpenBabel build-time deps missing under modules\openbabel\external\
  echo [WARN] (maeparser / coordgen / rapidjson). Without them CMake will try to
  echo [WARN] download them from github.com at build time (needs good network).
  echo [WARN] Recommended: extract IQmol-openbabel-deps.tar.gz into modules\openbabel\
  echo.
)

REM ---- short/ASCII path hint ----
set "PLEN=0" & set "PT=%ROOT%"
:plen
if defined PT ( set "PT=!PT:~1!" & set /a PLEN+=1 & goto plen )
if %PLEN% GTR 40 (
  echo [WARN] Repo path is long (%PLEN% chars). If you hit "file name too long",
  echo [WARN] move the repo to a short ASCII path (e.g. D:\iqmol) and rebuild.
  echo.
)

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
    echo [ERROR] CMake configure failed. If it mentions CMP0042 / cmake_minimum_required,
    echo [ERROR] you are on CMake 4.x - switch to portable CMake 3.31 and retry.
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

REM ---- generate zh_CN.qm (try lrelease, then lrelease-qt5) ----
echo.
echo ==^> generating zh_CN.qm ...
set "LR="
where lrelease >nul 2>nul && set "LR=lrelease"
if not defined LR ( where lrelease-qt5 >nul 2>nul && set "LR=lrelease-qt5" )
if defined LR (
    if not exist "%EXEDIR%translations" mkdir "%EXEDIR%translations"
    %LR% "%ROOT%\translations\zh_CN.ts" -qm "%EXEDIR%translations\zh_CN.qm"
    echo [OK] zh_CN.qm -^> %EXEDIR%translations\
) else (
    if exist "%ROOT%\translations\zh_CN.qm" (
        if not exist "%EXEDIR%translations" mkdir "%EXEDIR%translations"
        copy /y "%ROOT%\translations\zh_CN.qm" "%EXEDIR%translations\zh_CN.qm" >nul
        echo [OK] copied bundled zh_CN.qm
    ) else (
        echo [WARN] lrelease/lrelease-qt5 not found and no bundled qm; UI will be English.
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
    echo [OK] OpenBabel data -^> %EXEDIR%share\
) else (
    echo [WARN] modules\openbabel\data missing, OpenBabel formats may not work.
)

echo.
echo ============================================================
echo   Build done!
echo   executable: %EXE%
echo   Ship the exe together with all DLLs and translations\ share\.
echo ============================================================
endlocal
