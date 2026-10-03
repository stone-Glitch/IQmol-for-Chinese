#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
镜头密度自检
============

对标方法与结论见 docs/B站对标分析.md。

做法：降采样到160×90 灰度，逐帧求相邻帧平均绝对差，
超过阈值即记一次"画面变化"，0.4 秒内的相邻变化合并。

⚠️ 阈值必须选对，否则结论完全错。
   实测各视频的帧差分布差异极大（见下方分位数）：
       对标 B 沉浸式翻译  p99=27.95  max=201.0   （高对比动效）
       对标 C 分屏读顶刊  p99=15.22  max=115.5
       对标 A UVR5        p99=19.74  max=159.0
       我们（录屏+大字卡） p99= 5.35  max=164.9   （低对比）
   早期版本固定用 th=8，导致我们这种低对比画面**一次变化都测不到**，
   自检误报"首次画面变化 11.96s"，而实际第1.5 秒就有变化。
   所以这里默认 th=1，并同时输出 th=1/3/8 三档做交叉验证。

⚠️ 必须流式解码。整段读进内存会在 400s 视频上直接 OOM。

参考基准（B站同类头部作品，th=8 / th=1 两档）：
    A: UVR5      139万播放   5.91s / 1.92s
    B: 沉浸式翻译  72万播放   2.25s / 0.74s
    C: 分屏读顶刊 50万播放   2.25s / 0.90s

用法：python3 shot_density.py <视频> [标签]
"""
import os
import subprocess
import sys

import numpy as np

W, H = 160, 90
FPS = 25
MERGE_GAP = 0.4      # 秒；此间隔内的多次变化合并为一次
STILL_THRESH = 0.3   # 低于此值算"近乎静止"
THRESHOLDS = (1.0, 3.0, 8.0)


def frame_diffs(path):
    """流式解码，返回逐帧平均绝对差数组。"""
    proc = subprocess.Popen(
        ["ffmpeg", "-v", "error", "-i", path,
         "-vf", f"scale={W}:{H}", "-pix_fmt", "gray", "-f", "rawvideo", "-"],
        stdout=subprocess.PIPE, bufsize=10 ** 8)

    fsz = W * H
    prev = None
    n = 0
    diffs = []

    while True:
        buf = proc.stdout.read(fsz * 50)
        if not buf:
            break
        cnt = len(buf) // fsz
        blk = np.frombuffer(buf[:cnt * fsz], dtype=np.uint8
                            ).reshape(cnt, H, W).astype(np.float32)
        if prev is not None:
            blk = np.concatenate([prev[None, :, :], blk], axis=0)
        for i in range(1, len(blk)):
            diffs.append(float(np.abs(blk[i] - blk[i - 1]).mean()))
        prev = blk[-1]
        n += cnt
    proc.wait()

    if n < 10:
        return None, 0
    return np.array(diffs), n


def marks_for(d, th):
    marks = []
    for i in np.where(d > th)[0]:
        t = i / FPS
        if not marks or t - marks[-1] > MERGE_GAP:
            marks.append(t)
    return marks


def analyze(path, label=""):
    if not os.path.exists(path):
        print(f"文件不存在：{path}")
        return None

    d, n = frame_diffs(path)
    if d is None:
        print(f"帧数不足：{path}")
        return None

    dur = n / FPS
    if label:
        print(f"### {label}")
    print(f"  时长           {dur:.1f}s（{n} 帧）")
    print(f"  帧差分位       p50={np.percentile(d, 50):.3f} "
          f"p90={np.percentile(d, 90):.2f} "
          f"p99={np.percentile(d, 99):.2f} max={d.max():.1f}")
    print(f"  近乎静止帧     {float((d < STILL_THRESH).mean() * 100):.1f}%"
          f"   ← 对标基准 66–83%")

    res = {}
    for th in THRESHOLDS:
        marks = marks_for(d, th)
        gap = dur / max(len(marks), 1)
        first = marks[0] if marks else float("nan")
        head = sum(1 for t in marks if t < 15)
        gaps = sorted(marks[i + 1] - marks[i] for i in range(len(marks) - 1))
        med = gaps[len(gaps) // 2] if gaps else float("nan")
        short = (sum(1 for g in gaps if g < 2) / len(gaps) * 100) if gaps else 0

        print(f"  ── 阈值 {th:g} ──")
        print(f"    画面变化     {len(marks)} 次")
        print(f"    平均间隔     {gap:.2f}s"
              f"   ← 对标 0.74–1.92s（th=1）/ 2.25–5.91s（th=8）")
        print(f"    镜头中位     {med:.2f}s   短镜头占比 {short:.0f}%"
              f"   ← 对标 56–66%（th=8）")
        print(f"    首次变化     {first:.2f}s   前15秒 {head} 次"
              f"   ← 对标首次 0.48s、前15秒 4–6 次")
        res[th] = {"gap": gap, "first": first, "head15": head, "changes": len(marks)}

    print("  ⚠️ 以阈值 1 为准判断低对比画面；阈值 8 会漏掉大量变化。")
    return res


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    analyze(sys.argv[1], sys.argv[2] if len(sys.argv) > 2
            else os.path.basename(sys.argv[1]))