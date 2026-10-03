#!/bin/bash
# S4A 录制：干净重启 IQmol -> 聚焦 -> 点击元素按钮 -> 校验popup -> 录制
# 关键经验：
#  1) 必须无窗口管理器（openbox 的装饰框会吃掉所有指针事件）
#  2) 无 WM 时 xdotool windowactivate 会失败，必须用 windowfocus
#  3) 不要用 windowclose 强杀 Qt::Popup，会破坏内部状态机
set -u
cd "$(dirname "$0")/../.."
export DISPLAY=:99
OUT=build-video/out/clip_4a_buildmol.mp4
mkdir -p build-video/out

echo "[1/5] 关闭旧实例"
pkill -x IQmol 2>/dev/null
sleep 2

echo "[2/5] 启动干净实例 (无 WM)"
setsid env DISPLAY=:99 LANG=zh_CN.UTF-8 LC_ALL=zh_CN.UTF-8 \
  LIBGL_ALWAYS_SOFTWARE=1 GALLIUM_DRIVER=llvmpipe \
  QT_QPA_PLATFORM=xcb QT_XCB_GL_INTEGRATION=xcb_glx \
  ./build-video/IQmol src/Parser/test/samples/viagra.xyz > /tmp/iqmol_rec.log 2>&1 &
sleep 12

MAIN=$(xdotool search --name '^IQmol$' | tail -1)
echo "    MAIN=$MAIN"
[ -z "$MAIN" ] && { echo "启动失败"; exit 1; }
xdotool windowmove "$MAIN" 0 0 2>/dev/null
xdotool windowsize "$MAIN" 1920 1080 2>/dev/null
sleep 3
xdotool windowfocus "$MAIN" 2>/dev/null
sleep 0.5
echo "    焦点=$(xdotool getwindowfocus 2>&1)  指针落点=$(xdotool getmouselocation 2>&1)"

echo "[3/5] 定位并点击元素选择按钮"
FOUND=""
for y in 58 56 60 54 62 52 64 50 66; do
  for x in 262 266 270 258 274 254 278 250 282; do
    xdotool mousemove "$x" "$y"; sleep 0.08
    xdotool click 1; sleep 0.5
    if xdotool search --name '元素周期表' 2>/dev/null | head -1 | grep -q .; then
      FOUND="$x,$y"; break 2
    fi
  done
done

if [ -z "$FOUND" ]; then
  echo "    !! 点击未触发 popup，尝试菜单栏路径"
  # 备用：Build 菜单 -> 选元素
  for mx in 215 220 210 225 205; do
    xdotool mousemove "$mx" 34; sleep 0.15; xdotool click 1; sleep 0.6
    img=/tmp/menu_$mx.png
    import -window root "$img"
    # 下拉菜单出现（画布区变白）
    python3 -c "
from PIL import Image
im=Image.open('$img').convert('RGB'); px=im.load()
w=sum(1 for x in range(0,500,3) for y in range(40,300,3) if px[x,y]==(255,255,255))
print(w)
" 2>/dev/null | grep -qE '^[1-9]' && { FOUND="menu:$mx"; break; }
    xdotool key Escape; sleep 0.2
  done
fi

if [ -z "$FOUND" ]; then
  echo "    仍然失败，保存诊断截图后退出"
  import -window root /tmp/fail_state.png
  xdotool search --name '.' 2>/dev/null | while read -r w; do
    echo "win $w '$(xdotool getwindowname "$w" 2>/dev/null)'"
  done
  exit 2
fi
echo "    命中坐标: $FOUND"

echo "[4/5] 录制 8 秒"
rm -f "$OUT"
ffmpeg -y -f x11grab -framerate 25 -video_size 1920x1080 -i :99 \
  -t 8 -pix_fmt yuv420p -c:v libopenh264 -preset veryfast -crf 26 "$OUT" \
  > /tmp/rec4a.log 2>&1 &
FF=$!
sleep 2.5
# 悬停到周期表内一个元素，制造"可交互"观感
xdotool mousemove 240 150; sleep 1.2
xdotool mousemove 262 58;  sleep 1.0
wait $FF

echo "[5/5] 校验"
ffprobe -v error -show_entries format=duration -of csv=p=0 "$OUT"
ffmpeg -y -ss 5 -i "$OUT" -frames:v 1 /tmp/verify_4a.png 2>/dev/null
python3 -c "
from PIL import Image
im=Image.open('/tmp/verify_4a.png').convert('RGB')
cols=im.getcolors(maxcolors=200000); cols.sort(reverse=True)
tot=im.size[0]*im.size[1]
print('  画面主色:')
for n,c in cols[:4]: print(f'    {c}  {n*100//tot}%')
"
ls -la "$OUT"
echo "OK"
