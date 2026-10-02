#!/usr/bin/env bash
# ============================================================================
# setup_virtual_display.sh —— 一行装好「无显卡录屏环境」
#
# 做三件事：
#   1. 校验依赖（Xvfb / openbox / xdotool / imagemagick / ffmpeg / Qt5 / OpenBabel）
#   2. 生成 zh_CN.UTF-8 locale（否则 Qt 拿不到中文 locale，可能回退英文界面）
#   3. 打印「常驻启动 Xvfb 与 openbox」的命令（需由调用方放进独立后台任务）
#
# 注意：本脚本**不**在内部常驻 Xvfb/openbox——普通 `&` 起的后台进程
#       会随调用方会话被回收，导致后续步骤连不上显示。必须由外部以
#       独立后台任务方式常驻。
# ============================================================================
set -uo pipefail

GEOM="${GEOM:-1920x1080}"
DISPLAY_NUM="${DISPLAY_NUM:-:99}"
OK=0; MISS=0

echo "=== 1/3 检查依赖 ==="
for t in Xvfb openbox xdotool import ffmpeg glxinfo; do
  if command -v "$t" >/dev/null; then
    printf "  ✓ %-10s %s\n" "$t" "$(command -v "$t")"; OK=$((OK+1))
  else
    printf "  ✗ %-10s 缺失\n" "$t"; MISS=$((MISS+1))
    case "$t" in
      Xvfb)        echo "      → sudo apt-get install -y xvfb" ;;
      openbox)     echo "      → sudo apt-get install -y openbox" ;;
      xdotool)     echo "      → sudo apt-get install -y xdotool" ;;
      import)      echo "      → sudo apt-get install -y imagemagick" ;;
      ffmpeg)      echo "      → sudo apt-get install -y ffmpeg" ;;
      glxinfo)     echo "      → sudo apt-get install -y mesa-utils" ;;
    esac
  fi
done

echo
echo "=== 2/3 检查 Qt5 / OpenBabel / 渲染库 ==="
pkg-config --exists Qt5Widgets && echo "  ✓ Qt5Widgets $(pkg-config --modversion Qt5Widgets)" || { echo "  ✗ Qt5Widgets 缺失 → sudo apt-get install -y qtbase5-dev"; MISS=$((MISS+1)); }
pkg-config --exists openbabel-3 && echo "  ✓ OpenBabel $(pkg-config --modversion openbabel-3)" \
  || { echo "  ✗ OpenBabel-3 缺失 → sudo apt-get install -y libopenbabel-dev"; MISS=$((MISS+1)); }
ls /usr/lib/x86_64-linux-gnu/dri/*swrast* /usr/lib/x86_64-linux-gnu/dri/*llvmpipe* >/dev/null 2>&1 \
  && echo "  ✓ llvmpipe/swrast 软件渲染 DRI 就位" \
  || echo "  ! 未找到 swrast/llvmpipe DRI（通常随 mesa 一起装，先试试能否跑 glxinfo）"

echo
echo "=== 3/3 生成 zh_CN.UTF-8 locale ==="
if locale -a 2>/dev/null | grep -qiE '^zh_CN\.(utf8|UTF-8)$'; then
  echo "  ✓ 已存在"
else
  sed -i 's/^# *zh_CN\.UTF-8 UTF-8/zh_CN.UTF-8 UTF-8/' /etc/locale.gen 2>/dev/null
  locale-gen zh_CN.UTF-8 >/dev/null 2>&1 && echo "  ✓ 已生成" || echo "  ✗ 生成失败（中文界面可能回退英文）"
fi
LC_ALL=zh_CN.UTF-8 date 2>/dev/null | grep -q 年 && echo "  ✓ 验证通过：$(LC_ALL=zh_CN.UTF-8 date)" || echo "  ! 验证失败"

cat <<EOF

────────────────────────────────────────────────────────────
依赖检查：$OK 项就绪，$MISS 项缺失

下一步（两条命令各需在**独立后台任务**中常驻，不要用普通 &）：

  exec Xvfb $DISPLAY_NUM -screen 0 ${GEOM}x24 -nolisten tcp

  DISPLAY=$DISPLAY_NUM openbox --sm-disable

就绪后执行录屏：

  bash scripts/video/record_virtual_display.sh <分子文件> <输出.mp4> [时长秒]

验证中文已生效（权威标志，勿靠肉眼）：

  grep 'Loaded translation' build-video/out/logs/iqmol.log
  # 期望： [i18n] Loaded translation: "zh_CN"
────────────────────────────────────────────────────────────
EOF
