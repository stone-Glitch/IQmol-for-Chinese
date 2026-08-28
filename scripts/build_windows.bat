@echo off
REM =============================================================================
REM  IQmol-for-Chinese  Windows 一键构建脚本 (产出 IQmol.exe)
REM
REM  功能: 在 MSYS2 + MinGW-w64 (64位) 环境下编译 IQmol.exe，并自动：
REM        1) 生成 zh_CN.qm（中文本地化）
REM        2) 用 windeployqt 打包 Qt 运行库
REM        3) 复制 OpenBabel 数据文件
REM        4) 产出可分发的 IQmol.exe
REM
REM  前置依赖（在 MSYS2 的 MINGW64 终端中安装一次）:
REM    pacman -S --needed ^
REM      mingw-w64-x86_64-gcc mingw-w64-x86_64-cmake mingw-w64-x86_64-make ^
REM      mingw-w64-x86_64-qt5-base mingw-w64-x86_64-qt5-tools ^
REM      mingw-w64-x86_64-boost mingw-w64-x86_64-openssl ^
REM      mingw-w64-x86_64-zlib mingw-w64-x86_64-hdf5
REM
REM  用法: 在 MINGW64 终端进入仓库根目录，执行  .\scripts\build_windows.bat
REM =============================================================================
setlocal enabledelayedexpansion

REM ---- 定位仓库根目录（脚本位于 scripts/ 下）----
set "ROOT=%~dp0.."
for %%I in ("%ROOT%") do set "ROOT=%%~fI"

echo ============================================================
echo   IQmol-for-Chinese  Windows 构建
echo   仓库根目录: %ROOT%
echo ============================================================
echo.

REM ---- 检查 MinGW 环境 ----
where cmake >nul 2>nul || ( echo [错误] 未找到 cmake，请在 MSYS2 MINGW64 终端中安装依赖后重试 & exit /b 1 )
where mingw32-make >nul 2>nul || ( echo [错误] 未找到 mingw32-make，请确认已在 MINGW64 环境 & exit /b 1 )
where lrelease >nul 2>nul || ( echo [警告] 未找到 lrelease，界面将回退英文；可用 pacman 安装 mingw-w64-x86_64-qt5-tools )
echo.

REM ---- 清理并创建构建目录 ----
set "BUILD=%ROOT%\build_win"
if exist "%BUILD%" (
    echo ==> 清理旧的构建目录...
    rmdir /s /q "%BUILD%"
)
mkdir "%BUILD%"

REM ---- 配置 CMake (MinGW Makefiles + Qt5) ----
echo ==> 运行 CMake 配置...
cd /d "%BUILD%"
cmake -G "MinGW Makefiles" ^
    -DCMAKE_BUILD_TYPE=Release ^
    -DCMAKE_MAKE_PROGRAM=mingw32-make ^
    "%ROOT%"
if errorlevel 1 (
    echo [错误] CMake 配置失败，请检查依赖是否安装完整。
    exit /b 1
)

REM ---- 编译 ----
echo.
echo ==> 编译（-j 并行，请耐心等待）...
mingw32-make -j%NUMBER_OF_PROCESSORS%
if errorlevel 1 (
    echo [错误] 编译失败。
    exit /b 1
)

REM ---- 定位可执行文件（优先根目录，其次 bin/ 子目录）----
set "EXE="
if exist "%BUILD%\IQmol.exe" set "EXE=%BUILD%\IQmol.exe"
if exist "%BUILD%\bin\IQmol.exe" set "EXE=%BUILD%\bin\IQmol.exe"
if "%EXE%"=="" (
    echo [错误] 未找到编译产物 IQmol.exe
    exit /b 1
)
echo.
echo ==> 可执行文件: %EXE%

REM ---- exe 所在目录（用于部署运行库与数据）----
for %%I in ("%EXE%") do set "EXEDIR=%%~dpI"

REM ---- 生成中文本地化 .qm（若 lrelease 存在）----
echo.
echo ==> 生成 zh_CN.qm ...
where lrelease >nul 2>nul
if not errorlevel 1 (
    if not exist "%EXEDIR%translations" mkdir "%EXEDIR%translations"
    lrelease "%ROOT%\translations\zh_CN.ts" -qm "%EXEDIR%translations\zh_CN.qm"
    echo [OK] zh_CN.qm 已生成到 %EXEDIR%translations\
) else (
    REM lrelease 缺失时，直接复制仓库里已提交的 qm 兜底
    if exist "%ROOT%\translations\zh_CN.qm" (
        if not exist "%EXEDIR%translations" mkdir "%EXEDIR%translations"
        copy /y "%ROOT%\translations\zh_CN.qm" "%EXEDIR%translations\zh_CN.qm" >nul
        echo [OK] 已复制仓库内 zh_CN.qm
    )
)

REM ---- windeployqt 打包 Qt 运行库 ----
echo.
echo ==> 用 windeployqt 打包 Qt 运行库...
where windeployqt >nul 2>nul
if not errorlevel 1 (
    windeployqt --release --no-translations --no-compiler-runtime "%EXE%"
    echo [OK] Qt 运行库已打包
) else (
    echo [警告] 未找到 windeployqt，请手动复制 Qt 的 DLL 到 exe 目录。
)

REM ---- 复制 OpenBabel 数据文件 ----
echo.
echo ==> 复制 OpenBabel 数据文件...
if exist "%ROOT%\modules\openbabel\data" (
    if not exist "%EXEDIR%share" mkdir "%EXEDIR%share"
    xcopy /e /i /y "%ROOT%\modules\openbabel\data" "%EXEDIR%share\openbabel" >nul
    echo [OK] OpenBabel 数据已复制到 %EXEDIR%share\
) else (
    echo [警告] 未找到 modules\openbabel\data，请先执行 git submodule update --init --recursive
)

echo.
echo ============================================================
echo  构建完成！
echo  可执行文件: %EXE%
echo  分发时请将 exe 同目录的所有 DLL 及 translations\ share\ 一并打包。
echo ============================================================
endlocal
