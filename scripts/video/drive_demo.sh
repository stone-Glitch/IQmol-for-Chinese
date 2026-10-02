#!/usr/bin/env bash
# ============================================================================
# drive_demo.sh —— 用 xdotool 驱动 IQmol 完成一段演示操作（供录屏时调用）
#
# 流程：载入分子 → 切换显示风格 → 打开对话框 → 展示菜单汉化
# 每个动作前后留出停顿，方便后期剪辑配字幕。
# ============================================================================
set -uo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SHOT_DIR="$REPO/build-video/out/shots"
mkdir -p "$SHOT_DIR"

# 坐标基于 1600x900 虚拟屏，按实际窗口布局微调
WIN_W=1600
WIN_H=900

shot() { import -window root "$SHOT_DIR/$1.png" 2>/dev/null && echo "  [shot] $1"; }
pause() { sleep "${1:-2}"; }

echo "[drive] 开始演示流程"

# 1. 通过命令行参数预先载入分子更稳；这里假定已用 `iqmol file.pdb` 启动
#    若为空视图，则用 File > Open 走一遍
pause 2
shot "02_before_action"

# 2. 打开 File 菜单（左上角）
xdotool key --clearmodifiers alt+f 2>/dev/null || true
pause 2
shot "03_file_menu"

# 3. 关闭菜单
xdotool key --clearmodifiers Escape
pause 1

# 4. 打开 Calculation 菜单（展示汉化菜单项）
#    用点击方式定位菜单位置（窗口左上角附近）
xdotool mousemove 150 40 click 1 2>/dev/null || true
pause 2
shot "04_calc_menu"
xdotool key --clearmodifiers Escape
pause 1

# 5. 打开 Display 菜单
xdotool mousemove 260 40 click 1 2>/dev/null || true
pause 2
shot "05_display_menu"
xdotool key --clearmodifiers Escape
pause 1

# 6. 打开 Preference/其它对话框（示例：View 菜单下的 Camera）
xdotool key --clearmodifiers ctrl+p 2>/dev/null || true
pause 3
shot "06_preferences"

echo "[drive] 演示流程结束"
