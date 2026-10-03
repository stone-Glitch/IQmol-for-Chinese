#!/usr/bin/env python3
# ============================================================
#宣传文案数字核验闸门
#
# 为什么需要这个：
#   视频画面上写着「2125 条翻译 · 155 个界面模块 · 34 页中文手册」，
#   并且底部承诺「数据可在 translations/zh_CN.ts 逐条核验」。
#   既然承诺可核验，那么**所有文档里的这三个数字**就必须与仓库现状一致。
#   历史上已经漂移过三次：
#     2026-09-13  1519 / 111   （早期快照）
#     2026-10-02  2112 / 153   ← 视频画面用的就是这个
#     2026-10-03  2125 / 155   ← 真实值
#   文案散在 4 个 md 里，改翻译时没人会记得同步改文案，
#   于是出现「视频说2112、简介说 2035、实际 2125」三方打架。
#
# 做什么：
#   1. 从translations/zh_CN.ts 实时统计 message / context / unfinished；
#   2. 用 pdfinfo 实读 doc/IQmolUserGuide.pdf 的页数；
#   3. 扫描 docs/推广视频/ 下所有 md，把陈旧数字揪出来；
#   4. 顺带核对成片的实测时长/分辨率是否与文档写的一致。
#
# 用法：
#   python3 scripts/video/verify_doc_numbers.py
#   退出码 0 = 全部一致；1 = 发现漂移（CI 可直接拿它当门禁）
# ============================================================
import os
import re
import subprocess
import sys
import glob

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(ROOT)

# 已废弃的历史快照。命中即报错——留着是为了让"回到旧数字"这种回退被发现。
STALE = {
    "1519": "2026-09-13 快照",
    "111": "2026-09-13 快照的 context 数",
    "2112": "2026-10-02 快照（错数字，曾上屏）",
    "2035": "2026-10-02 快照（错数字，曾进简介）",
    "153": "2026-10-02 快照的 context 数",
}
# 这些词出现在正常语境里时不当作数字误报
STALE_ALLOW = {"111": [], "153": []}

fail = []
warn = []


def read_tsv_stats():
    """从 zh_CN.ts 实时统计。用 ElementTree 而不是 grep——grep 会被注释里的
    文本或多行标签骗到，XML 解析器不会。"""
    import xml.etree.ElementTree as ET

    p = "translations/zh_CN.ts"
    if not os.path.exists(p):
        print(f"!! 缺 {p}")
        sys.exit(1)
    root = ET.parse(p).getroot()
    ctxs = root.findall("context")
    n_msg = sum(len(c.findall("message")) for c in ctxs)
    n_ctx = len(ctxs)
    n_unf = 0
    for c in ctxs:
        for m in c.findall("message"):
            t = m.find("translation")
            if t is None or t.get("type") == "unfinished" or not (t.text or "").strip():
                n_unf += 1
    return n_msg, n_ctx, n_unf


def read_pdf_pages():
    """实读手册 PDF 页数。文件名是英文 IQmolUserGuide.pdf，
    目录是 doc/（不是 docs/）——历史上就是因为 glob 写成 docs/*.pdf 才漏掉它。"""
    import re

    for cand in ("doc/IQmolUserGuide.pdf", "docs/IQmolUserGuide.pdf"):
        if os.path.exists(cand):
            out = subprocess.run(["pdfinfo", cand], capture_output=True,
                                 text=True).stdout
            m = re.search(r"Pages:\s+(\d+)", out)
            if m:
                return int(m.group(1)), cand
    return None, None


n_msg, n_ctx, n_unf = read_tsv_stats()
n_pages, pdf_path = read_pdf_pages()

print("=" * 62)
print("仓库实测（发布前必须与文案一致）")
print("=" * 62)
print(f"  translations/zh_CN.ts   {n_msg} 条翻译 / {n_ctx} 个 context / "
      f"{n_unf} 条 unfinished")
if n_pages:
    print(f"  {pdf_path:<24} {n_pages} 页")
else:
    fail.append("找不到中文手册 PDF（doc/IQmolUserGuide.pdf）")
    print("  !! 找不到中文手册 PDF")

if n_unf:
    fail.append(f"存在 {n_unf} 条 unfinished 翻译，不能发布")

# ---------- 扫文档 ----------
DOCDIR = "docs/推广视频"
docs = sorted(glob.glob(f"{DOCDIR}/*.md"))
print("-" * 62)
print(f"扫描 {len(docs)} 个推广文档")
print("-" * 62)

# 只在这些数字紧邻"翻译/context/条/个/页"等语境时才判定，
# 避免把无关的数字（如 111 MB、153 行代码）误报。
CTX = r"(?:条翻译|条译文|个\s*context|个界面模块|context|条|个模块)"

for f in docs:
    lines = open(f, encoding="utf-8").read().splitlines()
    for i, line in enumerate(lines, 1):
        for num, why in STALE.items():
            # 匹配 "2112 条翻译" / "2112/153/34" / "= 2112（" 这类紧邻用法
            pats = [rf"(?<![\d.]){re.escape(num)}\s*{CTX}",
                    rf"{re.escape(num)}\s*/\s*\d+\s*/\s*\d+",
                    rf"=\s*{re.escape(num)}\s*[（(]"]
            for pat in pats:
                if re.search(pat, line):
                    # 允许行内自带"已废弃/历史快照"说明的自我标注行
                    if any(k in line for k in ("已废弃", "历史快照", "快照，均已废弃")):
                        warn.append(f"{f}:{i} 提及历史快照 {num}（已标注废弃）")
                    else:
                        fail.append(f"{f}:{i} 陈旧数字 {num}（{why}）→ 应为 "
                                    f"{n_msg}/{n_ctx}/{n_pages}\n      {line.strip()[:110]}")
                    break

# ---------- 核对成片实测 vs 文档写法 ----------
print("-" * 62)
print("成片实测 vs 文档写法")
print("-" * 62)
mp4 = "build-video/out/iqmol_promo_bili.mp4"
if os.path.exists(mp4):
    d = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                        "format=duration,size", "-show_entries",
                        "stream=width,height", "-of", "default=nw=1", mp4],
                       capture_output=True, text=True).stdout
    dur = re.search(r"duration=([\d.]+)", d)
    size = re.search(r"size=(\d+)", d)
    wh = re.findall(r"(?:width|height)=(\d+)", d)
    dur = float(dur.group(1)) if dur else 0
    size = int(size.group(1)) if size else 0
    print(f"  时长 {dur:.2f}s / 大小 {size} 字节 / {wh[0]}x{wh[1]}")
    for f in docs:
        for i, line in enumerate(open(f, encoding="utf-8").read().splitlines(), 1):
            for m in re.finditer(r"(\d+\.\d{2,3})s\s*/\s*1920", line):
                if abs(float(m.group(1)) - dur) > 0.05:
                    fail.append(f"{f}:{i} 文档写 {m.group(1)}s，实测 {dur:.2f}s")
else:
    print("  （成片不存在，跳过）")

# ---------- 核对封面数字 ----------
# 封面不在 docs/ 里，但同样会暴露在B站信息流里，数字同样不能错。
# （原封面写着 2112/153，而视频已是 2125/155——观众扫一眼就能发现对不上。）
print("-" * 62)
print("封面数字 vs 仓库实测")
print("-" * 62)
cover = "build-video/out/bili_cover.png"
if os.path.exists(cover):
    import zlib
    # 极简 PNG 文本块扫描：把 IDAT 之外的所有字节捞出来找数字字符串
    raw = open(cover, "rb").read()
    found = [n for n in (str(n_msg), str(n_ctx), str(n_pages)) if n.encode() in raw]
    # PNG 是无损的，图像数据被压缩过，不能靠字节搜数字。
    # 改成实跑生成脚本到临时目录再比像素——太重，这里只做存在性+尺寸检查，
    # 真正的数字校验交给 make_bili_cover.py 内的assert。
    from PIL import Image
    w, h = Image.open(cover).size
    print(f"  {cover}  {w}×{h}")
    if (w, h) != (1280, 800):
        warn.append(f"封面尺寸 {w}×{h}，非标准 1280×800")
    print("  数字由 scripts/video/make_bili_cover.py 实测绘制，"
          "重跑该脚本即可刷新")
else:
    print("  （封面不存在，跳过）")

# ---------- 结论 ----------
print("=" * 62)
for w in dict.fromkeys(warn):
    print(f"  [提示] {w}")
if fail:
    print(f"\n✗ 发现 {len(fail)} 处数字漂移：")
    for x in fail:
        print(f"  - {x}")
    sys.exit(1)
print(f"\n✓ 全部一致：{n_msg} 条 / {n_ctx} context / {n_pages} 页，"
      f"文档与仓库无漂移")
sys.exit(0)