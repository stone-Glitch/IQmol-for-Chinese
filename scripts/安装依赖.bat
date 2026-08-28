@echo off
chcp 65001 >nul
REM =============================================================================
REM  IQmol-for-Chinese  Windows 依赖一键安装脚本
REM
REM  功能: 将 MSYS2 安装到 D 盘，并自动安装编译 IQmol.exe 所需的全部依赖
REM        (MinGW-w64 编译器 + Qt5 + Boost + OpenSSL + zlib + HDF5)
REM
REM  特点:
REM   - 默认安装到 D:\msys64（不占用 C 盘空间）
REM   - 使用官方自解压归档，无需手动点击安装向导
REM   - 自动更新系统并安装依赖
REM
REM  用法: 右键「以管理员身份运行」本脚本，等待完成即可。
REM        完成后，双击 D:\msys64\mingw64.exe 进入 MINGW64 终端，
REM        再运行仓库内的 scripts\build_windows.bat 产出 IQmol.exe。
REM =============================================================================
setlocal enabledelayedexpansion

REM ---- 安装根目录（默认 D 盘，可改）----
set "MSYS2_ROOT=D:\msys64"

echo ============================================================
echo   IQmol-for-Chinese 依赖安装
echo   目标目录: %MSYS2_ROOT%
echo ============================================================
echo.

REM ---- 检查管理员权限（写 D 盘一般不需要，但更新系统建议管理员）----
net session >nul 2>&1
if errorlevel 1 (
    echo [提示] 建议以「管理员身份」运行本脚本，以确保系统更新顺利。
    echo         如未使用管理员权限，可能部分步骤失败。
    echo.
)

REM ---- 1. 检测是否已安装 ----
if exist "%MSYS2_ROOT%\usr\bin\bash.exe" (
    echo [跳过] 检测到 %MSYS2_ROOT% 已存在，跳过安装，直接进入依赖安装...
    goto :install_deps
)

REM ---- 2. 下载自解压归档 ----
echo ==> 下载 MSYS2 自解压归档（约 100MB，请耐心等待）...
set "DL=%TEMP%\msys2-base-x86_64-latest.sfx.exe"
set "URL=https://github.com/msys2/msys2-installer/releases/download/nightly-x86_64/msys2-base-x86_64-latest.sfx.exe"

REM 优先用 curl（Win10 1803+ 自带），失败则用 PowerShell
where curl >nul 2>nul
if not errorlevel 1 (
    curl -L --fail --output "%DL%" "%URL%"
) else (
    powershell -NoProfile -Command "[Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -UseBasicParsing -Uri '%URL%' -OutFile '%DL%'"
)
if not exist "%DL%" (
    echo [错误] 下载失败，请手动从 https://www.msys2.org/ 下载并安装到 %MSYS2_ROOT%
    pause
    exit /b 1
)

REM ---- 3. 解压到 D 盘根目录（自解压包内含 msys64 目录）----
echo.
echo ==> 解压到 D 盘 ...
if not exist "D:\" (
    echo [错误] 未检测到 D 盘，请修改脚本顶部 MSYS2_ROOT 变量为其它盘符。
    pause
    exit /b 1
)
REM 自解压归档内部结构为 msys64\...，解压到 D:\ 后得到 D:\msys64
"%DL%" -y -o"D:\"
if errorlevel 1 (
    echo [错误] 解压失败。
    pause
    exit /b 1
)
del /q "%DL%" >nul 2>nul

REM 校验实际解压路径
if exist "D:\msys64\usr\bin\bash.exe" set "MSYS2_ROOT=D:\msys64"

:install_deps

if not exist "%MSYS2_ROOT%\usr\bin\bash.exe" (
    echo [错误] 未在 %MSYS2_ROOT% 找到 bash.exe，安装失败。
    pause
    exit /b 1
)

set "BASH=%MSYS2_ROOT%\usr\bin\bash.exe"

REM ---- 4. 首次初始化 + 系统更新 ----
echo.
echo ==> 更新 MSYS2 系统（可能几分钟，如提示需重启终端会自动处理）...
"%BASH%" -lc "pacman --noconfirm -Syuu" 
"%BASH%" -lc "pacman --noconfirm -Syuu"

REM ---- 5. 安装编译依赖 ----
echo.
echo ==> 安装编译依赖（gcc/cmake/qt5/boost/openssl/zlib/hdf5）...
"%BASH%" -lc "pacman --noconfirm -S --needed mingw-w64-x86_64-gcc mingw-w64-x86_64-cmake mingw-w64-x86_64-make mingw-w64-x86_64-qt5-base mingw-w64-x86_64-qt5-tools mingw-w64-x86_64-boost mingw-w64-x86_64-openssl mingw-w64-x86_64-zlib mingw-w64-x86_64-hdf5 mingw-w64-x86_64-git"

if errorlevel 1 (
    echo [错误] 依赖安装失败，请检查网络后重试。
    pause
    exit /b 1
)

echo.
echo ============================================================
echo  安装完成！
echo
echo  MSYS2 位置: %MSYS2_ROOT%
echo
echo  下一步:
echo    1) 双击 %MSYS2_ROOT%\mingw64.exe 打开 MINGW64 终端
echo    2) 在终端中执行:
echo         git clone --recursive https://github.com/stone-Glitch/IQmol-for-Chinese.git
echo         cd IQmol-for-Chinese
echo         ./scripts/build_windows.bat
echo ============================================================
echo.
pause
endlocal
