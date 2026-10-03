#!/usr/bin/env python3
# ============================================================================
# exp_close.py —— 一次性诊断脚本（结论已固化进rec_segment4.sh 的注释）
#
# 保留原因：这三个实验钉死了 4c 换方案的关键依据，重录遇到同样问题时
#        需要能重新跑一遍验证，而不是凭记忆判断。
# ============================================================================
#!/usr/bin/env python3
#
# 三个驱动实测一致（llvmpipe/softpipe/swrast）：对话框一打开，画布就再也不画
# 分子（std 22.8 → 0.0），切换样式画面 Δ=0.00。换驱动无用，这是 IQmol 自身行为。
#
# 那么最后一条路：如果关掉对话框，画布会不会把新样式画出来？
#   能 → 4c 改成"开对话框 → 选样式 → 关对话框"，收尾能看到结果
#   不能 → 只能靠裁剪区避开画布（当前做法）
#
# 顺带用像素分析精确定位"关闭"按钮——三个驱动下点击它都无效（关不掉）。
# ============================================================================
import subprocess, time, re
import numpy as np
from PIL import Image

# 从任意位置运行都能找到仓库根（归档到 diagnostics/ 后深度变了）
import os
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../.."))

MOL = "src/Parser/test/samples/viagra.xyz"
D = "DISPLAY=:99 "
MOLE = (1150, 400, 1450, 800)
DLG = (808, 309, 1092, 690)


def sh(c, d=D):
    return subprocess.run(d + c, shell=True, capture_output=True, text=True)


def grab(p="/tmp/ec.png"):
    sh(f"ffmpeg -v error -f x11grab -video_size 1920x1080 -i :99.0 -frames:v 1 {p} -y")
    return np.asarray(Image.open(p).convert("L"), dtype=np.float64)


def s(f, b):
    return float(f[b[1]:b[3], b[0]:b[2]].std())


def m(a, b, box):
    return float(np.abs(a[box[1]:box[3], box[0]:box[2]] - b[box[1]:box[3], box[0]:box[2]]).mean())


# ---- 启动 ----
sh("pkill -x IQmol"); time.sleep(2)
for w in sh("xdotool search --name 'IQmol|配置分子|元素周期表|QChem'").stdout.split():
    sh(f"xdotool windowkill {w} 2>/dev/null")
subprocess.Popen(
    "setsid env DISPLAY=:99 LIBGL_ALWAYS_SOFTWARE=1 GALLIUM_DRIVER=llvmpipe "
    f"LANG=zh_CN.UTF-8 QT_QPA_PLATFORM=xcb QT_XCB_GL_INTEGRATION=xcb_glx "
    f"QT_AUTO_SCREEN_SCALE_FACTOR=0 ./build-video/IQmol {MOL} > /tmp/ec.log 2>&1 &", shell=True)
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
print(f"初始分子 std={s(a,MOLE):.1f}")

# ---- 开对话框 ----
sh("xdotool mousemove 900 500"); time.sleep(0.2)
for i in range(1, 21):
    sh(f"xdotool mousemove {900-(900-32)*i//20} {500-(500-160)*i//20}"); time.sleep(0.04)
sh("xdotool click 1"); time.sleep(0.3)
sh("xdotool click --repeat 2 --delay 120 1"); time.sleep(1.5)
dlg = sh("xdotool search --name '配置分子'").stdout.strip()
assert dlg, "对话框没弹出"
cx, cy = 808, 309
for ln in sh(f"xdotool getwindowgeometry {dlg.split()[0]}").stdout.splitlines():
    if "Position" in ln:
        n = re.findall(r"-?\d+", ln.split(":", 1)[1])
        cx, cy = int(n[0]), int(n[1])
print(f"对话框 @({cx},{cy})，打开后分子 std={s(grab(),MOLE):.1f}")

# ---- 像素定位"关闭"按钮 ----
# 按钮通常是浅色描边的圆角矩形。在对话框下半部找横向的亮边框线。
img = grab("/tmp/ec_dlg.png")
sub = img[cy:cy+382, cx:cx+285]
rowmax = sub.max(axis=1) - sub.mean(axis=1)      # 每行的"最亮减均值"= 边框可能性
cand = [i for i, v in enumerate(rowmax) if v > 28]
print(f"对话框下半部疑似边框行(rel y): {cand[-12:]}")
if cand:
    y0 = cand[-1]
    band = sub[y0:y0+30, :]
    colmax = band.max(axis=0) - band.mean(axis=0)
    cidx = [i for i, v in enumerate(colmax) if v > 28]
    if cidx:
        print(f"  按钮横向范围(rel x): {cidx[0]}–{cidx[-1]}  → 绝对 x {cx+cidx[0]}–{cx+cidx[-1]}")
        print(f"  按钮中心绝对坐标 ≈ ({cx+(cidx[0]+cidx[-1])//2}, {cy+y0+12})")

# ---- 点空间填充，再 Escape 关闭，看分子是否恢复 ----
sh(f"xdotool mousemove {cx+28} {cy+86}; xdotool click 1"); time.sleep(1.2)
b = grab()
sh("xdotool key Escape"); time.sleep(1.2)
c = grab()
print(f"\nEscape 关闭后：对话框还在吗 = {'在' if sh(chr(34)+'xdotool search --name 配置分子'+chr(34)).stdout.strip() else '已关闭'}")
print(f"  分子区 std={s(c,MOLE):.1f}  (初始 {s(a,MOLE):.1f})")
print(f"  与初始画面差异 Δ={m(a,c,MOLE):.2f}")
print(f"  分子区 vs 对话框打开时 Δ={m(b,c,MOLE):.2f}")
print("  判定：" + ("分子恢复且样式已改变 ✅" if s(c, MOLE) > 12 and m(a, c, MOLE) > 1.0
                  else ("分子恢复但样式未变" if s(c, MOLE) > 12 else "分子仍未恢复 ❌")))
sh("pkill -x IQmol")
