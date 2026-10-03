#!/usr/bin/env python3
# ============================================================================
# canvas_std.py —— 逐帧统计画布区域的像素方差，检测"分子还在不在"
#
# 为什么需要它：llvmpipe 软渲染下 IQmol 会随机出现画布只剩背景蓝、
# 分子整个不画的情况（GL context 坏死），肉眼抽几帧容易漏判。
# 空背景是纯渐变蓝，灰度 std < 5；有分子时边缘丰富，std > 15。
#
# 用法：
#   python3 canvas_std.py <视频> [步长秒] [区域x,y,w,h]
#
# 输出：时刻,std,#判断    （OK=分子可见 / EMPTY=空画布）
# ============================================================================
import subprocess, sys, os
import numpy as np
from PIL import Image

video = sys.argv[1]
step = float(sys.argv[2]) if len(sys.argv) > 2 else 0.5
region = sys.argv[3] if len(sys.argv) > 3 else "1200,250,400,550"

dur = float(subprocess.run(
    ["ffprobe", "-v", "error", "-show_entries", "format=duration",
     "-of", "csv=p=0", video], capture_output=True, text=True).stdout.strip())

rx, ry, rw, rh = map(int, region.split(","))
tmp = "/tmp/cs_frame.png"

print(f"# {video}  时长{dur:.1f}s  区域{region}")
worst = 999.0
t = 0.0
while t < dur - 0.05:
    subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.2f}", "-i", video,
                    "-frames:v", "1", tmp, "-y"], check=False)
    if not os.path.exists(tmp):
        break
    a = np.asarray(Image.open(tmp).convert("L").crop(
        (rx, ry, rx + rw, ry + rh)), dtype=np.float64)
    s = a.std()
    worst = min(worst, s)
    print(f"{t:5.2f} {s:6.1f}  {'OK' if s > 12 else 'EMPTY'}")
    t += step

print(f"# 最低 std={worst:.1f}  ->  {'全程可见' if worst > 12 else '存在空画布帧'}")
