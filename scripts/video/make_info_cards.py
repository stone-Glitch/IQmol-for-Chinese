#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IQmol 中文版推广视频 · B站版信息卡生成器
================================================

依据：docs/B站对标分析.md 的实测结论

对标三个 B站同类头部作品（UVR5 139万播放 / 沉浸式翻译 72万 / 分屏读顶刊 50万），
实测画面变化间隔 2.25s、短镜头占比 56–66%、静态帧占比 73–88%。

我们原片：间隔 6.25s、短镜头 18%、静态帧 97.8%。

三个头部作品的共同视觉语言（抽帧观察）：
  · 纯色背景 + 超大粗体关键字幕，一个信息点占满一屏
  · 字体带黑色描边或硬阴影，压在画面上部 1/3，永不遮挡操作区
  · 高饱和纯色/深色渐变底，与录屏画面形成强对比

本脚本生成 6 张大字信息卡，穿插在各段之间打断静止帧。
每张卡只讲一件事，2.0–2.6 秒，符合"每个镜头一个信息点"的对标节奏。

用法：python3 make_info_cards.py <输出目录>
"""
import sys
import os
from PIL import Image, ImageDraw, ImageFont

W, H = 1920, 1080

FONT_TTC = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
FONT_SC_INDEX = 2          # index=2 = Noto Sans CJK SC
SYMFONT = "/usr/share/fonts/truetype/noto/NotoSansSymbols2-Regular.ttf"


def f(size):
    return ImageFont.truetype(FONT_TTC, size, index=FONT_SC_INDEX)


def fs(size):
    return ImageFont.truetype(SYMFONT, size)


def stroke_text(d, xy, text, font, fill, stroke=(0, 0, 0), width=6, anchor_center=None):
    """带黑色描边的文字 —— 对标作品全部使用描边而非半透明底条。"""
    x, y = xy
    if anchor_center:
        w = d.textbbox((0, 0), text, font=font)[2]
        x -= w / 2
    d.text((x, y), text, font=font, fill=fill,
           stroke_width=width, stroke_fill=stroke)


# ============================================================
# 卡片定义
#
# 每个元组：(文件名, 底色, 顶部小标签, 主标题行, 副标题行或None, 时长)
# 主标题字号统一 108，副标题 68，顶部标签 40
#
# 内容策略参考对标 C「分屏读顶刊」：靠**提问**留人；
# 参考对标 A/B：直接说收益，不说工作量。
# 2112/153/34 这组数字只保留 2112（最直观），且放在"值多少"而不是"我们做了多少"
#
# ⚠️ hook 卡刻意做短（1.6s / 1.4s）。实测本片首次画面变化若晚于2.8s，
#    就会在B站信息流里被直接划走 —— 对标作品是 0.48s。
#    卡内还有 zoompan 推近在1.4s 处开始产生帧差，所以实际首次变化更早。
# ============================================================
CARDS = [
    # ---------- 开场前两张：0–3 秒必须出画面变化 ----------
    (
        "hook1", (18, 22, 30), None,
        "474 处界面文本",
        "菜单·对话框·按钮·提示 全部中文化",
        1.6,
    ),
    (
        "hook2", (18, 22, 30), None,
        "做科研，不必再见英文菜单",
        None,
        1.4,
    ),
    # ---------- 汉化专业度：和机翻拉开差距 ----------
    # 这是本片"汉化重点"的核心钩子——不止翻译了文字，而是做了
    # 计算化学术语规范化（证据来自 zh_CN.qm 里的翻译注释）：
    #   弛豫密度（不是机翻的"松弛密度"）、冻结核近似（frozen core，标准术语）、
    #   区分 Singles 单激发 / Doubles 双激发、文件格式名与快捷键保留英文。
    # 放在开场紧跟 hook1/hook2，前 10 秒把"汉化规模 + 专业度"一次讲透。
    (
        "term", (18, 22, 30), None,
        "翻译得专业",
        "弛豫密度（非松弛密度）·冻结核近似·保留快捷键",
        2.0,
    ),
    # ---------- 中段：痛点提问，打断连续录屏 ----------
    (
        "pain1", (24, 34, 54), "你是不是也这样",
        "菜单看不懂",
        None,
        2.0,
    ),
    (
        "pain2", (24, 34, 54), "你是不是也这样",
        "报错看不懂",
        None,
        2.0,
    ),
    # ---------- 功能卡：把"我们做了什么"翻译成"你能得到什么" ----------
    (
        "gain1", (16, 58, 48), None,
        "建模 · 计算 · 可视化",
        "全中文，不需要切语言包",
        2.2,
    ),
    # ---------- 结尾前：引导到完整教程 ----------
    (
        "end1", (32, 26, 52), None,
        "免费 · 开源 · GPL-3.0",
        "仓库和中文手册就在简介里",
        2.2,
    ),
]


def build(outdir):
    os.makedirs(outdir, exist_ok=True)
    made = []

    for name, bg, tag, title, sub, dur in CARDS:
        img = Image.new("RGB", (W, H), bg)
        d = ImageDraw.Draw(img)

        # 背景装饰：斜向细条纹 + 角部圆块。
        # 对标 A/B 的底图都有这类低对比几何元素，但强度都很低——
        # 只做质感，不抢文字。这里的圆只提亮 6 级，之前提 16 级太扎眼。
        for k in range(-2, 14):
            x0 = k * 160
            d.polygon([(x0, H), (x0 + 70, H), (x0 + 70 + 300, 0), (x0 + 300, 0)],
                      fill=tuple(c + 5 for c in bg))
        d.ellipse([W - 300, -190, W + 170, 280], fill=tuple(
            min(255, c + 8) for c in bg))

        y = 300

        if tag:
            tf = f(40)
            tw = d.textbbox((0, 0), tag, font=tf)[2]
            stroke_text(d, ((W - tw) / 2, y - 92), tag, tf,
                        (130, 190, 255), width=3)

        # 主标题：108px 粗体 + 黑描边，字号占画面高度约 10%
        tf = f(108)
        stroke_text(d, (W / 2, y), title, tf, (255, 255, 255),
                    width=8, anchor_center=True)

        if sub:
            # 56px 在1080p 下实测偏小，移动端会糊。对标作品的副标题
            # 普遍和主标题同量级，这里提到 68px。
            sf = f(68)
            stroke_text(d, (W / 2, y + 205), sub, sf, (178, 214, 255),
                        width=5, anchor_center=True)

        path = os.path.join(outdir, f"card_{name}.png")
        img.save(path)
        made.append((path, dur))

    # ---- 输出 ffmpeg 用的时长清单，供合成脚本读取 ----
    lst = os.path.join(outdir, "cards.tsv")
    with open(lst, "w", encoding="utf-8") as fh:
        for path, dur in made:
            fh.write(f"{path}\t{dur}\n")

    total = sum(d for _, d in made)
    print(f"  信息卡 ×{len(made)} 已生成，总时长 {total:.1f}s")
    for path, dur in made:
        print(f"    {os.path.basename(path):<22} {dur}s")
    return made


if __name__ == "__main__":
    outdir = sys.argv[1] if len(sys.argv) > 1 else "/tmp/iqmol_cards"
    build(outdir)