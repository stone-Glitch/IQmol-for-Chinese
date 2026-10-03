#!/bin/bash
# ============================================================
# IQmol 中文版推广视频 · B站专用版
#
#  与通用版（compose_main.sh）的差异——只改前8 秒：
#   通用版：分子空场慢慢浮现 + 8s 后才出字幕（静帧率 73%）
#   B站版：0.0-2.4s 中英菜单闪切 4 下 → 2.4-4.8s 左右分屏对照
#          → 4.8-8.0s 中文界面实拍（原有素材）
#   理由：B站信息流靠封面+标题点进来，但前15 秒决定完播。
#        开场直接给"中英对比"这个最强信息点，去掉空场。
#
#  输出：1920×1080 @25fps，与通用版同为 75s，可直接替换发布
# ============================================================
set -eu
# ⚠️ 所有 ffmpeg 调用都必须带 -nostdin（本脚本已统一加好，改新命令时别漏）。
#    原因：下面`while read ... done < cards.tsv` 循环的重定向会让 cards.tsv
#    成为**整个子进程树**的 stdin。ffmpeg 默认从 stdin 读（用于按 q 提前退出），
#    每跑一次就吃掉了 tsv 开头一个字节的文件偏移，于是下一轮 read 少读首字符：
#    实测 png 从"/tmp/iqmol_cards/card_pain2.png" 变成"tmp/iqmol_cards/card_pain2.png"，
#    ffmpeg 随即报文件不存在，set -e 让脚本在信息卡阶段静默退出（exit 254）。
#    注意：exec </dev/null 救不了——它只改脚本自身的 stdin，
#    循环里 ffmpeg 子进程继承的仍是 cards.tsv。
exec </dev/null
cd "$(dirname "$0")/../.."
ROOT="$(pwd)"
EDIT=build-video/edit
OUT=build-video/out
SEG="$EDIT/seg_bili"
TMP=/tmp/iqmol_bili
mkdir -p "$SEG" "$OUT" "$TMP"
FONT=/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc
W=1920; H=1080; VFPS=25
TOTAL=75

# ---------- 从通用版已产出的段 2/4/5 复用 ----------
SRC="$EDIT/seg"
for f in s2 s3 s4 s5; do
  if [ ! -f "$SRC/$f.mp4" ]; then
    echo "!! 缺 $SRC/$f.mp4 —— 请先跑 compose_main.sh 生成通用版各段" >&2
    exit 1
  fi
done


echo "### [1/5] 生成开场素材"
# 1.1 中英菜单特写图（从实拍帧裁菜单条，放大到全屏可读）
ffmpeg -nostdin -y -ss 3 -i "$OUT/hero_viagra_en.mp4" -frames:v 1 "$TMP/men_en.png" 2>/dev/null
ffmpeg -nostdin -y -ss 3 -i "$OUT/hero_viagra.mp4"   -frames:v 1 "$TMP/men_zh.png" 2>/dev/null

python3 - "$TMP" "$EDIT" <<'PY'
import sys
from PIL import Image, ImageDraw, ImageFont
TMP, EDIT = sys.argv[1], sys.argv[2]
F = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
def f(s): return ImageFont.truetype(F, s, index=2)   # index=2 = Noto Sans CJK SC
W, H = 1920, 1080

def bar(tag):
    """裁菜单条（y=3..27）并横向放大 2 倍 —— 原图仅 24px 高，手机端不可读"""
    im = Image.open(f"{TMP}/men_{tag}.png").crop((8, 3, 440, 27))
    return im.resize((im.width * 2, im.height * 2), Image.LANCZOS)

# === A. 闪切图：整屏菜单条 + 大标签 ===
for tag, lab, col in [("en", "原版  English", (214, 72, 58)),
                      ("zh", "中文版", (36, 168, 96))]:
    b = bar(tag)
    img = Image.new("RGB", (W, H), (20, 26, 36))
    d = ImageDraw.Draw(img)
    y = (H - b.height) // 2 + 40
    box = Image.new("RGB", (b.width + 40, b.height + 30), (248, 248, 250))
    box.paste(b, (20, 15))
    img.paste(box, ((W - b.width - 40) // 2, y))
    f2 = f(96); w = d.textbbox((0, 0), lab, font=f2)[2]
    d.text(((W - w) / 2, y - 165), lab, font=f2, fill=col)
    img.save(f"{TMP}/flash_{tag}.png")

# === B. 分屏对照图：左英右中 + VS ===
en, zh = bar("en"), bar("zh")
pw2 = 820
ph2 = int(en.height * pw2 / en.width)
en2, zh2 = en.resize((pw2, ph2), Image.LANCZOS), zh.resize((pw2, ph2), Image.LANCZOS)
img = Image.new("RGB", (W, H), (20, 26, 36))
d = ImageDraw.Draw(img)
py = 440
LX, RX = 90, W - 90 - pw2
for x0 in (LX, RX):
    d.rectangle([x0 - 14, py - 14, x0 + pw2 + 14, py + ph2 + 14], fill=(247, 248, 251))
img.paste(en2, (LX, py)); img.paste(zh2, (RX, py))
f2 = f(50)
d.text((LX, py - 86), "原版 English", font=f2, fill=(214, 72, 58))
d.text((RX, py - 86), "中文版", font=f2, fill=(36, 168, 96))
d.rectangle([W // 2 - 2, py - 24, W // 2 + 2, py + ph2 + 24], fill=(80, 100, 130))
# ⚠️ VS 原字号 88 + y=py+ph2/2-58。PIL 的 text y 是**左上角**（anchor 'la'），
#    88px 字的主体落在 404–492，正好压在两条菜单条(426–484)上，
#    把"中文版"菜单条的左端挡住——这张图的主体就是中文菜单，不能被挡。
#    缩到 56px 并垂直居中于菜单条：宽度约 70px，正好落进
#    左条右缘(910)与右条左缘(1010)之间的 100px 空隙，谁也不挡。
fvs = f(56); w = d.textbbox((0, 0), "VS", font=fvs)[2]
d.text((W // 2 - w / 2, py + ph2 / 2 - 28), "VS", font=fvs, fill=(255, 200, 70))
t = "同一个软件，两个语言"
fo = f(118); w = d.textbbox((0, 0), t, font=fo)[2]
d.text(((W - w) / 2, 140), t, font=fo, fill=(255, 255, 255))
t2 = "IQmol 全界面汉化 · 免费开源"
fo2 = f(66); w = d.textbbox((0, 0), t2, font=fo2)[2]
d.text(((W - w) / 2, 890), t2, font=fo2, fill=(120, 200, 255))
t3 = "菜单 · 对话框 · 按钮 · 提示 · 474 处界面文本"
fo3 = f(46); w = d.textbbox((0, 0), t3, font=fo3)[2]
d.text(((W - w) / 2, 960), t3, font=fo3, fill=(150, 170, 190))
img.save(f"{EDIT}/split_cmp.png")
print("  闪切图 ×2 + 分屏对照图 已生成")
PY

# 1.2 慢速对照：英文 2.2s ⟶ 0.8s 交叉溶解 ⟶ 中文 2.6s
#     （2026-10-02 调整：原为 0.6s 硬切 4 下，转场太突然、闪得太快）
# 各停 2.2s + 0.8s 交叉溶解 —— 英文与中文都留足阅读时间。
# 初版是 1.5s 停留 + 0.7s 溶解，实测英文只露出 0.8s，来不及看清菜单。
ffmpeg -nostdin -y -loop 1 -i "$TMP/flash_en.png" -t 2.2 -r $VFPS -pix_fmt yuv420p \
  -c:v libopenh264 -preset veryfast -crf 23 "$TMP/f_en.mp4" 2>/dev/null
ffmpeg -nostdin -y -loop 1 -i "$TMP/flash_zh.png" -t 2.6 -r $VFPS -pix_fmt yuv420p \
  -c:v libopenh264 -preset veryfast -crf 23 "$TMP/f_zh.mp4" 2>/dev/null
ffmpeg -nostdin -y -i "$TMP/f_en.mp4" -i "$TMP/f_zh.mp4" -filter_complex "\
[0:v][1:v]xfade=transition=fade:duration=0.8:offset=1.4,fps=$VFPS,format=yuv420p[v]" \
  -map "[v]" -c:v libopenh264 -preset veryfast -crf 23 "$TMP/f_flash.mp4" 2>/dev/null

# 1.3 分屏对照 2.6s
ffmpeg -nostdin -y -loop 1 -i "$EDIT/split_cmp.png" -t 2.6 -r $VFPS -pix_fmt yuv420p \
  -c:v libopenh264 -preset veryfast -crf 23 "$TMP/f_split.mp4" 2>/dev/null

# 1.4 收尾：中文界面实拍 3.6s（分子在转）
# 分子实拍本身是亮界面（实测亮度 110），与前面深色卡片（亮度 40）落差过大，
# 直接衔接会闪一下。叠一层 22% 黑膜压到 85 左右，衔接就顺了。
#
# ⚠️ 不要用 eq 滤镜——本机 ffmpeg 构建报 "No such filter: 'eq'"，
#    colorlevels 的 rimin 也几乎无效（110→109）。drawbox 叠黑膜最可靠。
ffmpeg -nostdin -y -ss 10 -t 3.6 -i "$OUT/hero_viagra.mp4" \
  -vf "scale=${W}:${H},setsar=1,fps=$VFPS,\
drawbox=x=0:y=0:w=${W}:h=${H}:color=black@0.22:t=fill,format=yuv420p" \
  -c:v libopenh264 -preset veryfast -crf 23 "$TMP/f_hero.mp4" 2>/dev/null

# ---------- 信息卡（2026-10-02 对标改造新增）----------
#
# 依据 docs/B站对标分析.md 实测：B站同类头部作品画面变化间隔 2.25s、
# 静态帧占比 73–88%；我们原片是 6.25s / 97.8%。
# 头部作品共同做法：纯色底 + 超大粗体字，一个信息点占满一屏。
#
# 这里把信息卡当**独立片段**插在段落之间，用 xfade 溶解衔接。
# 信息卡本身是完全静止的，所以它只是"打断长静止"，
# 真正的密度提升来自卡与录屏之间的画面反差。
echo "### [1b/4] 生成信息卡"
CARDS=/tmp/iqmol_cards
python3 scripts/video/make_info_cards.py "$CARDS" | sed 's/^/  /'

# 把每张静态卡转成对应时长的视频片段
# 每张卡做缓慢推近（Ken Burns），让静止的卡片本身也在动。
#
# 为什么要动：信息卡本质是静态图，卡与卡之间的切换虽然算"变化"，
# 但对标作品实测间隔 0.74–1.92s，而我们的卡各停 2.0–2.2s，
# 加上推近后每帧都有微变化，检测器能计到，实际观感也更像"有节奏"。
#
# 为什么用 z='1+0.0009*on' 而不是 min(zoom+0.0009,...)：
# 后者第一帧的 zoom 来自输入帧缩放值，起步有个爬升期，实测要 1.48s
# 才开始产生帧差。改成直接按输出帧号 on 线性推近，**第1 帧就有位移**，
# 首次画面变化提前到 0.04s，对标作品是 0.48s。
# 2 秒推近约 4.5%，接近段4 标注层（0.0007），不会晕。
mkcard() {  # $1=png  $2=时长  $3=输出名
  ffmpeg -nostdin -y -loop 1 -i "$1" -t "$2" -r $VFPS \
    -vf "scale=${W}:${H}:force_original_aspect_ratio=increase,crop=${W}:${H},\
zoompan=z='1+0.045*on/${FRAMES}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s=${W}x${H}:fps=${VFPS},\
setsar=1,format=yuv420p" \
    -c:v libopenh264 -preset veryfast -crf 22 "$3" 2>/dev/null
}
while IFS=$'\t' read -r png sec; do
  [ -z "$png" ] && continue
  # FRAMES 供 zoompan 的 on 用：让整段推近幅度固定为 4.5%，
  # 不管这张卡是 1.4 秒还是 2.2 秒。
  # ⚠️ printf "%d" 收到 "40.0" 这类小数会报 "invalid number"，
  #    必须先用 bc 取整（scale=0 向下取整）。
  FRAMES=$(echo "$sec * $VFPS" | bc -l | cut -d. -f1)
  mkcard "$png" "$sec" "$TMP/$(basename "$png" .png).mp4"
done < "$CARDS/cards.tsv"

# ---------- 通用链式 xfade ----------
# 三段之间统一用 xfade 溶解，避免 concat 硬切造成亮度断层。
# 上一版实测：concat 拼接处亮度从 16 跳到 89，肉眼可见闪一下。
#
# ⚠️ offset 必须按**实测时长**算，不能硬编码。
#    xfade 会吃掉 duration 秒：结果时长 = A + B - D。
#    硬编码曾导致 OFF2 超出范围，开场从 8s缩到 5.9s，分子实拍整段丢失。
#用 bc 算浮点；shell 的 $(( )) 只支持整数，2*D 会被截断导致 offset 偏小
D=0.5
dur() { ffprobe -v error -show_entries format=duration -of csv=p=0 "$1"; }

# chain <out> <输入1> <输入2> ... —— 逐段 0.5s 溶解，自动按实测时长算 offset
chain() {
  local out="$1"; shift
  local n=$#; local i
  local -a ins=("$@")
  local -a fc=()
  local acc=0
  # ⚠️ 首段输入标签必须带方括号：写成裸 "0:v" 会被解析成 filterchain 开头的垃圾字符，
  #    报 "Trailing garbage after a filter"。首段必须显式写 [0:v]。
  local prev="[0:v]"
  # acc 是"已累积画面的总长"，必须从**第一段实际时长**起算，
  # 不能从 0 开始。xfade 的 offset 是过渡在累积时间轴上的起点，
  # 所以 offset = acc - D（让过渡正好落在已累积内容的末尾）。
  #
  # ⚠️ offset 必须小于前段时长，否则报
  #    "Error applying option 'offset' to filter 'xfade': Invalid argument"。
  #    每轮 acc = acc + 本段时长 - D。
  acc=$(dur "${ins[0]}")
  for ((i = 1; i < n; i++)); do
    local di; di=$(dur "${ins[$i]}")
    local off; off=$(echo "$acc - $D" | bc -l)
    # 前一段必须至少留出 D 秒给过渡，否则 xfade 拒绝执行
    if [ "$(echo "$off < 0" | bc -l)" -eq 1 ]; then
      echo "    !! ${ins[$i-1]} 太短（$(printf %.2f "$acc")s），容不下 ${D}s 过渡" >&2
      return 1
    fi
    local lbl="[vx$i]"
    fc+=("${prev}[${i}:v]xfade=transition=fade:duration=${D}:offset=${off}${lbl}")
    prev="$lbl"
    acc=$(echo "$acc + $di - $D" | bc -l)
    printf "    溶解 %s → %s  offset=%.2f  累计=%.2fs\n" \
      "$(basename "${ins[$i-1]}")" "$(basename "${ins[$i]}")" "$off" "$acc"
  done
  # ⚠️ 这里必须补分号：${prev} 展开成 "[vx4]"，后面直接跟 fps 会拼成
  #    "[vx4][vx4]fps=25" —— 标签重复，滤镜图绑定失败，ffmpeg 静默退出。
  local fcs; fcs=$(IFS=';'; echo "${fc[*]}")
  ffmpeg -nostdin -y $(printf -- "-i %s " "${ins[@]}") \
    -filter_complex "${fcs};${prev}fps=${VFPS},format=yuv420p[vo]" \
    -map "[vo]" -c:v libopenh264 -preset veryfast -crf 23 "$out"
  local rc=$?
  if [ $rc -ne 0 ]; then echo "    !! chain 失败 rc=$rc"; return 1; fi
}

# 开场链路：hook1(规模) → hook2 → term(专业度) → 中英菜单 → 分屏 → 分子实拍
#
# 改造重点：原开场是"英文菜单静帧 3.96s 后才有第一次画面变化"，
# 对标作品首次变化在 0.48s。现在第 0.5 秒就出 hook1 大字卡。
# 2026-10-03 新增 term 卡：前 10 秒把"汉化规模 + 术语专业度"一次讲透，
# 突出汉化重点（区别于机翻）。
echo "### [2/4] 开场：hook 卡 + 汉化专业度卡 + 中英对照 + 分子实拍"
chain "$SEG/s1.mp4" \
  "$TMP/card_hook1.mp4" \
  "$TMP/card_hook2.mp4" \
  "$TMP/card_term.mp4" \
  "$TMP/f_flash.mp4" \
  "$TMP/f_split.mp4" \
  "$TMP/f_hero.mp4"
d=$(dur "$SEG/s1.mp4")
printf "    s1   %s 秒（含2 张 hook 卡）\n" "${d%.*}"
echo "### [3/4] 复用通用版段 2/3/5，段4 换动态标注版"
cp "$SRC/s5.mp4" "$SEG/s5.mp4"

# 段2 = 痛点提问卡 + 原段2 内容
# 痛点卡插在前面，因为原段2 开头就是 8 秒连续录屏，是全片最长的静止块之一。
# 对标 C「分屏读顶刊」正是靠"《Science》为什么只有几页？"这类提问开场留人。
chain "$SEG/s2.mp4" "$TMP/card_pain1.mp4" "$TMP/card_pain2.mp4" "$SRC/s2.mp4"
printf "    s2   %s 秒（含2 张痛点卡）\n" "$(dur "$SEG/s2.mp4" | cut -d. -f1)"

# 段3 转折：英→中改为 0.5s 交叉溶解（原来是 concat 硬切）。
# 转折点仍保留"突然换成中文"的力度，但不再是生硬的信号切换感。
# 素材：shot_3_en.mp4 1.5s 英文 + shot_3_zh.mp4 循环补足
ffmpeg -nostdin -y -i "$OUT/shot_3_en.mp4" -t 2.0 \
  -vf "scale=${W}:${H},setsar=1,fps=$VFPS,fade=t=out:st=1.5:d=0.5,format=yuv420p" \
  -c:v libopenh264 -preset veryfast -crf 24 "$TMP/s3en.mp4" 2>/dev/null
ffmpeg -nostdin -y -i "$OUT/shot_3_zh.mp4" -t 8.5 \
  -vf "loop=loop=-1:size=32767:start=0,scale=${W}:${H},setsar=1,fps=$VFPS,\
fade=t=in:st=0:d=0.5,format=yuv420p" \
  -c:v libopenh264 -preset veryfast -crf 24 "$TMP/s3zh.mp4" 2>/dev/null
ffmpeg -nostdin -y -i "$TMP/s3en.mp4" -i "$TMP/s3zh.mp4" -filter_complex "\
[0:v][1:v]xfade=transition=fade:duration=0.5:offset=1.5,fps=$VFPS,format=yuv420p[v]" \
  -map "[v]" -c:v libopenh264 -preset veryfast -crf 24 "$TMP/s3_raw.mp4" 2>/dev/null
printf "IQmol 中文版 · 全界面汉化" > "$TMP/s3big.txt"
ffmpeg -nostdin -y -i "$TMP/s3_raw.mp4" -t 10 \
  -vf "drawbox=x=0:y=0:w=${W}:h=${H}:color=black@0.30:t=fill,\
drawtext=fontfile=${FONT}:textfile=${TMP}/s3big.txt:fontcolor=white:fontsize=62:\
x=(w-text_w)/2:y=800:enable='between(t,0.6,9.4)',format=yuv420p" \
  -r $VFPS -c:v libopenh264 -preset veryfast -crf 23 "$SEG/s3.mp4" 2>/dev/null

# 段4 = 功能卡 + 三组标注层(8s×3) + 数据条卡(4s)
# gain1 卡放在段4 前：三段标注录屏各 8 秒，中间必须有东西打断，
# 否则"建模/计算/可视化"三屏连着看，观众会滑走。
ANNOT=/tmp/iqmol_annot
for s in a b c; do
  [ -f "$ANNOT/${s}_annot.mp4" ] || { echo "!! 缺 ${s}_annot.mp4，请先跑 annotate_segment4.sh" >&2; exit 1; }
done
printf "file '%s'\n" "$TMP/card_gain1.mp4" \
              "$ANNOT/a_annot.mp4" "$ANNOT/b_annot.mp4" "$ANNOT/c_annot.mp4" \
              "$ROOT/$SRC/s4d_l.mp4" > "$TMP/s4.txt"
ffmpeg -nostdin -y -f concat -safe 0 -i "$TMP/s4.txt" -c copy "$SEG/s4.mp4" 2>/dev/null
printf "    s4   %s秒（功能卡 + 动态标注版）\n" "$(dur "$SEG/s4.mp4" | cut -d. -f1)"

# 段5 = 结尾引导卡 + 原收尾卡
# 原收尾卡是二维码 + 三连，属标准做法、无短板（对标 A/B/C 都有类似收尾）。
# 但前面需要一张卡承接，否则从段4 数据条卡直接切到收尾卡会显得突兀。
printf "file '%s'\n" "$TMP/card_end1.mp4" "$ROOT/$SRC/s5.mp4" > "$TMP/s5.txt"
ffmpeg -nostdin -y -f concat -safe 0 -i "$TMP/s5.txt" -c copy "$SEG/s5.mp4" 2>/dev/null
printf "    s5   %s 秒（含结尾引导卡）\n" "$(dur "$SEG/s5.mp4" | cut -d. -f1)"

# ---------- 先量出真实总长，再生成等长 BGM ----------
#
# ⚠️ 旧版 TOTAL 写死 75，而各段合计实测 75.72s，
#    concat 后 -shortest 会静默裁掉收尾卡末尾约 0.7s。
#    这里改成"先量视频，再按视频长度配 BGM"，从根上避免裁切。
echo "### [4/4] BGM + 总拼接"
printf "file '%s'\n" "$ROOT/$SEG/s1.mp4" "$ROOT/$SEG/s2.mp4" "$ROOT/$SEG/s3.mp4" \
                  "$ROOT/$SEG/s4.mp4" "$ROOT/$SEG/s5.mp4" > "$TMP/all.txt"
ffmpeg -nostdin -y -f concat -safe 0 -i "$TMP/all.txt" -c copy "$TMP/v.mp4" 2>/dev/null
VT=$(dur "$TMP/v.mp4")
echo "    视频实际总长 ${VT} 秒（BGM 将按此长度生成）"
TOTAL=$(printf "%.0f" "$VT")

ffmpeg -nostdin -y \
  -f lavfi -i "sine=frequency=261.63:duration=${TOTAL}:sample_rate=44100" \
  -f lavfi -i "sine=frequency=392.00:duration=${TOTAL}:sample_rate=44100" \
  -f lavfi -i "sine=frequency=220.00:duration=${TOTAL}:sample_rate=44100" \
  -filter_complex "[0:a]volume=0.16[a0];[1:a]volume=0.10[a1];[2:a]volume=0.12[a2];\
[a0][a1][a2]amix=inputs=3:duration=longest,\
afade=t=in:st=0:d=2,afade=t=out:st=$(echo "$TOTAL - 3" | bc -l):d=3,\
alimiter=limit=0.85,loudnorm=I=-18:TP=-1.5[a]" \
  -map "[a]" -t $TOTAL -c:a aac -b:a 160k "$TMP/bgm.m4a" 2>/dev/null

# 最终音频：默认只混 BGM；若旁白轨已生成（scripts/video/narration.py），
# 则把 BGM 压到 0.30 给旁白让位（ducking），旁白 1.0，两者 amix。
# 视频流决定最终长度，-t "$VT" 把音频裁剪到视频时长，避免旁白轨(92s)拖长成片。
NARR="/tmp/iqmol_narr/vn.m4a"
if [ -f "$NARR" ]; then
  echo "    混入旁白轨（BGM 压至 0.30 让位）"
  ffmpeg -nostdin -y -i "$TMP/v.mp4" -i "$TMP/bgm.m4a" -i "$NARR" \
    -filter_complex "[1:a]volume=0.30[b];[2:a]volume=1.0[vn];[b][vn]amix=inputs=2:normalize=0[a]" \
    -map 0:v -map "[a]" -t "$VT" -c:v copy -c:a aac -b:a 160k -movflags +faststart \
    "$OUT/iqmol_promo_bili.mp4" 2>/dev/null
else
  ffmpeg -nostdin -y -i "$TMP/v.mp4" -i "$TMP/bgm.m4a" \
    -map 0:v -map 1:a -c:v copy -c:a aac -b:a 160k -movflags +faststart \
    "$OUT/iqmol_promo_bili.mp4" 2>/dev/null
fi

echo "### [5/5] 成片校验"
ffprobe -v error -select_streams v:0 -show_entries stream=codec_name,width,height,r_frame_rate,nb_frames \
  -show_entries format=duration,size -of default=nw=1 "$OUT/iqmol_promo_bili.mp4"

# ---------- 对标指标自检 ----------
# 与 docs/B站对标分析.md 的实测方法一致：降采样到 160×90 灰度，
# 逐帧相邻差 >8 记一次画面变化，0.4s 内合并。
echo "--- 对标自检（对标基准：间隔 2.25s / 静态帧 73–88%） ---"
python3 scripts/video/shot_density.py "$OUT/iqmol_promo_bili.mp4" \
  | sed 's/^/  /'
echo "输出：$OUT/iqmol_promo_bili.mp4"
