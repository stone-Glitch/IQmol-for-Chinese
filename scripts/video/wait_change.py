#!/usr/bin/env python3
# ============================================================================
# wait_change.py —— 轮询指定区域，直到画面发生变化（或超时）
#
# 为什么需要：软件渲染（softpipe/llvmpipe）下 IQmol 的响应延迟很不稳定——
#   菜单展开、GL 重绘可能 0.2s 就好，也可能拖到 1s 以上。
#   写死 sleep 要么浪费素材时长，要么"还没画完就继续操作"。
#
# 用法：python3 wait_change.py <x> <y> <w> <h> [最长等待秒] [阈值]
# 退出码：0=检测到变化（stdout 打印实际等待秒数）；1=超时
# ============================================================================
import sys, subprocess, time
import numpy as np
from PIL import Image

x, y, w, h = map(int, sys.argv[1:5])
maxs = float(sys.argv[5]) if len(sys.argv) > 5 else 3.0
thr = float(sys.argv[6]) if len(sys.argv) > 6 else 2.0


def grab(path):
    subprocess.run(
        ["ffmpeg", "-v", "error", "-f", "x11grab", "-video_size", "1920x1080",
         "-i", ":99.0", "-frames:v", "1", path, "-y"], check=False)
    try:
        return np.asarray(Image.open(path).convert("L").crop((x, y, x + w, y + h)),
                          dtype=np.float64)
    except Exception:
        return None


A = grab("/tmp/wc_a.png")
if A is None:
    sys.exit(1)

t0 = time.time()
while time.time() - t0 < maxs:
    time.sleep(0.25)
    B = grab("/tmp/wc_b.png")
    if B is not None and np.abs(A - B).mean() > thr:
        print(f"{time.time() - t0:.2f}")
        sys.exit(0)

print("timeout", file=sys.stderr)
sys.exit(1)
