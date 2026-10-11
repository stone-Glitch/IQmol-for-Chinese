#!/usr/bin/env bash
# ============================================================================
# change_surface.sh —— 量化「汉化改动面」（第三层 D 项配套工具）
#
# 用途：每次上游升级后，度量我们相对上游基线的改动规模，判断改动是否
#       按第三层规范组织（改动面越小、可脚本重放比例越高 → 升级越轻松）。
#
# 用法：
#   bash scripts/i18n/change_surface.sh [<基准提交>]
#   # 默认基准 af7ff60（上游 nutjunkie/IQmol3 v3.2.3）
#   # 也可用环境变量： UPSTREAM_BASE=<sha>
#
# 输出：
#   控制台报告 + 归档到 docs/验证记录/改动面基线.md
#
# 指标（对应方案 D 节）：
#   · 修改 / 新增 / 删除 文件数
#   · 修改文件的分类：tr() 类 / 构建类 / 语言逻辑类 / 资源类 / 文档类 / 脚本类 / 其他
#   · 修改行数总和（+/−）
#   · 可脚本重放比例 = tr() 类文件数 / 全部修改文件数
#
# 分类判据（按路径）：
#   tr           : src/**/*.C *.h（.h 也可能含 tr 兜底文本）
#   lang         : src/Main/IQmolApplication.C / MainWindow.C（语言切换相关）
#   build        : CMakeLists.txt / cmake/ / *.pro / build|package|deploy|make_ 脚本
#   res          : translations/ resources/ share/ icons/
#   doc          : docs/ doc/ *.md *.txt
#   script       : scripts/
#   other        : 兜底
#
# 注：若仓库为浅克隆、缺少基线到 HEAD 的中间对象，行数统计会降级为 N/A；
#     文件清单（name-status）通常仍可用，故分类指标不受影响。
# ============================================================================
set -uo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO"

BASE="${1:-${UPSTREAM_BASE:-af7ff60c0fe56e77660f7ad42e58cd8fb4f9deb0}}"
OUT_DOC="docs/验证记录/改动面基线.md"

echo "================================================================"
echo " 汉化改动面度量"
echo " 基准提交: ${BASE:0:10}"
echo " 当前 HEAD: $(git rev-parse --short HEAD)"
echo "================================================================"

if ! git cat-file -e "$BASE^{commit}" 2>/dev/null; then
   echo "⚠️  基准提交 $BASE 不在本仓库，无法度量。"
   echo "    请先: git fetch <上游> $BASE   （或传入正确的基准）"
   exit 2
fi

# --- 文件清单（name-status；TAB 分隔： 状态 <TAB> 路径）--------------------
NAMESTAT=$(git diff --name-status "$BASE" HEAD 2>/dev/null || true)
if [ -z "$NAMESTAT" ]; then
   echo "⚠️  无法完成 diff（仓库为浅克隆 / 缺少中间对象），且未取到文件清单。"
   exit 3
fi

# --- 分类键（ASCII，供关联数组使用）→ 显示名 -------------------------------
KEYS=(tr lang build res doc script other)
declare -A LABEL=([tr]="tr() 类" [lang]="语言逻辑类" [build]="构建类"
                  [res]="资源类" [doc]="文档类" [script]="脚本类" [other]="其他")
declare -A CNT MOD ADD DEL
total_mod=0; total_add=0; total_del=0

classify() {
   local p="$1"
   case "$p" in
      src/*.C|src/*.c|src/*.cpp|src/*.hpp|src/*.h)
         if echo "$p" | grep -qE 'IQmolApplication\.C$|MainWindow\.C$'; then
            echo "lang"; else echo "tr"; fi ;;
      CMakeLists.txt|*/CMakeLists.txt|cmake/*|*.pro|*.prf)
         echo "build" ;;
      *build*.sh|*build*.bat|*package*.sh|*deploy*.sh|make_*.sh|*install*.sh)
         echo "build" ;;
      translations/*|resources/*|share/*|icons/*)
         echo "res" ;;
      docs/*|doc/*|*.md|*.txt)
         echo "doc" ;;
      scripts/*)
         echo "script" ;;
      *)
         echo "other" ;;
   esac
}

while IFS=$'\t' read -r st path _rest; do
   [ -z "${path:-}" ] && continue
   st="${st:0:1}"
   cls=$(classify "$path")
   CNT[$cls]=$(( ${CNT[$cls]:-0} + 1 ))
   case "$st" in
      M) MOD[$cls]=$(( ${MOD[$cls]:-0} + 1 )); total_mod=$((total_mod+1)) ;;
      A) ADD[$cls]=$(( ${ADD[$cls]:-0} + 1 )); total_add=$((total_add+1)) ;;
      D) DEL[$cls]=$(( ${DEL[$cls]:-0} + 1 )); total_del=$((total_del+1)) ;;
   esac
done <<< "$NAMESTAT"

# --- 行数（可能因对象缺失而 N/A）-----------------------------------------
add_lines="N/A"; del_lines="N/A"
NUMSTAT=$(git diff --numstat "$BASE" HEAD 2>/dev/null || true)
if [ -n "$NUMSTAT" ]; then
   add_lines=0; del_lines=0
   while IFS=$'\t' read -r a d _rest; do
      [[ "$a" =~ ^[0-9]+$ ]] && add_lines=$(( add_lines + a ))
      [[ "$d" =~ ^[0-9]+$ ]] && del_lines=$(( del_lines + d ))
   done <<< "$NUMSTAT"
fi

# --- 可脚本重放比例 -------------------------------------------------------
tr_files=${MOD[tr]:-0}
replay_pct=0
[ "$total_mod" -gt 0 ] && replay_pct=$(( tr_files * 100 / total_mod ))

# --- 控制台输出 -----------------------------------------------------------
echo
echo "【文件数】"
echo "  修改: $total_mod    新增: $total_add    删除: $total_del"
echo
echo "【修改文件分类】（修改数 / 该类别总数）"
for k in "${KEYS[@]}"; do
   printf "  %-10s  改 %-3d  计 %-3d\n" "${LABEL[$k]}" "${MOD[$k]:-0}" "${CNT[$k]:-0}"
done
echo
echo "【行数】 +(新增) = $add_lines   -(删除) = $del_lines"
[ "$add_lines" = "N/A" ] && echo "  （N/A：仓库为浅克隆，缺少中间对象；文件清单分类不受影响）"
echo
echo "【可脚本重放比例】 tr() 类 $tr_files / 全部修改 $total_mod = ${replay_pct}%"
echo "  （越高越好：tr() 类文件的包裹可由 scripts/i18n/replay_tr.py 从上游一键重建）"

# --- 归档 -----------------------------------------------------------------
{
   echo "# 改动面基线"
   echo
   echo "> 自动生成：\`bash scripts/i18n/change_surface.sh\` ｜ 生成时间：$(date '+%Y-%m-%d %H:%M')"
   echo "> 基准提交：\`${BASE:0:10}\`（上游 v3.2.3）｜ 当前 HEAD：\`$(git rev-parse --short HEAD)\`"
   echo
   echo "## 文件数"
   echo
   echo "| 类型 | 数量 |"
   echo "|---|---|"
   echo "| 修改 | $total_mod |"
   echo "| 新增 | $total_add |"
   echo "| 删除 | $total_del |"
   echo
   echo "## 修改文件分类"
   echo
   echo "| 类别 | 修改数 | 该类别总数 |"
   echo "|---|---|---|"
   for k in "${KEYS[@]}"; do
      echo "| ${LABEL[$k]} | ${MOD[$k]:-0} | ${CNT[$k]:-0} |"
   done
   echo
   echo "## 行数"
   echo
   echo "- 新增行：$add_lines"
   echo "- 删除行：$del_lines"
   [ "$add_lines" = "N/A" ] && echo "- 注：浅克隆缺少中间对象，行数未能统计（分类指标不受影响）"
   echo
   echo "## 可脚本重放比例"
   echo
   echo "**tr() 类 $tr_files / 全部修改 $total_mod = ${replay_pct}%**"
   echo
   echo "> 该比例越高，上游升级越轻松：tr() 类文件的包裹可由"
   echo "> \`scripts/i18n/replay_tr.py\` 从干净上游基线一键重建。"
   echo
   echo "> 若某次升级后「修改文件数」异常上升，说明有改动未按第三层规范组织，应回退重做。"
   echo
   echo "---"
   echo
   echo "> 本文件由 \`change_surface.sh\` 生成，可重复执行覆盖。"
} > "$OUT_DOC"

echo
echo "✅ 已归档: $OUT_DOC"
