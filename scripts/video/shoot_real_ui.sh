#!/usr/bin/env bash
# ============================================================================
# shoot_real_ui.sh —— 从**真实运行的** IQmol 截取中文界面（非 .ui 静态渲染）
#
# 背景：dialog_screenshots/ 用 QUiLoader 静态渲染 .ui，Qt5 无 setTranslator，
#       截出来全是英文原文。要展示中文效果，必须在真实运行态截图。
#
# 本脚本做三件事：
#   1. 起虚拟显示（Xvfb + openbox），无需显卡/物理显示器
#   2. 跑起已编译的 IQmol，确认中文已生效（[i18n] Loaded translation: "zh_CN"）
#   3. 用 xdotool 驱动菜单栏，逐项截图输出到 out/ui_shots/
#
# ⚠️ 踩过的坑（务必先读）：
#   1. Xvfb/openbox 必须用 setsid 脱离会话，否则随调用方被回收
#   2. Qt 对话框在 openbox 下**无窗口装饰**，右上角没有 X 按钮，
#      不能用「点关闭按钮」关对话框
#   3. xdotool mousemove --window <id> x y 的相对坐标有偏移，
#      一律改用**绝对屏幕坐标**
#   4. Q-Chem 设置对话框是**模态**的，不关掉它后面每次截图都是同一张
#      → 本脚本对每个对话框都**重启一个 IQmol 实例**，彻底规避模态阻塞
#   5. 别用 pkill -f "IQmol" —— 会匹配到执行脚本自己的命令行并自杀；
#      用 pkill -x IQmol 精确匹配进程名
#
# 用法：
#   bash scripts/video/shoot_real_ui.sh              # 截全套
#   OUT_DIR=/tmp/myshots bash scripts/video/shoot_real_ui.sh
# ============================================================================
set -uo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BIN="${IQMOL_BIN:-$REPO/build-video/IQmol}"
MOL="${IQMOL_MOL:-$REPO/src/Parser/test/samples/viagra.xyz}"
OUT_DIR="${OUT_DIR:-$REPO/build-video/out/ui_shots}"
DISPLAY_NUM="${DISPLAY_NUM:-:99}"
GEOM="${GEOM:-1920x1080}"

# 菜单栏各菜单的 x 坐标（窗口内坐标，1920 宽屏幕实测）
declare -A MENU_X=([文件]=13 [编辑]=64 [显示]=106 [构建]=145 [计算]=182 [帮助]=220)
# 反查：给定 x 偏移，得到菜单名（供对话框清单里用 x 指代菜单）
declare -A MENU_NAME=([13]=文件 [64]=编辑 [106]=显示 [145]=构建 [182]=计算 [220]=帮助)

# 对话框清单：输出名|菜单x|菜单项y(窗口内)|说明
DIALOGS=(
  "dlg_qchem|182|47|Q-Chem 设置"
  "dlg_jobmonitor|182|70|任务监视器"
  "dlg_server|182|93|服务器列表"
  "dlg_camera|106|130|配置相机"
  "dlg_appearance|106|155|外观"
  "dlg_insmol|145|39|按 ID 插入分子"
)

export LIBGL_ALWAYS_SOFTWARE=1
export GALLIUM_DRIVER=llvmpipe
export QT_QPA_PLATFORM=xcb
export QT_XCB_GL_INTEGRATION=xcb_glx
export QT_AUTO_SCREEN_SCALE_FACTOR=0
export LANG=zh_CN.UTF-8 LC_ALL=zh_CN.UTF-8 LANGUAGE=zh_CN

mkdir -p "$OUT_DIR"

die() { echo "错误: $*" >&2; exit 1; }

# ---------------------------------------------------------------- 依赖检查
echo "=== 0/3 检查依赖 ==="
for t in Xvfb openbox xdotool import ffmpeg; do
  command -v "$t" >/dev/null || die "缺少 $t（apt-get install -y xvfb openbox xdotool imagemagick ffmpeg）"
done
[[ -x "$BIN" ]] || die "找不到可执行文件 $BIN（先构建：cd build-video && make -j\$(nproc)）"
[[ -f "$MOL" ]] || die "找不到分子文件 $MOL"

# ------------------------------------------------------- 1. 虚拟显示常驻
echo "=== 1/3 启动虚拟显示 $DISPLAY_NUM (${GEOM}x24) ==="
pkill -f "Xvfb $DISPLAY_NUM" 2>/dev/null; sleep 1
setsid Xvfb "$DISPLAY_NUM" -screen 0 "${GEOM}x24" -nolisten tcp >/dev/null 2>&1 &
sleep 3
export DISPLAY="$DISPLAY_NUM"

# ⚠️ openbox 会给窗口加标题栏装饰，导致主窗口 Y 偏移（实测 y=48），
#    菜单栏点击坐标全部失效。这里用一份 rc 关掉装饰与动画，让坐标可预测。
OB_RC="$(mktemp -d)/rc.xml"
cat > "$OB_RC" <<'XEOF'
<?xml version="1.0" encoding="UTF-8"?>
<openbox_config xmlns="http://openbox.org/3.4/rc">
  <theme>
    <name>Clearlooks</name>
    <titleLayout></titleLayout>
  </theme>
  <applications>
    <application class="*">
      <decor>no</decor>
      <position force="yes"><x>0</x><y>0</y></position>
    </application>
  </applications>
</openbox_config>
XEOF
setsid openbox --config-file "$OB_RC" --sm-disable >/dev/null 2>&1 &
sleep 2
xdotool getdisplaygeometry >/dev/null 2>&1 || die "虚拟显示未就绪"

# ------------------------------------------------------ 主窗口坐标定位
# 不假设窗口在 (0,0)：每次点击前用 xdotool 查真实坐标，
# 菜单栏在窗口内 y≈22，各菜单 x 见 MENU_X。
MAIN_X=0; MAIN_Y=0

locate_main() {
  local w
  for w in $(xdotool search --onlyvisible --name "^IQmol$" 2>/dev/null); do
    local g
    g=$(xdotool getwindowgeometry --shell "$w" 2>/dev/null)
    MAIN_X=$(echo "$g" | awk -F= '/^X=/{print $2}')
    MAIN_Y=$(echo "$g" | awk -F= '/^Y=/{print $2}')
    [[ -n "$MAIN_X" && -n "$MAIN_Y" ]] && return 0
  done
  MAIN_X=0; MAIN_Y=0
  return 1
}

# 点菜单栏某个菜单（用主窗口偏移 + 窗口内坐标）
click_menu() {  # $1=菜单名
  locate_main
  xdotool mousemove $(( MAIN_X + MENU_X[$1] )) $(( MAIN_Y + 22 )) click 1
}

# 点下拉菜单里的某一项（y 为窗口内绝对坐标）
click_menu_item() {  # $1=菜单x偏移 $2=窗口内 y
  locate_main
  xdotool mousemove $(( MAIN_X + $1 + 60 )) $(( MAIN_Y + $2 )) click 1
}

# 起一个实例的封装：启动后确认中文已加载
start_iqmol() {
  pkill -x IQmol 2>/dev/null; sleep 2
  ( cd "$(dirname "$BIN")" && setsid "$BIN" "$MOL" >/tmp/iqmol_shoot.log 2>&1 </dev/null & )
  sleep 13
  locate_main || echo "  ! 警告：未找到 IQmol 主窗口"
  grep -q 'Loaded translation: "zh_CN"' /tmp/iqmol_shoot.log \
    || echo "  ! 警告：日志未见中文加载标志，界面可能回退英文"
}

# 截取当前的非主窗口（对话框）
# 用一个哨兵：调用前先记下打开的窗口集合，之后取「新出现的那个」
DIALOG_BEFORE=""

snapshot_windows() {
  local w
  DIALOG_BEFORE=""
  for w in $(xdotool search --onlyvisible --name ".*" 2>/dev/null); do
    local n; n=$(xdotool getwindowname "$w" 2>/dev/null)
    [[ -z "$n" ]] && continue
    DIALOG_BEFORE="$DIALOG_BEFORE $w"
  done
}

shoot_dialog() {  # $1=输出名
  local name="$1" wid="" wname=""
  for w in $(xdotool search --onlyvisible --name ".*" 2>/dev/null); do
    local n; n=$(xdotool getwindowname "$w" 2>/dev/null)
    [[ -z "$n" ]] && continue
    # 只认「新出现的、有标题的、非 IQmol 主窗口」的窗口
    [[ "$n" == "IQmol" ]] && continue
    [[ "$DIALOG_BEFORE" == *" $w "* || "$DIALOG_BEFORE" == " $w" || "$DIALOG_BEFORE" == "$w " ]] && continue
    wid="$w"; wname="$n"; break
  done
  if [[ -n "$wid" ]]; then
    import -window "$wid" "$OUT_DIR/$name.png" 2>/dev/null
    echo "  ✓ $name  ← 窗口标题「$wname」"
  else
    echo "  ! $name 未弹出对话框（该菜单项可能需先选中原子）"
  fi
}

# ------------------------------------------------------- 2. 六大菜单
echo "=== 2/3 截取菜单栏 ==="
start_iqmol
for label in 文件 编辑 显示 构建 计算 帮助; do
  click_menu "$label"; sleep 1.0
  import -window root "$OUT_DIR/_menu_full_$label.png" 2>/dev/null
  # 裁出「菜单栏 + 下拉」区域（保留主窗口偏移量），去掉右侧 3D 视图
  # ⚠️ 裁底的两个坑（都是真踩出来的）：
  #   (1) 下拉菜单左右各有 1px 边框竖线，贯穿全高；
  #       若探测区包含 x=0 或 x≈宽-2，这列永远「非背景」，
  #       导致「连续纯背景行」永不命中、一直裁到上限 → 必须避开左右各 8px（取 x=8..200）。
  #   (2) 背景色不能取「菜单栏区域或菜单中间」，要取探测区里**最靠下**的一行
  #       （菜单再长也不可能超过 400px，下方一定是主窗口白底），避免取到菜单内容。
  python3 - "$OUT_DIR" "$label" "$MAIN_X" "$MAIN_Y" <<'PY'
import sys, os
from PIL import Image
import numpy as np
d, label, mx, my = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
f = os.path.join(d, f'_menu_full_{label}.png')
img = Image.open(f).convert('RGB')
x0, y0 = max(0, mx), max(0, my)
W = 240
crop = img.crop((x0, y0, min(img.size[0], x0 + W), min(img.size[1], y0 + 700)))

# 探测区避开左右边框（各 8px），只在 x=8..200 之间判断背景
probe = np.array(crop.crop((8, 0, 200, crop.size[1]))).astype(int)
bg_y = min(probe.shape[0] - 1, 650)        # 菜单下方一定是主窗口白底
bg = probe[bg_y, 2]
rowmax = np.abs(probe - bg).max(axis=(1, 2))
is_bg = rowmax <= 12

# 从菜单栏下方（y>40）找「连续 30 行纯背景」的起点 = 下拉菜单真正结束处
end = crop.size[1]
run = 0
for y in range(40, len(is_bg)):
    run = run + 1 if is_bg[y] else 0
    if run >= 30:
        end = y - 29
        break
out = crop.crop((0, 0, crop.size[0], min(crop.size[1], end + 12)))
out.save(os.path.join(d, f'menu_{label}.png'))
print(f'     裁到 {out.size[1]}px 高')
PY
  rm -f "$OUT_DIR/_menu_full_$label.png"
  echo "  ✓ menu_$label"
  xdotool key Escape; sleep 0.6
done

# ------------------------------------------------------- 3. 各对话框
echo "=== 3/3 截取对话框（每个独立实例，规避模态阻塞）==="
for entry in "${DIALOGS[@]}"; do
  IFS='|' read -r name mx iy desc <<< "$entry"
  start_iqmol
  snapshot_windows
  click_menu "${MENU_NAME[$mx]:-计算}"; sleep 0.9
  click_menu_item "$mx" "$iy"; sleep 3.5
  shoot_dialog "$name"
done

pkill -x IQmol 2>/dev/null

echo
echo "=== 完成 ==="
echo "输出目录：$OUT_DIR"
ls -1 "$OUT_DIR"/*.png 2>/dev/null | wc -l | xargs echo "共截图："
echo
echo "校验中文是否真的生效（权威标志）："
echo "  grep 'Loaded translation' /tmp/iqmol_shoot.log"
