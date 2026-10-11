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
# 注意 -extensions C,ui 必须放在目录参数之前:
# IQmol 全部源文件用大写 .C 后缀, lupdate 默认扩展名列表不含 .C, 会导致 292 个源文件 tr() 零提取
lupdate -extensions C,ui "$TOPDIR/src/" -ts "$TS" 2>&1 | grep -E "Found|Kept" || true

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

echo "==> lrelease 生成 qm（严格模式：不含未完成条目）"
# -nounfinished: 不把 unfinished 条目编进 qm，与 CI i18n-tqa.yml 的 ts_unfinished_max=0 口径一致。
# 注：刻意**不加 -removeidentical** —— 它会把「译文与原文相同」的条目（如保留西文原名的
#     Gasteiger/Mulliken、单位符号 ppm 等）从 qm 中剔除，虽能减小体积，但会让
#     「已翻译条数」统计口径从 2125 → 1766，与仓库文档反复引用的 2125 条冲突，得不偿失。
#     界面显示不受影响（miss 时 Qt 自动回退原文），故保持 2125 口径。
lrelease -nounfinished "$TS" -qm "$TOPDIR/translations/zh_CN.qm" 2>&1 | tail -1

if [ "$SYNC" = "1" ]; then
   for d in "$TOPDIR/build/translations" "$TOPDIR/build/bin/translations"; do
      [ -d "$d" ] && cp "$TOPDIR/translations/zh_CN.qm" "$d/" && echo "    已同步: $d"
   done
fi

echo "==> 完成: $TS"
