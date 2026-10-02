#!/usr/bin/env bash
# ============================================================================
# record_hero_clip.sh —— 录一段「精品演示片段」：连续平滑旋转，适合做正片素材
#
# 与 record_virtual_display.sh 的区别：那段是"一次性跑通"的验证版；
# 这段把旋转轨迹做成**慢速往返 + 轻微俯仰**，观感更像成片。
#
# 用法： ./record_hero_clip.sh [分子文件] [输出.mp4] [时长秒]
# ============================================================================
set -euo pipefail

MOL="${1:-/workspace/IQmol-for-Chinese/src/Parser/test/samples/viagra.xyz}"
OUT="${2:-/workspace/IQmol-for-Chinese/build-video/out/hero_viagra.mp4}"
DURATION="${3:-24}"
DISPLAY_NUM="${DISPLAY_NUM:-:99}"
GEOM="${GEOM:-1920x1080}"
FPS="${FPS:-25}"
VIEW_CX=1100; VIEW_CY=530
REPO="/workspace/IQmol-for-Chinese"
WORK="$REPO/build-video/out"
BIN="$REPO/build-video/IQmol"

export DISPLAY="$DISPLAY_NUM"
export LIBGL_ALWAYS_SOFTWARE=1 GALLIUM_DRIVER=llvmpipe
export QT_QPA_PLATFORM=xcb QT_XCB_GL_INTEGRATION=xcb_glx
export QT_AUTO_SCREEN_SCALE_FACTOR=0
export LANG=zh_CN.UTF-8 LC_ALL=zh_CN.UTF-8 LANGUAGE=zh_CN

pgrep -x openbox >/dev/null || { echo "[x] openbox 未运行"; exit 1; }
xdpyinfo -display "$DISPLAY_NUM" >/dev/null 2>&1 || { echo "[x] $DISPLAY_NUM 不可用"; exit 1; }

pkill -x IQmol 2>/dev/null || true; sleep 2
echo "[i] 载入 $MOL"
"$BIN" "$MOL" > "$WORK/logs/hero.log" 2>&1 &

for i in $(seq 1 60); do
  grep -q 'Loaded translation: "zh_CN"' "$WORK/logs/hero.log" 2>/dev/null \
    && xdotool search --name "^IQmol$" >/dev/null 2>&1 && break
  sleep 1
done
grep -q 'Loaded translation: "zh_CN"' "$WORK/logs/hero.log" && echo "[i] 中文已加载" || echo "[!] 中文未加载"
sleep 10

WID=$(xdotool search --name "^IQmol$" | tail -1)
xdotool windowactivate "$WID" 2>/dev/null || true; sleep 1
# 视图居中
xdotool mousemove $VIEW_CX $VIEW_CY; sleep 1
for _ in $(seq 1 6); do xdotool click 4; sleep 0.35; done
sleep 2

echo "[i] 录制 ${DURATION}s → $OUT"
ffmpeg -y -loglevel error -f x11grab -video_size "$GEOM" -framerate "$FPS" -i "${DISPLAY_NUM}.0" \
  -c:v libopenh264 -b:v 10M -pix_fmt yuv420p -t "$DURATION" "$OUT" &
REC=$!
sleep 3

# 平滑正弦往返：水平 ±170px，垂直 ±45px，一个完整周期约 22s
xdotool mousemove $VIEW_CX $VIEW_CY mousedown 1
STEPS=$(( DURATION * FPS * 8 / 10 ))
for i in $(seq 0 "$STEPS"); do
  T=$(awk -v i="$i" -v n="$STEPS" 'BEGIN{print i/n}')
  # 前 60% 走一个完整往返，后 40% 缓慢停下
  PH=$(awk -v t="$T" 'BEGIN{printf "%.5f", t*6.2831853*1.2}')
  X=$(awk -v p="$PH" -v c="$VIEW_CX" 'BEGIN{printf "%d", c + 170*sin(p)}')
  Y=$(awk -v p="$PH" -v c="$VIEW_CY" 'BEGIN{printf "%d", c + 45*sin(p*0.6)}')
  xdotool mousemove "$X" "$Y"
  sleep 0.038
done
xdotool mouseup 1
wait $REC 2>/dev/null || true

echo "[✓] $OUT"
ffprobe -v error -show_entries format=duration,size -of default=nw=1 "$OUT"
