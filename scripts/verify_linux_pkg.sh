#!/usr/bin/env bash
#
# IQmol Linux 分发包 端到端自检脚本
# ------------------------------------------------------------------
# 作用：验证「解压出来的包」是否真的能用——重点是 reA22A 的两个坑：
#   ① 从任意目录启动都能加载中文翻译（旧包只有从包根启动才成功）
#   ② OpenBabel 数据与插件指向包内，不依赖用户机器装没装 OpenBabel
#
# 用法（复制即可运行）：
#   bash scripts/verify_linux_pkg.sh                        # 验默认 dist/IQmol-linux-x86_64
#   bash scripts/verify_linux_pkg.sh /opt/IQmol-linux-x86_64 # 验指定包目录
#   bash scripts/verify_linux_pkg.sh --quick                 # 只做结构+翻译检查（快）
#
# 退出码：0 全部通过；1 存在 FAIL
#
# 说明：不需要显示器。程序以 QT_QPA_PLATFORM=offscreen 启动，
#       只取启动日志即退出，单次约 2~5 秒。
# ------------------------------------------------------------------
set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC_DIR="$(dirname "$SCRIPT_DIR")"

PKG=""
QUICK=0
while [ $# -gt 0 ]; do
  case "$1" in
    --quick) QUICK=1; shift ;;
    *)       PKG="$1"; shift ;;
  esac
done
[ -z "$PKG" ] && PKG="$SRC_DIR/dist/IQmol-linux-x86_64"

PASS=0; FAIL=0
ok()   { printf "  \033[32mPASS\033[0m  %s\n" "$1"; PASS=$((PASS+1)); }
bad()  { printf "  \033[31mFAIL\033[0m  %s\n" "$1"; FAIL=$((FAIL+1)); }
info() { printf "  \033[36mINFO\033[0m  %s\n" "$1"; }

echo "=========================================================="
echo " IQmol Linux 分发包自检"
echo " 包目录: $PKG"
echo " 模式  : $([ "$QUICK" = 1 ] && echo 快速（跳过分子加载） || echo 完整)"
echo "=========================================================="

#------------------------------------------------------------------
# 1. 结构自检
#------------------------------------------------------------------
echo
echo "[1/4] 结构自检"
[ -x "$PKG/bin/IQmol" ] && ok "bin/IQmol 存在且可执行" || bad "缺少 bin/IQmol"
[ -f "$PKG/translations/zh_CN.qm" ] && ok "包根 translations/zh_CN.qm 存在" \
  || bad "缺少包根 translations/zh_CN.qm（reA22A 双保险之一）"
[ -f "$PKG/bin/translations/zh_CN.qm" ] && ok "bin/translations/zh_CN.qm 存在" \
  || bad "缺少 bin/translations/zh_CN.qm（与 applicationDirPath 对齐的那份）"
[ -f "$PKG/run.sh" ] && ok "run.sh 存在" || bad "缺少 run.sh"
[ -d "$PKG/share/openbabel" ] && ok "share/openbabel 数据随包" \
  || bad "缺少 share/openbabel（力场/元素数据，用户机器未装 OpenBabel 时会失效）"
[ -d "$PKG/lib/openbabel" ] && ok "lib/openbabel 运行期插件随包" \
  || bad "缺少 lib/openbabel（格式/力场插件）"

#------------------------------------------------------------------
# 2. 翻译加载：换 6 个工作目录启动
#------------------------------------------------------------------
echo
echo "[2/4] 翻译加载（换工作目录启动，reA22A 回归测试）"
TMPD="$(mktemp -d)"
trap 'rm -rf "$TMPD"' EXIT
mkdir -p "$TMPD/other"

probe() {  # $1 = 启动目录
  ( cd "$1" 2>/dev/null || exit 1
    timeout 10 env QT_QPA_PLATFORM=offscreen "$PKG/bin/IQmol" zh_CN 2>&1 \
      | grep -oE "Loaded translation|No translation file found" | head -1 )
}

for d in / /tmp /root "$TMPD/other" "$PKG" "$PKG/bin"; do
  [ -d "$d" ] || continue
  r="$(probe "$d")"
  case "$r" in
    "Loaded translation") ok "cwd=$d → 中文加载成功" ;;
    "No translation file found") bad "cwd=$d → 未找到翻译文件" ;;
    *) bad "cwd=$d → 无输出（程序未启动？依赖缺失？）" ;;
  esac
done

#------------------------------------------------------------------
# 3. BABEL 路径指向包内
#------------------------------------------------------------------
echo
echo "[3/4] OpenBabel 路径（应指向包内，而非 /usr）"
LOG="$(mktemp)"
( cd "$TMPD" && timeout 10 env QT_QPA_PLATFORM=offscreen "$PKG/bin/IQmol" zh_CN >"$LOG" 2>&1 )
BL="$(grep -oE 'BABEL_LIBDIR = .*|BABEL_LIBDIR already set: .*' "$LOG" | head -1)"
BD="$(grep -oE 'BABEL_DATADIR = .*|BABEL_DATADIR already set: .*' "$LOG" | head -1)"
rm -f "$LOG"
case "$BL" in
  *"$PKG"*) ok "BABEL_LIBDIR → 包内：${BL#*: }" ;;
  "")       bad "日志中没有 BABEL_LIBDIR（程序未走到 initOpenBabel）" ;;
  *)        bad "BABEL_LIBDIR 仍指向系统路径：${BL#*: }" ;;
esac
case "$BD" in
  *"$PKG"*) ok "BABEL_DATADIR → 包内：${BD#*: }" ;;
  "")       bad "日志中没有 BABEL_DATADIR" ;;
  *)        bad "BABEL_DATADIR 仍指向系统路径：${BD#*: }" ;;
esac

#------------------------------------------------------------------
# 4. 打开示例分子（力场可用性）
#------------------------------------------------------------------
echo
echo "[4/4] 打开示例分子（力场可用性）"
if [ "$QUICK" = 1 ]; then
  info "已跳过（--quick）"
else
  # 用内置水分子而不是 samples/ 里的蛋白：offscreen 下大蛋白（3nir 等）
  # 在 10 余秒内跑不完力场计算，会误报失败；水分子必然触发且秒级完成。
  SAMPLE="$TMPD/water.xyz"
  printf '3\nwater\nO   0.0000  0.0000  0.1173\nH   0.0000  0.7572 -0.4692\nH   0.0000 -0.7572 -0.4692\n' > "$SAMPLE"
  LOG2="$(mktemp)"
  ( cd "$TMPD" && timeout 15 env QT_QPA_PLATFORM=offscreen "$PKG/bin/IQmol" zh_CN "$SAMPLE" >"$LOG2" 2>&1 )
  if grep -q "Computing energy with forcefield" "$LOG2"; then
    ok "水分子加载成功，力场计算正常（$(grep -oE 'forcefield "[^"]+"' "$LOG2" | head -1)）"
  else
    bad "未触发力场计算（OpenBabel 数据/插件可能失效），日志尾部："
    tail -5 "$LOG2" | sed 's/^/         /'
  fi
  rm -f "$LOG2"
  # 顺带确认包内示例分子存在（不逐一打开，只查有无）
  if ls "$PKG"/samples/* >/dev/null 2>&1; then
    ok "包内示例分子 $(ls "$PKG"/samples/* 2>/dev/null | wc -l) 项就位"
  else
    info "包内没有 samples/（不影响使用，仅少示例文件）"
  fi
fi

#------------------------------------------------------------------
# 汇总
#------------------------------------------------------------------
echo
echo "=========================================================="
echo " 通过 $PASS 项，失败 $FAIL 项"
if [ "$FAIL" = 0 ]; then
  echo " 结论：该分发包可交付"
else
  echo " 结论：存在问题，按上面 FAIL 项排查；"
  echo "       若未打包请先跑 scripts/package_linux.sh"
fi
echo "=========================================================="
[ "$FAIL" = 0 ] || exit 1
