#!/bin/bash
# ============================================================
# IQmol 中文版推广视频 · 动态标注层
#
#  解决的问题：段4 三组录屏合计 24s 全是静态画面（实测静帧率 71%），
#  B站完播率被拖低。素材本身无需重录，改为叠加动态元素制造运动：
#    ① 局部放大特写 —— crop + Ken Burns 缓慢推近关键控件
#    ② 高亮描边     —— 框住界面关键区域
#    ③ 说明字幕     —— 讲什么标什么，与画面同步
#
#  ⚠️ 两个必须遵守的坑（2026-10-02 实测踩到）：
#    ① drawtext 的 fontfile/textfile 路径**必须用 ${VAR} 大括号**。
#      写成 $FONT:xxx 时 shell 会把后续字符当变量名吞掉，fontfile 变空串，
#       ffmpeg 报 "Either text, a valid file... must be provided"。
#    ② 同一输入 [0:v] 不能被 split 后只消费一路，另一路会因悬空输出导致
#       "Error binding filtergraph inputs/outputs"。放大+高亮改为两遍处理。
# ============================================================
set -eu
# ⚠️ 所有 ffmpeg 调用都必须带 -nostdin。下面`while read ... done < clicks文件`
#    循环之后紧跟 ffmpeg overlay，子进程继承列表文件作 stdin会推进文件偏移。
exec </dev/null
cd "$(dirname "$0")/../.."
OUT=build-video/out
TMP=/tmp/iqmol_annot
mkdir -p "$TMP"
FONT=/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc
VFPS=25
RIPPLE=${TMP}/ripple.mov

# annot <in> <out> <时长> <裁剪区域x,y,w,h> <字幕> [点击记录文件]
#
# 点击记录格式（rec_segment4.sh 产出）：每行 "时刻 点击x 点击y"，
# x/y 为录制时 1920x1080 屏幕绝对坐标。每个点击在对应时刻叠加一个
# 0.8s 橙色扩散波纹（ripple.mov，RGBA，中心 960,540）。
#
# 波纹落点换算（三重）：
#   ① 裁剪区偏移：屏幕坐标 → 裁剪后坐标，(x-cx, y-cy)
#   ② 裁剪区缩放：pass1 把 cw×ch 拉伸到 1920×1080，×(1920/cw, 1080/ch)
#   ③ zoompan 推近：z='min(zoom+0.0007,1.16)' 每帧 +0.0007，25fps
#      → z(t) = min(1+0.0175·t, 1.16)，居中放大 → 点在画面上
#      以 (960,540) 为中心向外漂：X(t) = 960 + (PX-960)·z(t)
#      overlay 位置 = 目标中心 - 波纹自身中心 = ((PX-960)·z(t), (PY-540)·z(t))
annot() {
  local in=$1 out=$2 dur=$3 crop=$4 txt=$5 clicks=${6:-}
  local cx=${crop%%,*}; local rest=${crop#*,}
  local cy=${rest%%,*}; rest=${rest#*,}
  local cw=${rest%%,*}; local ch=${rest#*,}

  printf '%s' "$txt" > "${TMP}/txt.txt"

  # ---- pass 1：裁剪 + Ken Burns 推近（制造持续运动）----
  ffmpeg -nostdin -y -i "$in" -t "$dur" \
    -vf "crop=${cw}:${ch}:${cx}:${cy},scale=1920:1080:flags=bicubic,\
zoompan=z='min(zoom+0.0007,1.16)':d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1920x1080:fps=${VFPS},\
format=yuv420p" \
    -c:v libopenh264 -preset veryfast -crf 22 "${TMP}/p1.mp4" 2>/dev/null

  # ---- 收集落在裁剪区内的有效点击 ----
  # ⚠️ 先过滤再 split：split 出的每一路都必须被消费，否则复现
  #    "Error binding filtergraph inputs/outputs"（本脚本头部的坑②）
  local pts=()
  if [ -n "$clicks" ] && [ -s "$clicks" ]; then
    local t x y
    while read -r t x y; do
      if (( x >= cx && x < cx+cw && y >= cy && y < cy+ch )); then
        pts+=("$t $x $y")
      else
        echo "    [i] 点击 ($x,$y) 在裁剪区外，不叠波纹"
      fi
    done < "$clicks"
  fi

  local base="drawbox=x=40:y=40:w=1840:h=1000:color=white@0.55:t=3,\
drawtext=fontfile=${FONT}:textfile=${TMP}/txt.txt:fontcolor=white:fontsize=72:\
box=1:boxcolor=0x101820@0.82:boxborderw=26:x=(w-text_w)/2:y=h-230"

  local n=${#pts[@]}
  if (( n == 0 )); then
    # ---- pass 2（无波纹）：高亮框 + 字幕 ----
    ffmpeg -nostdin -y -i "${TMP}/p1.mp4" -t "$dur" \
      -vf "${base},format=yuv420p" \
      -r $VFPS -c:v libopenh264 -preset veryfast -crf 22 "$out" 2>/dev/null
  else
    # ---- pass 2（带波纹）：高亮框 + 字幕 + 逐点击 overlay ----
    # ⚠️ 波纹只有 0.8s，必须把它的时间轴**平移**到点击时刻，不能靠 enable 开窗：
    #    overlay 取的是第二输入自身的 PTS，3.6s 时 ripple 早已 EOF，
    #    默认 eof_action=repeat 就一直重复最后一帧（透明度接近 0），
    #    实测差异只有 81 像素——等于没叠。用 setpts 平移 + eof_action=pass。
    local k t x y px py
    local fc="[0:v]${base}[base];[1:v]split=${n}"
    for k in $(seq 1 "$n"); do fc="${fc}[s${k}]"; done
    fc="${fc};"
    k=1
    for p in "${pts[@]}"; do
      read -r t x y <<< "$p"
      fc="${fc}[s${k}]setpts=PTS+${t}/TB[r${k}];"
      k=$((k+1))
    done
    local prev="[base]"
    k=1
    for p in "${pts[@]}"; do
      read -r t x y <<< "$p"
      px=$(python3 -c "print(f'{($x-$cx)*1920/$cw:.1f}')")
      py=$(python3 -c "print(f'{($y-$cy)*1080/$ch:.1f}')")
      # 落点再做边界限制：点菜单栏这类贴边点击，换算后波纹中心会跑到
      # 画面外（4b 首个点击中心 y≈13，圆环大半被裁掉）。
      # 约束波纹中心距边缘至少 60px：overlay 左上角 x∈[-900,900]、y∈[-480,480]
      fc="${fc}${prev}[r${k}]overlay=\
x='max(-900\,min((${px}-960)*min(1+0.0175*t\,1.16)\,900))':\
y='max(-480\,min((${py}-540)*min(1+0.0175*t\,1.16)\,480))':\
eof_action=pass[o${k}];"
      prev="[o${k}]"
      k=$((k+1))
    done
    fc="${fc}${prev}format=yuv420p[vout]"
    ffmpeg -nostdin -y -i "${TMP}/p1.mp4" -i "$RIPPLE" -filter_complex "$fc" \
      -map "[vout]" -t "$dur" \
      -r $VFPS -c:v libopenh264 -preset veryfast -crf 22 "$out" 2>/dev/null
  fi

  [ -f "$out" ] || { echo "!! 生成失败：$out" >&2; exit 1; }
}

echo "### 动态标注层（段4 三组）"
# 素材换成重录版（真实鼠标操作 + 缓动），点击记录由 rec_segment4.sh 产出
REC=/tmp/iqmol_rec

# 4a 建模：元素周期表 + 菜单栏（面板实测 x 0–517 / y 0–294）
# ⚠️ 裁剪区必须框住"动作发生的地方"，不是界面图标。
#    第一版裁 8,8,200,130 只框到静态工具栏小角，放大 10 倍后全程无鼠标操作，
#    观众看到的是一张 8 秒不动的图。
annot "$OUT/clip_4a_new.mp4" "${TMP}/a_annot.mp4" 8 \
  "0,0,640,360" "建模：元素周期表 + 原子 / 键模板" "$REC/clicks_a.txt"

# 4b 计算：计算菜单展开 → Q-Chem 设置对话框弹出（面板实测 x 0–951 / y 0–679）
annot "$OUT/clip_4b_new.mp4" "${TMP}/b_annot.mp4" 8 \
  "0,0,1313,739" "计算：Q-Chem 参数一键设置" "$REC/clicks_b.txt"

# 4c 可视化：拖拽旋转 + 滚轮缩放（分子实测在 x 782–1477 / y 409–765）
#    第三版换方案：不再拍"配置分子"对话框——那个对话框一打开画布就永久清空
#    （三个驱动实测一致），拍出来是"点了样式分子没反应"。
#    裁剪区框住分子所在区域，让旋转/缩放的真实变化占满画面。
#    时长 12s（不是 8s）：录制时 xdotool 被 ffmpeg 拖慢约 1.5 倍，
#    8 秒素材会截掉末尾两次滚轮。
annot "$OUT/clip_4c_new.mp4" "${TMP}/c_annot.mp4" 12 \
  "620,120,1120,700" "可视化：实时旋转缩放，渲染流畅" "$REC/clicks_c.txt"

echo
for f in a_annot b_annot c_annot; do
  d=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "${TMP}/${f}.mp4")
  printf "    %-10s %ss\n" "$f" "${d%.*}"
done
echo "输出：${TMP}/{a,b,c}_annot.mp4"
