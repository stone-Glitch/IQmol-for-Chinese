# =============================================================================
#  IQmol-for-Chinese 仓库拉取脚本 (Windows PowerShell)
#
#  用途: 一键克隆含子模块的 IQmol 汉化仓库到本地。
#  用法: 在 PowerShell 中执行  .\scripts\clone_repo.ps1
# =============================================================================
param(
    [string]$RepoUrl = "https://github.com/stone-Glitch/IQmol-for-Chinese.git",
    [string]$Dest = "IQmol-for-Chinese"
)

Write-Host "==> 目标仓库: $RepoUrl"
Write-Host "==> 本地目录: $Dest"
Write-Host ""

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Error "未找到 git，请先安装 Git for Windows: https://git-scm.com/download/win"
    exit 1
}

# 目标已存在则拉取更新并同步子模块
if (Test-Path (Join-Path $Dest ".git")) {
    Write-Host "==> 检测到已存在的仓库，改为拉取最新并同步子模块..."
    git -C $Dest pull --ff-only
    git -C $Dest submodule update --init --recursive
    Write-Host ""
    Write-Host "✅ 更新完成: $Dest"
    exit 0
}

Write-Host "==> 克隆仓库（含子模块，首次较慢请耐心等待）..."
git clone --recursive $RepoUrl $Dest
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ""
Write-Host "✅ 克隆完成: $Dest"
Write-Host ""
Write-Host "下一步（编译前先安装依赖，详见 doc/构建说明-中文版.md）:"
Write-Host "  cd $Dest"
Write-Host "  .\scripts\build_windows.bat    # 产出 IQmol.exe"
