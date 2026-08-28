# =============================================================================
#  IQmol-for-Chinese 仓库拉取脚本 (Linux / macOS / 带 Git Bash 的 Windows)
#
#  用途: 一键克隆含子模块的 IQmol 汉化仓库到本地。
#        仓库地址: https://github.com/stone-Glitch/IQmol-for-Chinese
#
#  用法:
#    ./scripts/clone_repo.sh                 # 克隆到当前目录 IQmol-for-Chinese/
#    ./scripts/clone_repo.sh /path/to/dest   # 克隆到指定目录
# =============================================================================
#!/bin/bash
set -euo pipefail

REPO_URL="${IQMOL_REPO_URL:-https://github.com/stone-Glitch/IQmol-for-Chinese.git}"
DEST="${1:-IQmol-for-Chinese}"

echo "==> 目标仓库: $REPO_URL"
echo "==> 本地目录: $DEST"
echo

if ! command -v git >/dev/null 2>&1; then
    echo "错误: 未找到 git，请先安装 Git。"
    echo "  Ubuntu/Debian: sudo apt-get install git"
    echo "  macOS:         brew install git"
    exit 1
fi

# 若目标目录已存在且是仓库，则跳过克隆、只拉取更新并同步子模块
if [ -d "$DEST/.git" ]; then
    echo "==> 检测到已存在的仓库，改为拉取最新并同步子模块..."
    git -C "$DEST" pull --ff-only || true
    git -C "$DEST" submodule update --init --recursive
    echo
    echo "✅ 更新完成: $DEST"
    exit 0
fi

echo "==> 克隆仓库（含子模块，首次较慢请耐心等待）..."
git clone --recursive "$REPO_URL" "$DEST"

echo
echo "✅ 克隆完成: $DEST"
echo
echo "下一步（编译前先安装依赖，详见 doc/构建说明-中文版.md）:"
echo "  cd $DEST"
echo "  ./scripts/build_windows.bat    # Windows 下产出 IQmol.exe"
echo "  # 或 Linux/macOS 下:"
echo "  ./configure --release && cd build && make -j"
