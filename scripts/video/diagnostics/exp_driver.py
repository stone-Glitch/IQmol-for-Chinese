#!/usr/bin/env python3
# ============================================================================
# exp_driver.py —— 一次性诊断脚本（结论已固化进rec_segment4.sh 的注释）
#
# 保留原因：这三个实验钉死了 4c 换方案的关键依据，重录遇到同样问题时
#        需要能重新跑一遍验证，而不是凭记忆判断。
# ============================================================================
#!/usr/bin/env python3
#
# 背景（2026-10-03）：llvmpipe 下画布不重绘（打开"配置分子"对话框后分子消失，
# 切换渲染样式画面纹丝不动）；曾试 softpipe，画布重绘正常（Δ=36），
# 但当时判定"UI 点击失效"——**可那次实验环境里有 X 僵尸窗口**，
# 而 llvmpipe 点击失效的真凶也正是僵尸窗口，两者可能是同一件事。
# 这次在干净环境里重测，把结论钉死。
#
# 测四项：
#   A 启动后分子是否可见
#   B 双击图层能否弹出"配置分子"对话框（且弹窗后分子是否还在）
#   C 点击"空间填充"后：单选钮是否切换 + 画布是否重绘
#   D 关闭对话框是否成功（不留模态残渣）
#   E 周期表 popup 能否点开（4a 场景，验证 UI 点击整体可用）
#
# 用法：python3 exp_driver.py <驱动> [<驱动> ...]
#   驱动写法：llvmpipe / softpipe / swrast（MESA_LOADER_DRIVER_OVERRIDE）
# ============================================================================
import subprocess, sys, time, os, re
import numpy as np
from PIL import Image

# 从任意位置运行都能找到仓库根（归档到 diagnostics/ 后深度变了）
import os
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../.."))

MOL = "src/Parser/test/samples/viagra.xyz"
D = "DISPLAY=:99 "
MOLE = (1150, 400, 1450, 800)    # 分子右半（避开对话框 808-1092）
DLG = (808, 309, 1092, 690)      # 配置分子对话框
POPUP = (10, 30, 524, 293)       # 元素周期表 popup
BTN = (250, 40, 290, 70)         # 元素按钮（显示 C / O）


def sh(c, d=D):
    return subprocess.run(d + c, shell=True, capture_output=True, text=True)


def grab(p="/tmp/e.png"):
    sh("ffmpeg -v error -f x11grab -video_size 1920x1080 -i :99.0 -frames:v " + f"1 {p} -y")
    try:
        return np.asarray(Image.open(p).convert("L"), dtype=np.float64)
    except Exception:
        return None


def s(f, b):
    return float(f[b[1]:b[3], b[0]:b[2]].std())


def m(a, b, box):
    return float(np.abs(a[box[1]:box[3], box[0]:box[2]] - b[box[1]:box[3], box[0]:box[2]]).mean())


def clean():
    """杀掉 IQmol 并清掉 X 里的残留窗口——僵尸窗口会吃掉点击"""
    sh("pkill -x IQmol")
    time.sleep(2)
    for w in sh("xdotool search --name 'IQmol|配置分子|元素周期表|QChem'").stdout.split():
        sh(f"xdotool windowkill {w} 2>/dev/null")
    time.sleep(0.5)


def launch(driver):
    clean()
    if driver == "swrast":
        env = ("LIBGL_ALWAYS_SOFTWARE=1 MESA_LOADER_DRIVER_OVERRIDE=swrast")
    else:
        env = f"LIBGL_ALWAYS_SOFTWARE=1 GALLIUM_DRIVER={driver}"
    cmd = (f"setsid env DISPLAY=:99 {env} LANG=zh_CN.UTF-8 LC_ALL=zh_CN.UTF-8 "
           f"QT_QPA_PLATFORM=xcb QT_XCB_GL_INTEGRATION=xcb_glx "
           f"QT_AUTO_SCREEN_SCALE_FACTOR=0 "
           f"./build-video/IQmol {MOL} > /tmp/exp_{driver}.log 2>&1 &")
    subprocess.Popen(cmd, shell=True)
    for _ in range(40):
        time.sleep(1)
        if sh("pgrep -x IQmol").stdout.strip():
            break
    time.sleep(3)
    w = sh("xdotool search --name '^IQmol$'").stdout.strip().split("\n")[-1]
    sh(f"xdotool windowmove {w} 0 0; xdotool windowsize {w} 1920 1080")
    time.sleep(2)
    sh(f"xdotool windowfocus {w}")
    # 等分子出现（最多 25s，softpipe 慢）
    for _ in range(25):
        f = grab()
        if f is not None and s(f, MOLE) > 12:
            return True
        time.sleep(1)
    return False


def run(driver):
    print(f"\n{'='*58}\n 驱动 {driver}\n{'='*58}")
    ok = launch(driver)
    a = grab()
    print(f"  A 启动后分子可见           : {'是' if ok else '否'} (std={s(a,MOLE):.1f})")
    if not ok:
        return

    # B 双击图层 → 配置分子对话框
    # 操作序列必须和 rec_segment4.sh 一致：缓动移过去 → 单击选中 → 双击。
    # 只发 xdotool click --repeat 2 弹不出对话框（实测三个驱动都不行）。
    sh("xdotool mousemove 900 500")
    time.sleep(0.2)
    for i in range(1, 21):                      # 分步移动，模拟缓动
        sh(f"xdotool mousemove {900-(900-32)*i//20} {500-(500-160)*i//20}")
        time.sleep(0.04)
    sh("xdotool click 1")                        # 先单击选中图层
    time.sleep(0.3)
    sh("xdotool click --repeat 2 --delay 120 1")  # 再双击
    time.sleep(1.5)
    b = grab()
    dlg = sh("xdotool search --name '配置分子'").stdout.strip()
    print(f"  B 对话框弹出               : {'是' if dlg else '否'}")
    print(f"    弹窗后分子还在           : {'是' if s(b,MOLE) > 12 else '否'} (std={s(b,MOLE):.1f})")
    if not dlg:
        clean(); return
    pos = sh(f"xdotool getwindowgeometry {dlg.split()[0]}").stdout
    cx, cy = 808, 309
    # 输出形如 "  Position: 808,309 (screen)"，要用正则挑数字
    for ln in pos.splitlines():
        if "Position" in ln:
            nums = re.findall(r"-?\d+", ln.split(":", 1)[1])
            if len(nums) >= 2:
                cx, cy = int(nums[0]), int(nums[1])
    print(f"    对话框位置               : ({cx},{cy})")

    # C 点空间填充（rel 28,86）
    sh(f"xdotool mousemove {cx+28} {cy+86}; xdotool click 1")
    time.sleep(1.5)
    c = grab()
    print(f"  C 点空间填充  单选钮切换   : {'是' if m(b,c,DLG) > 0.15 else '否'} (Δ={m(b,c,DLG):.3f})")
    print(f"    画布重绘                 : {'是' if m(b,c,MOLE) > 1.0 else '否'} (Δ={m(b,c,MOLE):.2f})")

    # D 关闭对话框
    sh(f"xdotool mousemove {cx+237} {cy+340}; xdotool click 1")
    time.sleep(0.8)
    still = sh("xdotool search --name '配置分子'").stdout.strip()
    if still:
        sh("xdotool key Escape")
        time.sleep(0.4)
    print(f"  D 对话框关闭               : {'是' if not still else '关不掉'}")

    # E 周期表 popup（4a 场景）
    clean()
    launch(driver)
    sh("xdotool mousemove 267 55; xdotool click 1")
    time.sleep(1.0)
    e = grab()
    print(f"  E 周期表 popup 点开        : {'是' if s(e,POPUP) > 40 else '否'} (std={s(e,POPUP):.1f})")
    sh("xdotool mousemove 444 82; xdotool click 1")   # 选 O
    time.sleep(1.0)
    e2 = grab()
    print(f"    选中氧（按钮 C→O）       : {'是' if m(e,e2,BTN) > 0.5 else '否'} (Δ={m(e,e2,BTN):.2f})")
    clean()


if __name__ == "__main__":
    for d in (sys.argv[1:] or ["llvmpipe", "softpipe", "swrast"]):
        run(d)
    print("\n完成")
