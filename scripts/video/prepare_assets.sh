#!/bin/bash
# ============================================================
# IQmol 中文版推广视频 · 素材预处理
# 生成：钩子段分子快切 / 痛点段术语堆叠 / 收尾卡（含二维码）
# ============================================================
set -eu
cd "$(dirname "$0")/../.."
EDIT=build-video/edit
OUT=build-video/out
mkdir -p "$EDIT" "$OUT"
# ⚠️ 字体选择（2026-10-02 修复方框问题）
#   DroidSansFallbackFull.ttf 在 PIL 下不提供拉丁字形，且缺 · ①②③ ⭐，
#   导致英文/数字/间隔号全部渲染为方框（数据条 2112/153/34 曾整块变方框）。
#   NotoSansCJK-Regular.ttc index2 = Noto Sans CJK SC：拉丁+CJK+·①②③ 全覆盖，
#   仅缺 ⭐（U+2B50），用 NotoSansSymbols2 做回退。
FONT=/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc
FONT_IDX=2
SYMFONT=/usr/share/fonts/truetype/noto/NotoSansSymbols2-Regular.ttf
REPO=https://github.com/stone-Glitch/IQmol-for-Chinese

echo "###1) 生成收尾卡二维码"
python3 - <<PY
import qrcode
qr = qrcode.QRCode(version=None, box_size=12, border=2,
                   error_correction=qrcode.constants.ERROR_CORRECT_H)
qr.add_data("$REPO")
qr.make(fit=True)
img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
img.save("$EDIT/qrcode.png")
print("  二维码", img.size)
PY

echo "### 2) 收尾卡背景（深色渐变 + 文字 + 二维码）"
#用 Python 画布生成，比 ffmpeg 滤镜更可控
python3 - <<'PY'
from PIL import Image, ImageDraw, ImageFont
W, H = 1920, 1080
FONT = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
FONT_IDX = 2   # Noto Sans CJK SC
SYMFONT = "/usr/share/fonts/truetype/noto/NotoSansSymbols2-Regular.ttf"  # 提供 ⭐

def mkfont(size):
    return ImageFont.truetype(FONT, size, index=FONT_IDX)

img = Image.new("RGB", (W, H), (18, 24, 34))
d = ImageDraw.Draw(img)
# 垂直渐变
for y in range(H):
    t = y / H
    d.line([(0, y), (W, y)],
           fill=(int(18 + 12 * t), int(24 + 18 * t), int(34 + 28 * t)))

f_title = mkfont(76)
f_sub   = mkfont(46)
f_url   = mkfont(36)
f_star  = mkfont(40)
f_sym   = ImageFont.truetype(SYMFONT, 40)   # ⭐ 单独用符号字体

def ctext(y, text, font, fill):
    w = d.textbbox((0, 0), text, font=font)[2]
    d.text(((W - w) / 2, y), text, font=font, fill=fill)

ctext(190, "开源免费 · GPL-3.0", f_sub, (120, 200, 255))
ctext(300, "IQmol 中文版", f_title, (255, 255, 255))
ctext(420, "建模 · 计算 · 可视化", f_sub, (200, 215, 235))

# 二维码（居中偏下）
qr = Image.open("build-video/edit/qrcode.png").convert("RGB").resize((300, 300), Image.NEAREST)
qx, qy = (W - 300) / 2, 520
img.paste(qr, (int(qx), int(qy)))
d.rectangle([int(qx) - 8, int(qy) - 8, int(qx) + 308, int(qy) + 308],
            outline=(90, 110, 140), width=3)

# URL
url = "github.com/stone-Glitch/IQmol-for-Chinese"
w = d.textbbox((0, 0), url, font=f_url)[2]
d.text(((W - w) / 2, 850), url, font=f_url, fill=(130, 190, 255))

# Star 提示：文本用 CJK 字体，末尾 ⭐ 用符号字体拼接（CJK 字体无 U+2B50）
star_txt = "觉得好用，顺手点个 Star"
w1 = d.textbbox((0, 0), star_txt, font=f_star)[2]
star_glyph = "⭐"
w2 = d.textbbox((0, 0), star_glyph, font=f_sym)[2]
total = w1 + 8 + w2
x0 = (W - total) / 2
y0 = 920
d.text((x0, y0), star_txt, font=f_star, fill=(255, 205, 90))
d.text((x0 + w1 + 8, y0 + 4), star_glyph, font=f_sym, fill=(255, 205, 90))

img.save("build-video/edit/endcard.png")
print("  收尾卡已生成（Noto CJK SC + Symbols2 ⭐）")
PY

echo "### 3) 钩子段：分子快切（3 组，各 2.6s）"
#从 hero 视频切 3 段不同角度，模拟"分子快切"
ffmpeg -y -ss 1 -t 2.67 -i "$OUT/hero_viagra.mp4" \
  -vf "scale=1920:1080,format=yuv420p" -r 25 -c:v libopenh264 -preset veryfast -crf 24 \
  "$EDIT/hook_a.mp4" 2>/dev/null
ffmpeg -y -ss 7 -t 2.67 -i "$OUT/hero_viagra.mp4" \
  -vf "scale=1920:1080,format=yuv420p" -r 25 -c:v libopenh264 -preset veryfast -crf 24 \
  "$EDIT/hook_b.mp4" 2>/dev/null
ffmpeg -y -ss 13 -t 2.67 -i "$OUT/hero_viagra.mp4" \
  -vf "scale=1920:1080,format=yuv420p" -r 25 -c:v libopenh264 -preset veryfast -crf 24 \
  "$EDIT/hook_c.mp4" 2>/dev/null
echo "  钩子素材 3 段完成"

echo "### 4) 痛点段：灰调背景 + 英文术语堆叠（10s）"
python3 - <<'PY'
from PIL import Image, ImageDraw, ImageFont
import random
W, H = 1920, 1080
# 拉丁术语堆叠用含拉丁字形的字体（Droid 无拉丁字形会出方框）
FONT = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
FONT_IDX = 2
random.seed(7)

img = Image.new("RGB", (W, H), (38, 40, 44))
d = ImageDraw.Draw(img)
f_t = ImageFont.truetype(FONT, 120, index=FONT_IDX)
f_k = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 40)

# 中央大字：英文界面痛点
big = "English Manual"
w = d.textbbox((0, 0), big, font=f_t)[2]
d.text(((W - w) / 2, 300), big, font=f_t, fill=(120, 124, 132))

terms = ["Gaussian", "ORCA", "XYZ", "Cube File", "Wavefunction",
         "Population Analysis", "Orbital Viewer", "Force Field",
         "Molecular Dynamics", "Basis Set", "SCF Convergence"]
# 灰色浮动的术语云
for i, t in enumerate(terms):
    x = random.randint(80, W - 400)
    y = random.randint(60, 180) + (i % 4) * 200
    a = random.randint(70, 150)
    d.text((x, y), t, font=f_k, fill=(a, a, a + 6))

img.save("build-video/edit/pain_base.png")
print("  痛点底图完成")
PY
# 底图 +缓慢漂移的动态层
ffmpeg -y -loop 1 -i "$EDIT/pain_base.png" -t 10 -r 25 \
  -vf "format=yuv420p" -c:v libopenh264 -preset veryfast -crf 24 \
  "$EDIT/pain.mp4" 2>/dev/null
echo "  痛点段完成"

echo
echo "### 素材清单"
for f in hook_a hook_b hook_c pain; do
  d=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$EDIT/$f.mp4")
  printf "  %-8s %ss\n" "$f" "${d%.*}"
done
ls -la "$EDIT/endcard.png" "$EDIT/qrcode.png"
