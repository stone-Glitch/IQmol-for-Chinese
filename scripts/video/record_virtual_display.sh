#!/usr/bin/env bash
# ============================================================================
# 虚拟窗口录屏 —— Xvfb + llvmpipe 软件渲染 + openbox，无需显卡/物理显示器
#
# 本脚本是**实测跑通**的方案（2026-10-02），关键点全部踩过坑：
#   1. 必须有窗口管理器（openbox），否则 Qt 的 resize 请求不生效，
#      窗口会保持上次尺寸（表现为只占屏幕左上角一块）。
#   2. 不要设 QT_XCB_GL_INTEGRATION=none，那会禁用 GLX，Qt 建不出 GL 上下文。
#   3. 用 LANG/LC_ALL/LANGUAGE=zh_CN 强制中文；仅靠系统 locale 可能回退英文。
#   4. setlocale 后 IQmol 的日志会出现 `[i18n] Loaded translation: "zh_CN"`，
#      这是「中文已生效」的权威标志（不要靠肉眼看界面判断）。
#   5. Xvfb/openbox 必须用 run_in_background 常驻，普通 `&` 会随工具会话被回收。
#
# 用法：
#   ./record_virtual_display.sh <分子文件> <输出.mp4> [时长秒]
# 示例：
#   ./record_virtual_display.sh samples/viagra.xyz out/demo.mp4 15
# ============================================================================
set -euo pipefail

MOL="${1:?用法: $0 <分子文件> <输出.mp4> [时长秒]}"
OUT="${2:?缺少输出路径}"
DURATION="${3:-15}"
GEOM="${GEOM:-1920x1080}"
DISPLAY_NUM="${DISPLAY_NUM:-:99}"
FPS="${FPS:-25}"
VIEW_CX="${VIEW_CX:-1100}"   # 3D 视图区中心 X（左栏约 300px 宽）
VIEW_CY="${VIEW_CY:-530}"    # 3D 视图区中心 Y（工具栏约 60px 高）
ZOOM_TICKS="${ZOOM_TICKS:-6}"

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BIN="${IQMOL_BIN:-$REPO/build-video/IQmol}"
WORK="$REPO/build-video/out"
mkdir -p "$(dirname "$OUT")" "$WORK/shots" "$WORK/logs"

export DISPLAY="$DISPLAY_NUM"
# ---- 软件渲染 + GLX（关键：不要禁用 GLX）----
export LIBGL_ALWAYS_SOFTWARE=1
export GALLIUM_DRIVER=llvmpipe
export QT_QPA_PLATFORM=xcb
export QT_XCB_GL_INTEGRATION=xcb_glx
export QT_AUTO_SCREEN_SCALE_FACTOR=0
# ---- 强制简体中文 ----
export LANG=zh_CN.UTF-8 LC_ALL=zh_CN.UTF-8 LANGUAGE=zh_CN

# ---- 0. 前置检查 ----
for t in Xvfb openbox xdotool import ffmpeg; do
  command -v "$t" >/dev/null || { echo "[x] 缺少工具: $t"; exit 1; }
done
[[ -x "$BIN" ]] || { echo "[x] 二进制不存在: $BIN（先构建：cd build-video && make -j\$(nproc)）"; exit 1; }
[[ -f "$MOL" ]] || { echo "[x] 分子文件不存在: $MOL"; exit 1; }

# ---- 1. 显示与窗口管理器 ----
if ! xdpyinfo -display "$DISPLAY_NUM" >/dev/null 2>&1; then
  echo "[x] $DISPLAY_NUM 不可用。请先在独立后台任务中常驻启动："
  echo "      exec Xvfb $DISPLAY_NUM -screen 0 ${GEOM}x24 -nolisten tcp"
  exit 1
fi
if ! pgrep -x openbox >/dev/null 2>&1; then
  echo "[x] openbox 未运行。请在独立后台任务中常驻启动："
  echo "      DISPLAY=$DISPLAY_NUM openbox --sm-disable"
  exit 1
fi
xdpyinfo -display "$DISPLAY_NUM" | grep -q "dimensions: *${GEOM}" \
  || echo "[!] 警告：虚拟屏尺寸与期望 $GEOM 不一致，实际：$(xdpyinfo -display "$DISPLAY_NUM" | grep dimensions)"

# ---- 2. 启动 IQmol 载入分子 ----
pkill -x IQmol 2>/dev/null || true
sleep 2
echo "[i] 启动 IQmol，载入 $MOL"
"$BIN" "$MOL" > "$WORK/logs/iqmol.log" 2>&1 &
APP_PID=$!

# ---- 3. 等窗口就绪 + 确认中文已加载 ----
for i in $(seq 1 60); do
  if grep -q '\[i18n\] Loaded translation: "zh_CN"' "$WORK/logs/iqmol.log" 2>/dev/null \
     && xdotool search --name "^IQmol$" >/dev/null 2>&1; then
    echo "[i] 窗口就绪 + 中文已加载（${i}s）"
    break
  fi
  sleep 1
done
grep -q '\[i18n\] Loaded translation: "zh_CN"' "$WORK/logs/iqmol.log" \
  || echo "[!] 警告：未在日志中看到 zh_CN 加载标志，界面可能是英文！"
sleep 8   # 等分子渲染完（大 PDB 需更久）

WID=$(xdotool search --name "^IQmol$" | tail -1)
echo "[i] 窗口 $WID  尺寸 $(xdotool getwindowgeometry "$WID" | grep -o '[0-9]*x[0-9]*')"
xdotool windowactivate "$WID" 2>/dev/null || true
sleep 1

# ---- 4. 视图居中：在视图区中心滚轮放大 ----
xdotool mousemove "$VIEW_CX" "$VIEW_CY"
sleep 1
for _ in $(seq 1 "$ZOOM_TICKS"); do xdotool click 4; sleep 0.35; done
sleep 2
import -window root "$WORK/shots/frame_before.png" 2>/dev/null || true

# ---- 5. 录制 + 鼠标拖拽旋转 ----
echo "[i] 录制 ${DURATION}s @ ${FPS}fps → $OUT"
ffmpeg -y -loglevel error -f x11grab -video_size "$GEOM" -framerate "$FPS" -i "${DISPLAY_NUM}.0" \
  -c:v libopenh264 -b:v 8M -pix_fmt yuv420p -t "$DURATION" "$OUT" &
REC_PID=$!
sleep 2

# 水平拖拽一圈半，回到接近原始朝向
xdotool mousemove "$VIEW_CX" "$VIEW_CY" mousedown 1
X0="$VIEW_CX"
for dx in 60 140 220 280 320 340 330 300 250 190 130 80 40 -10 -50 -70 -60 -30 20 70 120 160 180 160 120 70 20 -30 -70 -90 -70 -30 20 60 90 80 50 10 -30 -60; do
  xdotool mousemove $((X0 + dx)) $((VIEW_CY + 10))
  sleep 0.28
done
xdotool mouseup 1
wait "$REC_PID" 2>/dev/null || true

import -window root "$WORK/shots/frame_after.png" 2>/dev/null || true
echo "[✓] 完成：$OUT"
ls -la "$OUT"
ffprobe -v error -show_entries format=duration,size -show_entries stream=width,height,codec_name \
  -of default=nw=1 "$OUT" 2>/dev/null | head -8
