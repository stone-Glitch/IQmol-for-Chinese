#!/usr/bin/env python3
# ============================================================================
# exp_canvas.py —— 一次性诊断脚本（结论已固化进rec_segment4.sh 的注释）
#
# 保留原因：这三个实验钉死了 4c 换方案的关键依据，重录遇到同样问题时
#        需要能重新跑一遍验证，而不是凭记忆判断。
# ============================================================================
#!/usr/bin/env python3
#
# 已知（2026-10-03，三驱动一致）：打开"配置分子"对话框 → 画布永久清空，
# 关掉对话框也不恢复。但"画布完全不能重绘"这个结论还没被严格验证。
# 如果拖拽/缩放/图层勾选能重绘并保住分子，那 4c 就应该改成
# "旋转 + 缩放分子"，比现在对着空白画布讲样式切换强得多。
# ============================================================================
import subprocess, time
import numpy as np
from PIL import Image

# 从任意位置运行都能找到仓库根（归档到 diagnostics/ 后深度变了）
import os
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../.."))

MOL = "src/Parser/test/samples/viagra.xyz"
D = "DISPLAY=:99 "
MOLE = (1150, 400, 1450, 800)   # 分子所在区域
TREE = (0, 100, 300, 400)       # 左侧图层树


def sh(c, d=D):
    return subprocess.run(d + c, shell=True, capture_output=True, text=True)


def grab(p="/tmp/cv.png"):
    sh(f"ffmpeg -v error -f x11grab -video_size 1920x1080 -i :99.0 -frames:v 1 {p} -y")
    return np.asarray(Image.open(p).convert("L"), dtype=np.float64)


def s(f, b):
    return float(f[b[1]:b[3], b[0]:b[2]].std())


def m(a, b, box):
    return float(np.abs(a[box[1]:box[3], box[0]:box[2]] - b[box[1]:box[3], box[0]:box[2]]).mean())


sh("pkill -x IQmol"); time.sleep(2)
for w in sh("xdotool search --name 'IQmol|配置分子|元素周期表|QChem'").stdout.split():
    sh(f"xdotool windowkill {w} 2>/dev/null")
subprocess.Popen(
    "setsid env DISPLAY=:99 LIBGL_ALWAYS_SOFTWARE=1 GALLIUM_DRIVER=llvmpipe "
    f"LANG=zh_CN.UTF-8 QT_QPA_PLATFORM=xcb QT_XCB_GL_INTEGRATION=xcb_glx "
    f"QT_AUTO_SCREEN_SCALE_FACTOR=0 ./build-video/IQmol {MOL} > /tmp/cv.log 2>&1 &", shell=True)
for _ in range(40):
    time.sleep(1)
    if sh("pgrep -x IQmol").stdout.strip():
        break
time.sleep(3)
w = sh("xdotool search --name '^IQmol$'").stdout.strip().split("\n")[-1]
sh(f"xdotool windowmove {w} 0 0; xdotool windowsize {w} 1920 1080; xdotool windowfocus {w}")
for _ in range(25):
    time.sleep(1)
    a = grab()
    if s(a, MOLE) > 12:
        break
print(f"初始：分子 std={s(a,MOLE):.1f}\n")


def step(name, fn, wait=1.2):
    global a
    b0 = grab()
    fn()
    time.sleep(wait)
    b1 = grab()
    keep = s(b1, MOLE) > 12
    changed = m(b0, b1, MOLE) > 1.0
    print(f"  {name:22s} 分子保留={'是' if keep else '否'} "
          f"画面变化={'是' if changed else '否'}(Δ={m(b0,b1,MOLE):5.2f}) "
          f"std {s(b0,MOLE):5.1f}→{s(b1,MOLE):5.1f}")
    a = b1
    return keep


# 1) 画布拖拽旋转
def rotate():
    sh("xdotool mousemove 700 400 mousedown 1 mousemove 760 440 mousemove 820 470 mouseup 1")


step("拖拽旋转", rotate)

# 2) 滚轮缩放
def zoom():
    sh("xdotool mousemove 1100 550 click 4 click 4 click 5")


step("滚轮缩放", zoom, 1.0)

# 3) 打开"显示"菜单（UI 层，不该触发画布重绘）
def show_menu():
    sh("xdotool mousemove 103 9 click 1")


step("显示菜单展开", show_menu, 1.0)
sh("xdotool key Escape"); time.sleep(0.5)

# 4) 图层树里点最上层"全显"复选框（切换显示）
def toggle_all():
    sh("xdotool mousemove 8 118 click 1")


step("图层树勾选切换", toggle_all, 1.2)

# 5) 双击图层开配置分子对话框（已知会毁掉画布，放最后）
def dlg():
    sh("xdotool mousemove 32 160 click 1"); time.sleep(0.3)
    sh("xdotool click --repeat 2 --delay 120 1")


step("双击开配置对话框", dlg, 1.5)

sh("pkill -x IQmol")
