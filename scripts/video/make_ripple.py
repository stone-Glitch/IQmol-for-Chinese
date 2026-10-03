#!/usr/bin/env python3
# ============================================================================
# make_ripple.py —— 生成"点击波纹"特效片段（带 alpha 通道，供 overlay 叠加）
#
# 视觉：橙色圆环从半径 10px 扩散到 74px，线宽渐细、透明度渐隐，0.8 秒。
# 用途：段4 重录素材的点击反馈。B站同类视频普遍给点击加可见反馈，
#       否则观众在缩小的画面里根本注意不到"这里点了一下"。
#
# ⚠️ 透明度衰减的坑：第一版用 t = i/(N-1) 归一化，末帧 t=1 → alpha=0，
#    实测 ripple.mov 在 t≥0.7s 后非透明像素直接归零。叠加到 4c 末尾那次
#    点击（t=11.68s）时，波纹只显示了 0.1s 就没了。
#    现在改成 t = i/N（末帧 0.95），并给 alpha 加 90 的下限托底，
#    保证整段 0.8s 都有可见波纹。
#
# 输出：/tmp/iqmol_annot/ripple.mov（qtrle 编码，Millions+ alpha，ffmpeg
#       overlay 滤镜可直接消费；中心在 960,540，与全屏画幅一致）
# ============================================================================
import subprocess, sys
import numpy as np
from PIL import Image, ImageDraw

OUT = sys.argv[1] if len(sys.argv) > 1 else "/tmp/iqmol_annot/ripple.mov"
W, H = 1920, 1080
FPS = 25
DUR = 0.8
N = int(DUR * FPS)          # 20 帧
CX, CY = W // 2, H // 2

def ring_frame(i: int) -> Image.Image:
    t = i / N                           # 0..0.95，末帧仍可见
    r = 10 + 64 * t# 半径扩散
    width = max(2, int(6 * (1 - t)))    # 线宽渐细
    alpha = max(90, int(230 * (1 - t) ** 1.3))   # 渐隐，但托底保证可见
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # 外环主色 + 内侧一圈暗描边，保证浅色/深色背景下都可见
    d.ellipse([CX - r, CY - r, CX + r, CY + r],
              outline=(255, 106, 0, alpha), width=width)
    r2 = r - width - 2
    if r2 > 4:
        a2 = int(alpha * 0.55)
        d.ellipse([CX - r2, CY - r2, CX + r2, CY + r2],
                  outline=(40, 20, 0, a2), width=2)
    return img

import tempfile, os
tmp = tempfile.mkdtemp()
for i in range(N):
    ring_frame(i).save(f"{tmp}/f{i:03d}.png")

cmd = ["ffmpeg", "-y", "-loglevel", "error",
       "-framerate", str(FPS), "-i", f"{tmp}/f%03d.png",
       "-c:v", "qtrle", "-pix_fmt", "argb", OUT]
subprocess.run(cmd, check=True)
# 清理帧序列
for f in os.listdir(tmp):
    os.remove(os.path.join(tmp, f))
os.rmdir(tmp)
print(f"波纹片段：{OUT}  {N}帧 / {DUR}s @ {FPS}fps")
