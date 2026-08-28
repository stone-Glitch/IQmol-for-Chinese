@echo off
chcp 65001 >nul
REM =============================================================================
REM  IQmol-for-Chinese  国内镜像加速拉取脚本
REM
REM  功能: 通过国内镜像加速拉取仓库（含 9 个子模块），解决 git 直连 GitHub
REM        只有几十 KB/s 的问题。
REM
REM  原理: 使用 git 的 url.<base>.insteadOf 规则，把 github.com 的下载
REM        自动改写为镜像地址，主仓库和所有子模块都会生效。
REM
REM  用法: 双击运行，或在命令行执行  .\scripts\拉取加速.bat
REM =============================================================================
setlocal enabledelayedexpansion

echo ============================================================
echo   IQmol-for-Chinese  镜像加速拉取
echo ============================================================
echo.

REM ---- 可选镜像前缀（按顺序尝试，直到成功）----
set "MIRRORS=https://ghfast.top/ https://gh-proxy.com/"

where git >nul 2>nul
if errorlevel 1 (
    echo [错误] 未找到 git，请先安装 Git for Windows 或 MSYS2。
    pause
    exit /b 1
)

REM ---- 设置 git 使用镜像重写 github.com ----
REM 注意: 镜像前缀必须带完整 https://，否则 insteadOf 会漏掉协议导致 403
for %%M in (%MIRRORS%) do (
    echo ==> 尝试镜像: %%M
    git config --global url."%%Mhttps://github.com/".insteadOf "https://github.com/"
    REM 快速连通性测试（用完整前缀 URL）
    git ls-remote --heads "%%Mhttps://github.com/stone-Glitch/IQmol-for-Chinese.git" >nul 2>&1
    if not errorlevel 1 (
        echo [OK] 镜像 %%M 可用
        goto :clone
    )
    echo [跳过] 镜像 %%M 不可用，尝试下一个...
    git config --global --unset url."%%Mhttps://github.com/".insteadOf 2>nul
)

echo [错误] 所有镜像均不可用，请检查网络。
pause
exit /b 1

:clone
echo.
echo ==> 拉取主仓库（含子模块）...
git clone --recursive https://github.com/stone-Glitch/IQmol-for-Chinese.git
if errorlevel 1 (
    echo [错误] 克隆失败，请重试。
    pause
    exit /b 1
)

echo.
echo ============================================================
echo  拉取完成！仓库目录: IQmol-for-Chinese
echo
echo  提示: 已全局设置镜像加速，以后 git clone github 仓库都会走镜像。
echo        如需还原直连，执行:
echo          git config --global --unset-all url."https://ghfast.top/https://github.com/".insteadOf
echo          git config --global --unset-all url."https://gh-proxy.com/https://github.com/".insteadOf
echo ============================================================
pause
endlocal
