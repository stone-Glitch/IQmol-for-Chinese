#!/bin/bash
# 扫描工具栏 y 带，找能真正弹出"元素周期表"的坐标
# 前置：Xvfb :99 + IQmol，**无 WM**
set -u
export DISPLAY=:99
MAIN=$(xdotool search --name '^IQmol$' | tail -1)
echo "MAIN=$MAIN"

close_pop() {
  xdotool search --name '元素周期表' 2>/dev/null | while read -r w; do
    xdotool windowclose "$w" 2>/dev/null
  done
  sleep 0.25
}
is_open() { xdotool search --name '元素周期表' 2>/dev/null | head -1 | grep -q . && return 0 || return 1; }

xdotool windowfocus "$MAIN" 2>/dev/null
sleep 0.4
close_pop

echo "扫描中 (x 180~330 step6, y 44~72 step4) ..."
for y in 44 48 52 56 58 60 64 68 72; do
  for x in $(seq 180 6 330); do
    close_pop
    xdotool mousemove "$x" "$y"
    sleep 0.08
    xdotool click 1
    sleep 0.35
    if is_open; then
      echo ">>> HIT: screen($x,$y) 打开了元素周期表"
      close_pop
      exit 0
    fi
  done
  echo "  y=$y扫完"
done
echo ">>> 未命中"
close_pop
