#!/bin/bash
# ============================================================
# IQmol 中文版推广视频 · 主合成
#   分镜（定稿见 docs/推广视频制作计划.md 第五节）
#   输出：1920×1080 @25fps H.264 MP4
#
#  ⚠️ 字幕一律走 textfile，不用 text=。
#     drawtext 的 text= 里中文标点/逗号会被滤镜链解析器拆成独立 filter
#     （报错 No such filter: '0.6'），textfile 无此风险。
# ============================================================
set -u
cd "$(dirname "$0")/../.."
ROOT="$(pwd)"   # concat 清单的路径按清单文件所在目录解析，必须用绝对路径
EDIT=build-video/edit
SEG="$EDIT/seg"
OUT=build-video/out
TMP=/tmp/iqmol_sub
mkdir -p "$SEG" "$OUT" "$TMP"
# ⚠️ 字体选择（2026-10-02 修复字幕方框）
#   DroidSansFallbackFull.ttf 缺 · ①②③ 且无拉丁字形 → 字幕出现方框。
#   NotoSansCJK-Regular.ttc = Noto Sans CJK SC 全覆盖（拉丁+CJK+·①②③）；
#   ffmpeg drawtext 直接引用 .ttc 即可，实测正常。
FONT=/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc
W=1920; H=1080
VFPS=25

# ---------- 字幕工具 ----------
# sub <in> <out> <时长> <主标题> <副标题> <y> [淡入淡出秒]
sub() {
  local in=$1 out=$2 dur=$3 big=$4 small=$5 ypos=$6 fade=${7:-0.5}
  local big_size=62 small_size=38
  local vf="drawbox=x=0:y=0:w=${W}:h=${H}:color=black@0.30:t=fill"

  if [ -n "$big" ]; then
    printf '%s' "$big" > "$TMP/big.txt"
    vf="$vf,drawtext=fontfile=${FONT}:textfile=${TMP}/big.txt:fontcolor=white:fontsize=${big_size}:x=(w-text_w)/2:y=${ypos}:enable='between(t,${fade},${dur}-${fade})'"
  fi
  if [ -n "$small" ]; then
    printf '%s' "$small" > "$TMP/small.txt"
    local y2=$(( ypos + big_size + 24 ))
    vf="$vf,drawtext=fontfile=${FONT}:textfile=${TMP}/small.txt:fontcolor=0x8FC8FF:fontsize=${small_size}:x=(w-text_w)/2:y=${y2}:enable='between(t,${fade},${dur}-${fade})'"
  fi

  ffmpeg -y -i "$in" -t "$dur" -vf "$vf,format=yuv420p" \
    -r $VFPS -c:v libopenh264 -preset veryfast -crf 23 "$out"
}

# ---------- 角标工具 ----------
badge() { # badge <in> <out> <label>
  printf '%s' "$3" > "$TMP/badge.txt"
  ffmpeg -y -i "$1" \
    -vf "drawbox=x=0:y=0:w=${W}:h=88:color=black@0.55:t=fill,\
drawtext=fontfile=${FONT}:textfile=${TMP}/badge.txt:fontcolor=white:fontsize=44:x=56:y=20,\
format=yuv420p" \
    -r $VFPS -c:v libopenh264 -preset veryfast -crf 23 "$2"
}

echo "### [1/6] 段1 钩子（8s：3 段分子快切）"
ffmpeg -y -i "$EDIT/hook_a.mp4" -i "$EDIT/hook_b.mp4" -i "$EDIT/hook_c.mp4" \
  -filter_complex "[0:v]trim=0:2.66,setpts=PTS-STARTPTS[v0];\
[1:v]trim=0:2.67,setpts=PTS-STARTPTS[v1];\
[2:v]trim=0:2.67,setpts=PTS-STARTPTS[v2];\
[v0][v1][v2]concat=n=3:v=1:a=0[v]" \
  -map "[v]" -r $VFPS -c:v libopenh264 -preset veryfast -crf 24 "$SEG/s1_raw.mp4" 2>/dev/null
sub "$SEG/s1_raw.mp4" "$SEG/s1.mp4" 8 "还在为英文界面头大？" "" 800 0.6
[ -f "$SEG/sX.mp4" ] || true
echo "    ok"

echo "### [2/6] 段2 痛点（10s）"
sub "$EDIT/pain.mp4" "$SEG/s2.mp4" 10 "教程翻三遍还是懵" "菜单找不到 · 手册是英文" 790 0.6
[ -f "$SEG/sX.mp4" ] || true
echo "    ok"

echo "### [3/6] 段3 转折（10s：英文 1.5s → 中文 8.5s）"
#素材仅 1.52s，中文段用 loop 补足；英文段做轻微放大避免突兀
# -stream_loop 对 1.5s 短输入不可靠，改用滤镜级 loop 滤镜
ffmpeg -y -i "$OUT/shot_3_zh.mp4" -t 8.5 \
  -vf "loop=loop=-1:size=32767:start=0,scale=${W}:${H},setsar=1,fps=$VFPS,format=yuv420p" \
  -c:v libopenh264 -preset veryfast -crf 24 "$SEG/s3zh.mp4" 2>/dev/null
ffmpeg -y -i "$OUT/shot_3_en.mp4" -t 1.5 \
  -vf "scale=${W}:${H},setsar=1,fps=$VFPS,format=yuv420p" \
  -c:v libopenh264 -preset veryfast -crf 24 "$SEG/s3en.mp4" 2>/dev/null
printf "file '%s'\nfile '%s'\n" "$ROOT/$SEG/s3en.mp4" "$ROOT/$SEG/s3zh.mp4" > "$SEG/s3.txt"
ffmpeg -y -f concat -safe 0 -i "$SEG/s3.txt" -c copy "$SEG/s3_raw.mp4" 2>/dev/null
sub "$SEG/s3_raw.mp4" "$SEG/s3.mp4" 10 "IQmol 中文版 · 全界面汉化" "" 800 0.6
[ -f "$SEG/sX.mp4" ] || true
echo "    ok"

echo "### [4/6] 段4 能力（27s：三组录屏 + 数据条）"
ffmpeg -y -i "$OUT/clip_4a_buildmol.mp4" -i "$OUT/clip_4b_qui.mp4" -i "$OUT/clip_4c_orbital.mp4" \
  -filter_complex "[0:v]trim=0:8,setpts=PTS-STARTPTS,fps=$VFPS[v0];\
[1:v]trim=0:8,setpts=PTS-STARTPTS,fps=$VFPS[v1];\
[2:v]trim=0:8,setpts=PTS-STARTPTS,fps=$VFPS[v2];\
[v0][v1][v2]concat=n=3:v=1:a=0[v]" \
  -map "[v]" -r $VFPS -c:v libopenh264 -preset veryfast -crf 24 "$SEG/s4_raw.mp4" 2>/dev/null

ffmpeg -y -i "$SEG/s4_raw.mp4" -t 8 -c copy "$SEG/s4a.mp4" 2>/dev/null
ffmpeg -y -ss 8 -i "$SEG/s4_raw.mp4" -t 8 -c copy "$SEG/s4b.mp4" 2>/dev/null
ffmpeg -y -ss 16 -i "$SEG/s4_raw.mp4" -t 8 -c copy "$SEG/s4c.mp4" 2>/dev/null
badge "$SEG/s4a.mp4" "$SEG/s4a_l.mp4" "① 建模 · 元素周期表"
badge "$SEG/s4b.mp4" "$SEG/s4b_l.mp4" "② 计算 · Q-Chem 设置"
badge "$SEG/s4c.mp4" "$SEG/s4c_l.mp4" "③ 可视化 · 轨道与性质"

# 数据条卡
# ⚠️ 数字必须从 translations/zh_CN.ts 实时统计，不要硬编码。
#    画面底部写着「数据可在 translations/zh_CN.ts 逐条核验」，
#    硬编码的数字一旦随翻译更新而失准，就成了自打脸的破绽
#    （历史上就发生过：画面 2112 / 文档 2035 / 实际早已不是 2112）。
python3 - <<'PY'
import os, re, subprocess
import xml.etree.ElementTree as ET
from PIL import Image, ImageDraw, ImageFont

# ---- 从 ts 实测三项数字 ----
TS = "translations/zh_CN.ts"
root = ET.parse(TS).getroot()
contexts = root.findall("context")
n_msg = sum(len(c.findall("message")) for c in contexts)
n_ctx = len(contexts)
n_unfinished = 0
for c in contexts:
    for m in c.findall("message"):
        t = m.find("translation")
        if t is None or t.get("type") == "unfinished" or not (t.text or "").strip():
            n_unfinished += 1
# 手册页数：实读仓库内的中文手册 PDF。
# ⚠️ 文件名是英文 IQmolUserGuide.pdf（在 doc/ 下），不叫「手册」——
#    早先按 *手册* / docs/ 去找会误判为"手册不存在"，务必用真实路径。
n_pages = None
for cand in ("doc/IQmolUserGuide.pdf",
             "docs/IQmolUserGuide.pdf",
             "docs/IQmol用户手册.pdf"):
    if os.path.exists(cand):
        try:
            out = subprocess.run(["pdfinfo", cand], capture_output=True, text=True).stdout
            m = re.search(r"Pages:\s+(\d+)", out)
            if m:
                n_pages = int(m.group(1))
        except Exception:
            pass
        break
print(f"  数据卡实测: {n_msg} 条翻译 / {n_ctx} 个界面模块 / "
      f"{str(n_pages) + ' 页中文手册' if n_pages else '手册未找到'}"
      f"（unfinished {n_unfinished}）")
assert n_unfinished == 0, f"存在 {n_unfinished} 条未完成翻译，数据卡不应发布"

W, H = 1920, 1080
# ⚠️ 这里必须用含拉丁字形的字体，否则 2112 / 153 / 34 与 GPL-3.0 会变方框
F = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
FIDX = 2   # Noto Sans CJK SC
def mk(size):
    return ImageFont.truetype(F, size, index=FIDX)
img = Image.new("RGB", (W, H), (20, 26, 36))
d = ImageDraw.Draw(img)
f_h = mk(54)
f_n = mk(96)
f_l = mk(34)
f_s = mk(30)

def center(y, t, f, c):
    w = d.textbbox((0, 0), t, font=f)[2]
    d.text(((W - w) / 2, y), t, font=f, fill=c)

center(110, "建模 · 计算 · 可视化", f_h, (120, 200, 255))
for i, (n, l) in enumerate([(str(n_msg), "条翻译"),
                            (str(n_ctx), "个界面模块"),
                            (str(n_pages) if n_pages else "—",
                             "页中文手册" if n_pages else "手册未找到")]):
    x = 380 + i * 580
    d.text((x, 370), n, font=f_n, fill=(255, 255, 255))
    w = d.textbbox((0, 0), n, font=f_n)[2]
    d.text((x + w / 2, 492), l, font=f_l, fill=(150, 172, 196))
center(700, "开源免费 · GPL-3.0", f_h, (200, 220, 240))
center(890, f"数据可在 translations/zh_CN.ts 逐条核验（{n_msg} 条 / 0 未完成）",
       f_s, (110, 132, 158))
img.save("build-video/edit/datacard.png")
PY
ffmpeg -y -loop 1 -i "$EDIT/datacard.png" -t 4 -r $VFPS \
  -c:v libopenh264 -preset veryfast -crf 23 -pix_fmt yuv420p "$SEG/s4d_l.mp4" 2>/dev/null

for f in s4a_l s4b_l s4c_l s4d_l; do
  [ -f "$SEG/$f.mp4" ] || { echo "缺 $f"; exit 1; }
done
printf "file '%s'\n" "$ROOT/$SEG/s4a_l.mp4" "$ROOT/$SEG/s4b_l.mp4" "$ROOT/$SEG/s4c_l.mp4" "$ROOT/$SEG/s4d_l.mp4" > "$SEG/s4.txt"
ffmpeg -y -f concat -safe 0 -i "$SEG/s4.txt" -c copy "$SEG/s4.mp4" 2>/dev/null
[ -f "$SEG/sX.mp4" ] || true
echo "    ok"

echo "### [5/6] 段5 收尾（20s：分子旋转 4s + 收尾卡 16s）"
# clip_5_rotate.mp4 只有 6s，不能 -ss 16
ffmpeg -y -ss 1 -t 4 -i "$OUT/clip_5_rotate.mp4" -c:v libopenh264 \
  -preset veryfast -crf 23 -pix_fmt yuv420p -r $VFPS "$SEG/s5a.mp4" 2>/dev/null
# 收尾卡 16s：二维码需足够停留时间供观众扫描
ffmpeg -y -loop 1 -i "$EDIT/endcard.png" -t 16 -r $VFPS \
  -vf "format=yuv420p" -c:v libopenh264 -preset veryfast -crf 23 "$SEG/s5b.mp4" 2>/dev/null
for f in s5a s5b; do
  [ -f "$SEG/$f.mp4" ] || { echo "缺 $f"; exit 1; }
done
printf "file '%s'\nfile '%s'\n" "$ROOT/$SEG/s5a.mp4" "$ROOT/$SEG/s5b.mp4" > "$SEG/s5.txt"
ffmpeg -y -f concat -safe 0 -i "$SEG/s5.txt" -c copy "$SEG/s5.mp4" 2>/dev/null
[ -f "$SEG/sX.mp4" ] || true
echo "    ok"

echo "### [6/6] BGM + 总拼接"
TOTAL=75
SEG5_TOTAL=75
ffmpeg -y \
  -f lavfi -i "sine=frequency=261.63:duration=${TOTAL}:sample_rate=44100" \
  -f lavfi -i "sine=frequency=392.00:duration=${TOTAL}:sample_rate=44100" \
  -f lavfi -i "sine=frequency=220.00:duration=${TOTAL}:sample_rate=44100" \
  -filter_complex "[0:a]volume=0.16[a0];[1:a]volume=0.10[a1];[2:a]volume=0.12[a2];\
[a0][a1][a2]amix=inputs=3:duration=longest,\
afade=t=in:st=0:d=2,afade=t=out:st=$((TOTAL-3)):d=3,\
alimiter=limit=0.85,loudnorm=I=-18:TP=-1.5[a]" \
  -map "[a]" -t $TOTAL -c:a aac -b:a 160k "$EDIT/bgm.m4a" 2>/dev/null

for f in s1 s2 s3 s4 s5; do
  if [ ! -f "$SEG/$f.mp4" ]; then echo "!! 缺段 $f，中止"; exit 1; fi
  d=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$SEG/$f.mp4" 2>/dev/null)
  printf "    %-4s %ss\n" "$f" "${d%.*}"
done
printf "file '%s'\n" "$ROOT/$SEG/s1.mp4" "$ROOT/$SEG/s2.mp4" "$ROOT/$SEG/s3.mp4" "$ROOT/$SEG/s4.mp4" "$ROOT/$SEG/s5.mp4" > "$SEG/all.txt"
ffmpeg -y -f concat -safe 0 -i "$SEG/all.txt" -i "$EDIT/bgm.m4a" \
  -map 0:v -map 1:a -c:v copy -c:a aac -b:a 160k -movflags +faststart \
  -shortest "$OUT/iqmol_promo_zh.mp4" 2>/dev/null

echo
echo "### 成片校验"
ffprobe -v error -select_streams v:0 -show_entries stream=codec_name,width,height,r_frame_rate,nb_frames \
  -show_entries format=duration,size -of default=nw=1 "$OUT/iqmol_promo_zh.mp4"
