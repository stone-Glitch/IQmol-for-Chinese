#! /bin/bash
# ----------------------------------------------------------------------------
# 更新翻译文件并生成 qm（lupdate + 防退化 + lrelease 一体化）
#
# 背景: lupdate 受 GLObject.h 解析错误影响, 无法解析部分源文件 (如 MainWindow.C)
# 中的 tr() 调用, 每次运行都会把这些字符串的既有翻译误标为 type="vanished",
# 导致 lrelease 跳过它们 (菜单/界面退回英文)。本脚本在 lupdate 后自动移除
# vanished 标记, 保证既有翻译始终生效。
#
# 用法:
#   ./scripts/update_translations.sh          # lupdate + 修复 + lrelease
#   ./scripts/update_translations.sh --sync   # 额外同步 qm 到 build 目录
# ----------------------------------------------------------------------------
set -e

TOPDIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )/.." &> /dev/null && pwd )
TS=$TOPDIR/translations/zh_CN.ts
SYNC=0
[ "$1" = "--sync" ] && SYNC=1

command -v lupdate >/dev/null 2>&1 || { echo "错误: 未找到 lupdate"; exit 1; }
command -v lrelease >/dev/null 2>&1 || { echo "错误: 未找到 lrelease"; exit 1; }

echo "==> lupdate 扫描源码"
lupdate "$TOPDIR/src/" -ts "$TS" 2>&1 | grep -E "Found|Kept" || true

echo "==> 移除误标的 vanished 标记 (防退化)"
python3 - "$TS" <<'PY'
import sys, re
p = sys.argv[1]
s = open(p, encoding='utf-8').read()
n = s.count('type="vanished"')
if n:
    s = s.replace('<translation type="vanished">', '<translation>')
    open(p, 'w', encoding='utf-8').write(s)
print(f'    恢复 {n} 条被误标的翻译')
PY

echo "==> lrelease 生成 qm"
lrelease "$TS" -qm "$TOPDIR/translations/zh_CN.qm" 2>&1 | tail -1

if [ "$SYNC" = "1" ]; then
   for d in "$TOPDIR/build/translations" "$TOPDIR/build/bin/translations"; do
      [ -d "$d" ] && cp "$TOPDIR/translations/zh_CN.qm" "$d/" && echo "    已同步: $d"
   done
fi

echo "==> 完成: $TS"
