#!/bin/bash
# ============================================================================
# rec_segment4.sh —— 段4 三组素材重录（真实鼠标操作版）
#
# 与旧素材的差别：
#   ① 光标用 smoothstep 缓动移动（~1s 划过画面），不再瞬移；
#   ② 每次点击记录时间戳/坐标到 /tmp/iqmol_rec/clicks_X.txt，
#      供 annotate_segment4.sh 叠加波纹特效；
#   ③ 4c 真的切换渲染样式：空间填充 → 线框 → 球棍（画面有戏剧性变化）；
#   ④ 4a 真的选中"氧"（工具栏按钮 C → O，是可核验的状态变化）。
#
# 关键坐标（2026-10-02 实测，窗口 0,0 起 1920x1080，无 WM）：
#   菜单栏 y≈9：文件23 编辑63 显示103 构建140 计算183 帮助223
#   元素按钮 "C"：(267,55)；周期表 popup (10,30) 514x263，
#     O=(444,82) Fe=(224,135) Ag=(305,162) Br=(467,135)
#   计算→Q-Chem 设置：菜单项 (235,41)；对话框标题含 "QChem"
#
# ⚠️ 「配置分子」对话框（双击图层打开）在这套环境里**不能用**：
#   三个驱动（llvmpipe/softpipe/swrast）实测一致——对话框一打开，画布就永久
#   清空（分子区 std 22.8 → 0.0），点样式画面 Δ=0.00，Escape 关掉也不恢复。
#   换驱动、预热、重新拖拽都救不回来，别再在这条路上耗时间。
#   反面结论同样重要：**画布本身能重绘**——拖拽旋转 Δ=11.93、滚轮缩放 Δ=13.06，
#   分子全程可见。所以 4c 改成"拖拽旋转 + 滚轮缩放"，别去碰那个对话框。
#
# ⚠️ GL 驱动：llvmpipe 与 softpipe 实测表现**完全一致**（分子可见、UI 可点、
#   画布能重绘、只有配置对话框会毁掉画布），所以驱动之争到此为止，
#   保持 llvmpipe（启动快）。
#
# ⚠️ 另一个坑：启动后偶发画布只剩背景蓝、分子整个不画（GL context 坏死）。
#   对策：start_app 检测画布像素方差，空白则自动重启，最多 3 次。
# ============================================================================
set -u
# ⚠️ 所有 ffmpeg 调用都必须带 -nostdin。本脚本有多处 `while read ... done < 文件`
#    （缓动路径点、点击记录），循环里又有 ffmpeg（verify_clicks 抽帧）——
#    ffmpeg 子进程继承列表文件作 stdin，每跑一次就推进文件偏移，
#    下一轮 read 会少读首字符（路径丢开头的 /），set -u 下直接报错。
exec </dev/null
cd "$(dirname "$0")/../.."
export DISPLAY=:99
BIN=./build-video/IQmol
MOL=src/Parser/test/samples/viagra.xyz
OUT=build-video/out
REC=/tmp/iqmol_rec
mkdir -p "$REC" "$OUT"

FPS=25
DUR=8
# 4c 单独加长：录制期间 ffmpeg 抓屏吃 CPU，xdotool 实际耗时被拉长约 1.5 倍，
# 8 秒素材会把动作序列末尾的两次滚轮截掉（详见 take_c 里的注释）。
DUR_C=12

# ⚠️ 必须**无窗口管理器**运行。有 openbox 时 getwindowgeometry 返回的是
#    "带标题栏装饰的外框原点"，据此算对话框相对坐标会整体偏上一个标题栏高度，
#    点击全部落空（实测三次样式切换画面 MAE=0.00，等于没点）。
#    无 WM 时它返回的就是内容区原点，rel 偏移才准。
if pgrep -x openbox >/dev/null 2>&1; then
  echo "[i] 检测到 openbox，按无 WM 要求关闭它（否则对话框坐标会偏）"
  pkill -x openbox 2>/dev/null || true
  sleep 1
fi

# ---- 光标缓动：smoothstep 插值，默认 0.9s 移完全程 ----
# ⚠️ 路径点必须由**单个** python 进程一次性生成。
#    第一版在循环里每步起 3 个 python（算 u/x/y），45 步 = 135 次解释器启动，
#    0.9s 的移动实际跑了 5.7s，点击时间戳全部漂出 8s 素材范围。
ease() {  # x0 y0 x1 y1 [秒]
  local x0=$1 y0=$2 x1=$3 y1=$4
  local dur=${5:-0.9}
  python3 - "$x0" "$y0" "$x1" "$y1" "$dur" <<'EOF' > /tmp/ease_pts.txt
import sys
x0, y0, x1, y1, dur = map(float, sys.argv[1:6])
n = max(8, int(dur * 50))
dt = dur / n
for i in range(1, n + 1):
    t = i / n
    u = t * t * (3 - 2 * t)          # smoothstep 缓入缓出
    print(f"{x0 + (x1 - x0) * u:.0f} {y0 + (y1 - y0) * u:.0f} {dt:.3f}")
EOF
  local line
  while read -r x y dt; do
    DISPLAY=:99 xdotool mousemove "$x" "$y"
    sleep "$dt"
  done < /tmp/ease_pts.txt
}

# ---- 拖拽：按下 → 缓动划过 → 松开（旋转分子）----
# 路径点仍由单个 python 进程生成（见 ease() 的注释），mousedown 状态下
# mousemove 就是拖拽，鼠标不抬起画布就一直跟着转。
drag() {  # x0 y0 x1 y1 [秒]
  local x0=$1 y0=$2 x1=$3 y1=$4
  local dur=${5:-1.2}
  DISPLAY=:99 xdotool mousemove "$x0" "$y0"
  # ⚠️ 按下前必须让鼠标停稳：第一版只停 0.15s，紧接着的 mousedown 经常
  #    被吃掉（实测第一次拖拽 Δ=0.02，分子压根没转），后面几次却正常。
  sleep 0.35
  DISPLAY=:99 xdotool mousedown 1
  sleep 0.15          # 真实拖拽按下后都会顿一下，顺带让 Qt 收到 press
  python3 - "$x0" "$y0" "$x1" "$y1" "$dur" <<'EOF' > /tmp/drag_pts.txt
import sys
x0, y0, x1, y1, dur = map(float, sys.argv[1:6])
n = max(10, int(dur * 50)); dt = dur / n
for i in range(1, n + 1):
    t = i / n; u = t * t * (3 - 2 * t)
    print(f"{x0 + (x1 - x0) * u:.0f} {y0 + (y1 - y0) * u:.0f} {dt:.3f}")
EOF
  local x y dt
  while read -r x y dt; do
    DISPLAY=:99 xdotool mousemove "$x" "$y"
    sleep "$dt"
  done < /tmp/drag_pts.txt
  sleep 0.1
  DISPLAY=:99 xdotool mouseup 1
  # 记录拖拽起点，标注层据此在操作发生处叠波纹
  click_mark "$x0" "$y0"
}

# ---- 滚轮：4=放大 5=缩小 ----
wheel() {  # x y 格数 方向(4|5)
  local x=$1 y=$2 n=$3 dir=$4
  DISPLAY=:99 xdotool mousemove "$x" "$y"
  sleep 0.1
  click_mark "$x" "$y"
  local i
  for i in $(seq 1 "$n"); do
    DISPLAY=:99 xdotool click "$dir"
    sleep 0.12
  done
}

# ---- 带记录的点击：时间戳相对录制起点 ----
click_rec() {  # x y
  click_mark "$1" "$2"
  sleep 0.12
  DISPLAY=:99 xdotool click 1
}

# 只记时间戳不真的点击（拖拽/滚轮本身已经是"操作"了，
# 再补一发 click 反而像在乱点界面）
click_mark() {  # x y
  [ "${REC_ACTIVE:-0}" = 1 ] || return 0      # 彩排阶段不记录
  local t=$(python3 -c "import time;print(f'{time.time()-$T0:.3f}')")
  echo "$t $1 $2" >> "$REC/clicks_${TAKE}.txt"
}

# ---- 分子可见性检测：画布中心区像素方差，空白蓝布 std < 3，有分子 > 15 ----
molecule_visible() {
  ffmpeg -nostdin -v error -f x11grab -video_size 1920x1080 -i :99.0 -frames:v 1 \
    "$REC/vis_check.png" -y 2>/dev/null
  local s
  s=$(python3 -c "
from PIL import Image; import numpy as np
im = np.asarray(Image.open('$REC/vis_check.png').convert('L').crop((600,400,1600,800)))
print(f'{im.std():.1f}')")
  python3 -c "exit(0 if $s > 15 else 1)"
}

# ---- 清洁重启 IQmol（中文界面，窗口 0,0 1920x1080，无 WM）----
# 带 GL 失败重试：画布空白（分子没画出来）就整个重启，最多 3 次
start_app() {
  local try
  for try in 1 2 3; do
    pkill -x IQmol 2>/dev/null || true
    sleep 2
    # ⚠️ 光 pkill 不够：IQmol 若非正常退出，X 里会留下僵尸窗口
    #    （实测残留了一个"元素周期表" popup，正好盖住 4a 的点击点 444,82，
    #     导致后续所有点击被它吃掉——素材里表现为"点了没反应"）。
    #    必须显式 windowkill 掉。
    local zw
    for zw in $(DISPLAY=:99 xdotool search --name 'IQmol|配置分子|元素周期表|QChem' 2>/dev/null); do
      DISPLAY=:99 xdotool windowkill "$zw" 2>/dev/null || true
    done
    sleep 0.5
    setsid env DISPLAY=:99 LANG=zh_CN.UTF-8 LC_ALL=zh_CN.UTF-8 LANGUAGE=zh_CN \
      LIBGL_ALWAYS_SOFTWARE=1 GALLIUM_DRIVER=llvmpipe \
      QT_QPA_PLATFORM=xcb QT_XCB_GL_INTEGRATION=xcb_glx \
      QT_AUTO_SCREEN_SCALE_FACTOR=0 \
      "$BIN" "$MOL" > /tmp/iqmol_rec.log 2>&1 &
    local ok=0
    for i in $(seq 1 40); do
      if grep -q 'Loaded translation: "zh_CN"' /tmp/iqmol_rec.log 2>/dev/null \
         && DISPLAY=:99 xdotool search --name '^IQmol$' >/dev/null 2>&1; then ok=1; break; fi
      sleep 1
    done
    [ $ok -eq 1 ] || { echo "[x] IQmol 启动失败"; exit 1; }
    local WID=$(DISPLAY=:99 xdotool search --name '^IQmol$' | tail -1)
    DISPLAY=:99 xdotool windowmove "$WID" 0 0 2>/dev/null
    DISPLAY=:99 xdotool windowsize "$WID" 1920 1080 2>/dev/null
    sleep 3
    DISPLAY=:99 xdotool windowfocus "$WID" 2>/dev/null
    # softpipe 很慢，死等 5s 不够——循环等多达 20s，分子一出现就走
    local i
    for i in $(seq 1 20); do
      molecule_visible && break
      sleep 1
    done
    if molecule_visible; then
      # ⚠️ 分子可见 ≠ GL 完全就绪。分子刚画出来时 GL 资源还在初始化，
      #    这时候发出的第一次交互会被吞掉——实测 4c 的第一次拖拽
      #    Δ=0.02（分子压根没转），等几秒后的第二、三次拖拽都正常。
      sleep 3
      echo "    IQmol 就绪（第${try}次启动，分子可见 + GL 预热 3s）"
      return 0
    fi
    echo "    [!] 第${try}次启动画布空白（GL 渲染失败），重启重试…"
  done
  echo "[x] 连续 3 次启动都没能拿到可用画面，放弃"; exit 1
}

# ---- 开始一段录制：ffmpeg 后台跑 DUR 秒，T0 为录制零点 ----
begin_take() {  # take名 [时长]
  TAKE=$1
  local dur=${2:-$DUR}
  rm -f "$REC/clicks_${TAKE}.txt"
  ffmpeg -nostdin -y -loglevel error -f x11grab -video_size 1920x1080 \
    -framerate $FPS -i :99.0 -t "$dur" -pix_fmt yuv420p \
    -c:v libopenh264 -preset veryfast -crf 24 "$OUT/clip_4${TAKE}_new.mp4" &
  FFPID=$!
  # ⚠️ T0 必须在 ffmpeg 启动瞬间取——素材时间轴从抓帧那一刻开始算，
  #    若放在 settle sleep 之后，所有点击时间会整体偏早 0.4s。
  T0=$(python3 -c "import time;print(time.time())")
  LAST_CLICK_T=0
  sleep 0.4
}

end_take() {
  wait $FFPID 2>/dev/null || true
  local d=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$OUT/clip_4${TAKE}_new.mp4")
  echo "    clip_4${TAKE}_new.mp4  ${d}s  点击 $(wc -l < "$REC/clicks_${TAKE}.txt") 次"
}

# ---- 校验：所有点击时刻都落在素材时长内 ----
#踩过的坑：录制时 xdotool 被 ffmpeg 拖慢，点击时刻比预算晚（11.7s vs 理论 7.9s），
#    而素材只有 8 秒 → 末尾点击被截断。画面看不出异常，但那些点击的
#    波纹落在素材之外，等于白录。verify_clicks 查不出这个（它只看
#    素材内的帧），所以必须单独按时间戳自查。
check_clicks_in_range() {  # take名 时长
  local f="$REC/clicks_$1.txt" bad=0
  [ -s "$f" ] || { echo "    [i] 无点击记录，跳过时长自查"; return 0; }
  local t x y
  while read -r t x y; do
    if (( $(python3 -c "print(1 if $t > $2 else 0)") )); then
      echo "    [!] 点击时刻 ${t}s 超出素材时长 ${2}s（落点 $x,$y）——该动作被截掉了"
      bad=1
    fi
  done < "$f"
  [ $bad = 0 ] && echo "    [x] 时长自查通过：所有点击都在 ${2}s 内"
  return 0
}

# ---- 校验：每次点击前后画面是否真的变了 ----
# 踩过的坑：坐标算错时 xdotool "点"了，但样式压根没切，
# 抽帧看才发现三次切换的画面差分 MAE=0.00（等于白录 8 秒）。
# 这里把差分做成自动检查：MAE < 1.0 视为"点击无效"。
# 区域可用 VERIFY_BOX="x,y,w,h" 指定。
# ⚠️ 必须指定：全帧平均会把局部变化稀释掉——配置分子对话框里单选钮确实
#    切换了（对话框区 Δ=0.36），但只占全屏 5%，全帧 MAE 只有 0.02，
#    按阈值 1.0 判定就成了"点击无效"，冤枉好素材。
verify_clicks() {  # 默认只查 2 次点击之后的（第1次是"打开菜单/对话框"）
  local f="$OUT/clip_4${TAKE}_new.mp4"
  local box=${VERIFY_BOX:-0,0,1920,1080}
  local n=0 bad=0
  while read -r t x y; do
    n=$((n+1))
    (( n < 2 )) && continue
    # ⚠️ 窗口要够宽：softpipe 比 llvmpipe 慢，重绘常延迟 0.5–1s。
    #    窗口只给 0.5s 时会把"还没画完"误判成"点击没生效"。
    local a=$(python3 -c "print(f'{$t-0.3:.3f}')")
    local b=$(python3 -c "print(f'{$t+1.1:.3f}')")
    (( $(python3 -c "print(1 if $b > $DUR - 0.9 else 0)") )) && continue
    local mae
    mae=$(python3 - "$f" "$a" "$b" "$box" <<'EOF'
import sys, subprocess
import numpy as np
from PIL import Image
v, ta, tb, box = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
x, y, w, h = map(int, box.split(","))
def fr(t, p):
    subprocess.run(["ffmpeg","-v","error","-ss",t,"-i",v,"-frames:v","1",p,"-y"],check=False)
    try:
        return np.asarray(Image.open(p).convert("L").crop((x, y, x+w, y+h)), dtype=np.float64)
    except Exception:
        return None
A, B = fr(ta, "/tmp/vfa.png"), fr(tb, "/tmp/vfb.png")
if A is None or B is None:
    print("-1")
else:
    m = np.abs(A-B).mean()
    print(f"{m:.3f}" if m < 10 else f"{m:.2f}")
EOF
)
    # 阈值 0.2：真正没点中时 MAE≈0.02，点中时局部 Δ≥0.36，能分开
    if python3 -c "exit(0 if $mae < 0.2 else 1)"; then
      echo "    [!] ${t}s 的点击未改变画面（MAE=${mae}）——坐标可能没命中"
      bad=$((bad+1))
    fi
  done < "$REC/clicks_${TAKE}.txt"
  if [ $bad -eq 0 ]; then
    echo "    校验通过：所有点击都产生了画面变化"
  else
    echo "    校验失败：${bad} 次点击无效果"
  fi
}

# ============================ 4a 建模 ============================
take_a() {
echo "### [4a] 建模：元素周期表选氧"
# 节奏说明：第一版在 4s 处就点了 O，popup 随即关闭，后面的 Fe/Ag/Br
# 扫过动作发生在空白画布上（没有视觉对象）。改为先在表内游走、
# 最后才点 O——popup 在场时间拉满，且"点 O → 按钮 C 变 O"紧挨着收尾。
start_app
begin_take a
ease 900 500 267 55 0.8          # 从画布划到元素按钮
sleep 0.15
click_rec 267 55                  # 点开周期表
sleep 0.5
ease 267 55 390 82 0.3            # 悬停 C
ease 390 82 417 82 0.25           # 滑到 N
sleep 0.2
ease 417 82 224 135 0.45          # 甩到第四周期（Fe）
ease 224 135 305 162 0.35         # 滑到 Ag
sleep 0.25
ease 305 162 467 135 0.4          # 滑到 Br
sleep 0.3
ease 467 135 444 82 0.4           # 折返回 O
sleep 0.3
click_rec 444 82                  # 选中氧（popup 关、按钮 C→O）
sleep 0.3
ease 444 82 620 250 0.45          # 收尾滑向画布
sleep 0.6
end_take
VERIFY_BOX=10,30,514,263 verify_clicks   # 周期表 popup 区域
}

# ============================ 4b 计算 ============================
take_b() {
echo "### [4b] 计算：菜单 → Q-Chem 设置"
start_app
begin_take b
ease 900 500 183 9 0.9            # 划向 计算 菜单
sleep 0.2
click_rec 183 9                   # 下拉展开
# ⚠️ softpipe 下菜单展开会慢半拍，只等 0.6s 会出现"菜单还没展开就点空"，
#    实测结果：QChem 窗口找不到，整段只剩 2 次点击。
#    Qt 菜单不是独立 X 窗口，xdotool search 搜不到——改用像素轮询。
# 不用 wait_change：它在点击之后才取基准帧，菜单已展开就没得可等了，
# 白白超时 3s 还拖慢后续动作。llvmpipe 下菜单响应快，固定等待即可。
sleep 0.8
ease 183 9 235 41 0.4             # 移到 Q-Chem 设置
sleep 0.3
click_rec 235 41                  # 弹出 Q-Chem 编辑器
sleep 1.4
# 对话框就位后，把光标移进对话框内容区（tab 行）
QWID=$(DISPLAY=:99 xdotool search --name 'QChem' | head -1)
if [ -n "$QWID" ]; then
  QPOS=$(DISPLAY=:99 xdotool getwindowgeometry "$QWID" | grep Position | grep -o '[0-9-]*,[0-9-]*')
  QX=${QPOS%%,*}; QY=${QPOS##*,}
  echo "    QChem 对话框 @ ($QX,$QY)"
  # ⚠️ 不在 QChem 对话框内点击：xdotool 报它 @ (0,0)，据此算出来的
  #    内部坐标不可靠（实测点了没反应，MAE=0.03）。只做悬停扫过。
  ease $((QX+900)) $((QY+500)) $((QX+70)) $((QY+80)) 0.5   # 移到 设置 tab
  sleep 0.6
  ease $((QX+70)) $((QY+80)) $((QX+200)) $((QY+180)) 0.45  # 滑到 任务段 组合框
  sleep 0.5
  ease $((QX+200)) $((QY+180)) $((QX+120)) $((QY+290)) 0.45 # 滑到 方法 组合框
  sleep 0.6
else
  echo "    [!] 未找到 QChem 窗口，光标原地收尾"
  sleep 2
fi
end_take
VERIFY_BOX=0,0,960,400 verify_clicks   # 菜单栏 + 对话框区
}

# ============================ 4c 可视化 ============================
# 第三版彻底换方案（2026-10-03）：不再演示"配置分子"对话框里的样式切换。
#
# 原因（三个驱动 llvmpipe/softpipe/swrast 实测一致，脚本注释里记了全过程）：
#   只要打开"配置分子"对话框，画布就永久清空——分子区 std 22.8 → 0.0，
#   切换渲染样式画面 Δ=0.00，Escape 关掉对话框也不恢复。
#   也就是说旧方案等于"点了样式、分子毫无反应"，内行观众会觉得软件坏了。
#
# 但画布本身**能**重绘：实测拖拽旋转 Δ=11.93、滚轮缩放 Δ=13.06，分子全程可见。
# 所以改成拖拽旋转 + 滚轮缩放——分子全程在画面里，而且这本来就是
# 化学可视化软件最该给观众看的卖点。
act_c() {  # 4c 的完整动作序列，彩排和正式录制跑同一套
  ease 600 900 1100 550 0.8          # 从左下角划入画面
  sleep 0.2
  drag 1100 550 880 430 1.3           # 按住拖拽旋转
  sleep 0.3
  wheel 1000 500 3 4                   # 滚轮放大 3 格
  sleep 0.4
  drag 1000 500 1230 660 1.2          # 反方向再转一次
  sleep 0.3
  wheel 1100 600 2 5                   # 缩小 2 格
  sleep 0.3
  ease 1100 600 960 480 0.5           # 收尾：光标回到分子上
  sleep 0.5
}

take_c() {
echo "### [4c] 可视化：拖拽旋转 + 滚轮缩放分子"
start_app
# ⚠️ 必须彩排一遍（同样的动作先跑一次不录制）。
#    ffmpeg x11grab 持续抓屏会把 CPU 吃满，IQmol 刚开始那几秒忙着渲染，
#    发给它的第一次拖拽会被吞掉——实测正式录制的前 2.5 秒 Δ≈0.02（完全静止），
#    而不录制时同样的拖拽 Δ=11.9 正常。彩排把状态热起来，正式录制就能接上。
REC_ACTIVE=0 act_c
echo "    彩排完成，正式录制"
# ⚠️ 4c 必须单独给 12 秒，不能沿用全局 DUR=8。
#    彩排验证了"开始阶段不再被吞"，但也暴露了另一个问题：录制期间
#    ffmpeg 抓屏吃 CPU，每个 xdotool 调用的实际耗时被拉长约 1.5 倍，
#    动作序列理论 7.9s 实际要跑 11.7s。8 秒素材会把末尾两次滚轮
#    （实测点击时刻 11.24s / 11.70s）直接截掉——画面看着没事，
#    但那两个点击的波纹落在素材之外，白录。
begin_take c $DUR_C
REC_ACTIVE=1 act_c
end_take
check_clicks_in_range c $DUR_C    # 有点击超出素材长度就报警
VERIFY_BOX=1150,400,300,400 verify_clicks   # 分子区：旋转/缩放都应产生变化
}

# ============================ 主流程 ============================
# 参数：./rec_segment4.sh [段名子串，默认 abc]  例如只重录 4c → ./rec_segment4.sh c
RUN=${1:-abc}
case "$RUN" in
  *a*) take_a ;;
esac
case "$RUN" in
  *b*) take_b ;;
esac
case "$RUN" in
  *c*) take_c ;;
esac

echo
echo "输出：$OUT/clip_4{a,b,c}_new.mp4 + $REC/clicks_{a,b,c}.txt"
