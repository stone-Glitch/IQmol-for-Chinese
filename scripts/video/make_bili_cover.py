#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IQmol 中文版推广视频 · B站封面生成器
================================================

为什么要有这个脚本：
    原封面（bili_cover.png，2026-10-02 手工做的）上写的是
    「2112 条翻译 · 153 个模块 · 34 页手册」，
    而视频里的数据卡早已改为实测的 2125 / 155 / 34。
    封面和成片数字打架——观众扫一眼封面、再看视频，就会发现对不上，
    这恰恰违背我们「数据可核验」的立身之处。

    所以把封面也纳入脚本化：数字一律实时统计，不允许硬编码。

设计沿用原封面（实测缩到 200px 宽仍能认出「中英对比」这个信息点）：
    · 上半：原版/中文版菜单条对照（用真机录屏帧，不画菜单）
    · 中部：主标题「IQmol 全界面汉化」
    · 下部：数据行 + 开源行 + 仓库地址 + 二维码

用法：
    python3 scripts/video/make_bili_cover.py
    → build-video/out/bili_cover.png（1280×800）
"""
import os
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(ROOT)

W, H = 1280, 800
FONT_TTC = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
FONT_SC = 2# index=2 = Noto Sans CJK SC
OUT = "build-video/out/bili_cover.png"
BG = (13, 17, 26)


def f(size):
    return ImageFont.truetype(FONT_TTC, size, index=FONT_SC)


# ============================================================
# 数字一律实测，绝不硬编码
# ============================================================
def repo_stats():
    """从 translations/zh_CN.ts 实时统计。"""
    root = ET.parse("translations/zh_CN.ts").getroot()
    ctxs = root.findall("context")
    n_msg = sum(len(c.findall("message")) for c in ctxs)
    n_ctx = len(ctxs)
    unf = sum(1 for c in ctxs for m in c.findall("message")
              if (m.find("translation") is None
                  or m.find("translation").get("type") == "unfinished"
                  or not (m.find("translation").text or "").strip()))
    # 手册页数：实读 PDF。文件名是英文 IQmolUserGuide.pdf，在 doc/ 下。
    pages = None
    for cand in ("doc/IQmolUserGuide.pdf", "docs/IQmolUserGuide.pdf"):
        if os.path.exists(cand):
            out = subprocess.run(["pdfinfo", cand], capture_output=True,
                                 text=True).stdout
            m = re.search(r"Pages:\s+(\d+)", out)
            if m:
                pages = int(m.group(1))
            break
    return n_msg, n_ctx, unf, pages


N_MSG, N_CTX, N_UNF, N_PAGES = repo_stats()
assert N_UNF == 0, f"存在 {N_UNF} 条未完成翻译，封面不应发布"
assert N_PAGES, "读不到中文手册页数（doc/IQmolUserGuide.pdf）"
print(f"  实测：{N_MSG} 条翻译 / {N_CTX} 个模块 / {N_PAGES} 页手册")


# ============================================================
# 菜单条素材：从真机录屏帧裁出来，不手画
# ============================================================
def crop_menu(tag, src):
    """裁出菜单条并横向放大。原图菜单条仅 24px 高，手机端不可读。"""
    if not os.path.exists(src):
        print(f"  !! 缺素材 {src}，菜单条留空")
        return None
    subprocess.run(["ffmpeg", "-nostdin", "-y", "-ss", "3", "-i", src,
                    "-frames:v", "1", f"/tmp/cover_men_{tag}.png"],
                   capture_output=True)
    p = f"/tmp/cover_men_{tag}.png"
    if not os.path.exists(p):
        return None
    im = Image.open(p).crop((8, 3, 440, 27))
    return im.resize((int(im.width * 2.0), int(im.height * 2.0)),
                     Image.LANCZOS)


img = Image.new("RGB", (W, H), BG)
d = ImageDraw.Draw(img)

# ---------- 菜单条对照 ----------
men_en = crop_menu("en", "build-video/out/hero_viagra_en.mp4")
men_zh = crop_menu("zh", "build-video/out/hero_viagra.mp4")

# 左侧标签列宽。「中文版」三个字@38px 约 114px宽，从 x=52 起算到 166px，
# 菜单条左边缘必须 > 166 才不会被压住——留到 186。
LAB_W = 186
bx = LAB_W          # 菜单条左边缘
if men_en and men_zh:
    bar_h = 46   # 统一高度，两条等高才像对照
    def fit(w0, h0):
        s = bar_h / h0
        return int(w0 * s), bar_h
    en = men_en.resize(fit(men_en.width, men_en.height), Image.LANCZOS)
    zh = men_zh.resize(fit(men_zh.width, men_zh.height), Image.LANCZOS)
    # 两条拉到同宽（原版有 Help、中文版有 帮助，字数不同导致宽度略异，
    # 等宽才构成分屏对照的视觉块）
    bw = max(en.width, zh.width)
    def fitw(im):
        # 菜单条右边缘留 26px 边距，与左边缘的 186 对称，视觉上才居中
        return im.resize((min(bw, W - bx - 26), bar_h), Image.LANCZOS)
    en, zh = fitw(en), fitw(zh)
    bw = en.width

    y_en, y_zh = 56, 146
    for y, bar, col, lab in ((y_en, en, (214, 72, 58), "原版"),
                             (y_zh, zh, (36, 168, 96), "中文版")):
        # 色块 + 标签（标签占满左列，不被菜单条压住）
        d.rectangle([26, y + 2, 26 + 14, y + bar_h - 2], fill=col)
        d.text((52, y + (bar_h - 44) / 2), lab, font=f(38),
               fill=(240, 240, 245))
        # 白底菜单条（外扩 6px 当边框）
        d.rectangle([bx - 6, y - 6, bx + bw + 6, y + bar_h + 6],
                    fill=(247, 248, 251))
        img.paste(bar, (bx, y))
    d.text((bx + 4, y_zh + bar_h + 20),
           "同一个软件，菜单直接变中文", font=f(32), fill=(120, 200, 255))
else:
    d.text((W // 2, 120), "IQmol", font=f(96), fill=(240, 240, 245),
           anchor="mm")

# ---------- 主标题 ----------
ft = f(94)
tw = d.textbbox((0, 0), "IQmol 全界面汉化", font=ft)[2]
d.text(((W - tw) / 2, 300), "IQmol 全界面汉化", font=ft, fill=(245, 246, 250))

# ---------- 数据行（实测） ----------
fd = f(42)
s = f"{N_MSG} 条翻译  ·  {N_CTX} 个模块  ·  {N_PAGES} 页手册"
tw = d.textbbox((0, 0), s, font=fd)[2]
d.text(((W - tw) / 2, 418), s, font=fd, fill=(120, 200, 255))

# ---------- 开源行 ----------
fo = f(38)
s = "免费 · 开源 · GPL-3.0"
tw = d.textbbox((0, 0), s, font=fo)[2]
d.text(((W - tw) / 2, 490), s, font=fo, fill=(120, 220, 170))

# ---------- 仓库地址 + 二维码 ----------
qr = "build-video/out/qr_repo.png"
addr = "github.com/stone-Glitch/IQmol-for-Chinese"
fa = f(28)
tw = d.textbbox((0, 0), addr, font=fa)[2]
block_w = tw + 106
if os.path.exists(qr):
    q = Image.open(qr).convert("RGB").resize((90, 90), Image.LANCZOS)
    x0 = int((W - block_w) / 2)
    img.paste(q, (x0, 570))
    tx = x0 + 104
else:
    tx = (W - tw) / 2
d.text((tx, 600), addr, font=fa, fill=(150, 170, 195))

os.makedirs(os.path.dirname(OUT), exist_ok=True)
img.save(OUT)
print(f"  输出：{OUT}（{W}×{H}）")