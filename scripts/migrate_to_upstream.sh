#!/usr/bin/env bash
#=============================================================================
# migrate_to_upstream.sh —— 上游升级迁移「一站式」执行器
#
# 用途: 上游 nutjunkie/IQmol3 发布新版本后, 把本仓库的全部汉化改动
#       迁移到新基线之上。本脚本把原先分散的三步固化为一条命令。
#
# 迁移三步（本脚本按序自动执行）:
#   ① patches/功能补丁-语言支持.patch     语言加载 / Language 偏好 / GCC15 cstdint
#   ② scripts/i18n/replay_tr.py --apply   tr() 包裹重放（规则表 487 条 / 58 文件）
#   ③ patches/功能补丁-非机械改动.patch    35 个文件的非机械逻辑改动
#
# 实测效果（对上游 af7ff60 干净树执行 ①→②→③）:
#   69 / 69 个源码文件与成果版完全一致（100% 复现）
#
# 用法:
#   scripts/migrate_to_upstream.sh --check     # 只预检（默认），不落盘
#   scripts/migrate_to_upstream.sh --apply     # 实际执行三步
#   scripts/migrate_to_upstream.sh --apply --target /d/IQmol-new
#   scripts/migrate_to_upstream.sh --apply --target /d/IQmol-new --selfcheck
#                                              # 迁移后自动比对（推荐）
#   scripts/migrate_to_upstream.sh --selfcheck-only --target /d/IQmol-new
#                                              # 只比对，不执行迁移
#
# --selfcheck 干什么（rw4e6e）:
#   迁移三步跑完后，把目标树的 69 个汉化相关源码文件与本仓库成果逐一 diff，
#   输出「完全一致文件数 / 总文件数」，列出缺失与不一致文件及其差异行数；
#   有一处不一致即以退出码 3 结束，避免上游大改时补丁静默失败/部分应用。
#
# 前置:
#   目标树必须是【干净的上游检出】，且工作区无未提交改动。
#   本脚本不负责 git fetch/merge —— 那部分交给 sync_upstream.sh。
#
# 与之配合:
#   scripts/sync_upstream.sh     —— 在本仓库内吸收上游更新（git merge 路线）
#   本脚本                        —— 在一个【全新上游树】上重放汉化（补丁路线）
#   两条路线按需二选一：
#     · 共享 git 历史、改动不大  → 用 sync_upstream.sh --merge
#     · 上游大重构 / 想干净重来  → 用本脚本在干净树上重放
#=============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

PATCH_LANG="$REPO_DIR/patches/功能补丁-语言支持.patch"
PATCH_NONMECH="$REPO_DIR/patches/功能补丁-非机械改动.patch"
RULES="$REPO_DIR/scripts/i18n/wrap_tr.rules"
REPLAY="$REPO_DIR/scripts/i18n/replay_tr.py"
TARGET="$REPO_DIR"
DO_APPLY=0
DO_SELFCHECK=0
SELFCHECK_ONLY=0

while [ $# -gt 0 ]; do
  case "$1" in
    --apply)  DO_APPLY=1; shift ;;
    --target) TARGET="${2:-}"; shift 2 ;;
    --check)  DO_APPLY=0; shift ;;
    --selfcheck) DO_SELFCHECK=1; shift ;;
    --selfcheck-only) SELFCHECK_ONLY=1; DO_SELFCHECK=1; shift ;;
    -h|--help) sed -n '2,55p' "$0"; exit 0 ;;
    *) echo "未知参数: $1" >&2; exit 2 ;;
  esac
done

info() { printf '==> %s\n' "$*"; }
warn() { printf 'WARN: %s\n' "$*" >&2; }
die()  { printf 'ERROR: %s\n' "$*" >&2; exit 1; }

#-----------------------------------------------------------------------------
# 迁移影响文件清单（= 两个补丁涉及的文件 ∪ 规则表涉及的文件）
#   这是「迁移后自动比对」的比对范围：只比汉化真正动过的文件，
#   避免构建产物/第三方子模块造成的噪声。
#-----------------------------------------------------------------------------
migration_file_list() {
  {
    grep -h '^+++ b/' "$PATCH_LANG" "$PATCH_NONMECH" 2>/dev/null \
      | sed -e 's|^+++ b/||' -e 's/[[:space:]].*$//'
    grep -v '^#' "$RULES" 2>/dev/null | cut -f1
  } | grep -v '^$' | sort -u
}

#-----------------------------------------------------------------------------
# 迁移后自动比对（selfcheck）
#   参考树 = 本仓库（汉化成果版）  目标树 = $TARGET
#   输出吻合度；有缺失/不一致 → 退出码 3
#-----------------------------------------------------------------------------
selfcheck() {
  local ref="$REPO_DIR" tgt="$TARGET"
  local total=0 same=0 differ=0 missing=0 refmissing=0
  local -a diff_files=() miss_files=()

  if [ "$(cd "$ref" 2>/dev/null && pwd)" = "$(cd "$tgt" 2>/dev/null && pwd)" ]; then
    warn "selfcheck: 目标树就是本仓库自身（TARGET=REPO_DIR），比对无意义。"
    warn "            请用 --target <新上游树> 指定迁移后的目录再比对。"
    return 3
  fi

  echo
  info "迁移后自动比对（selfcheck）"
  echo "    参考树（本仓库成果）: $ref"
  echo "    目标树（迁移结果）  : $tgt"

  while IFS= read -r f; do
    [ -n "$f" ] || continue
    total=$((total + 1))
    if [ ! -f "$tgt/$f" ]; then
      missing=$((missing + 1)); miss_files+=("$f"); continue
    fi
    if [ ! -f "$ref/$f" ]; then
      refmissing=$((refmissing + 1)); continue
    fi
    if diff -q "$ref/$f" "$tgt/$f" >/dev/null 2>&1; then
      same=$((same + 1))
    else
      local n
      n="$(diff -u "$ref/$f" "$tgt/$f" 2>/dev/null \
          | grep -c -E '^[+-][^+-]' || true)"
      differ=$((differ + 1)); diff_files+=("$f (差异 $n 行)")
    fi
  done < <(migration_file_list)

  echo "    --------------------------------------------"
  echo "    比对文件总数    : $total"
  echo "    完全一致        : $same"
  echo "    不一致          : $differ"
  echo "    目标树缺失      : $missing"
  if [ "$refmissing" -gt 0 ]; then
    echo "    参考树缺失(忽略) : $refmissing"
  fi

  if [ "$differ" -gt 0 ]; then
    echo "    不一致明细:"
    for x in "${diff_files[@]}"; do echo "      - $x"; done
  fi
  if [ "$missing" -gt 0 ]; then
    echo "    缺失明细:"
    for x in "${miss_files[@]}"; do echo "      - $x"; done
  fi

  if [ "$same" -eq "$total" ] && [ "$differ" -eq 0 ] && [ "$missing" -eq 0 ]; then
    echo "    ✅ $same / $total 全部一致（100% 复现）"
    return 0
  fi
  echo "    ❌ 吻合度 $same / $total —— 请按 docs/上游升级迁移指南.md「上游大改时怎么办」处理"
  return 3
}

# 只比对、不迁移：selfcheck 只读，不要求目标树工作区干净
if [ "$SELFCHECK_ONLY" = "1" ]; then
  [ -d "$TARGET" ] || die "目标目录不存在: $TARGET"
  selfcheck
  exit $?
fi

#-----------------------------------------------------------------------------
# 0. 前置检查
#-----------------------------------------------------------------------------
[ -d "$TARGET" ] || die "目标目录不存在: $TARGET"
for f in "$PATCH_LANG" "$PATCH_NONMECH" "$RULES" "$REPLAY"; do
  [ -f "$f" ] || die "缺少必要文件: $f"
done

cd "$TARGET"
if [ -d .git ] && [ -n "$(git status --porcelain 2>/dev/null)" ]; then
  die "目标树工作区有未提交改动，请先 commit / stash / 换一个干净检出。"
fi

info "仓库    : $REPO_DIR"
info "目标树  : $TARGET"
info "模式    : $([ "$DO_APPLY" = "1" ] && echo 实际执行 || echo 预检-only)"
[ "$DO_SELFCHECK" = "1" ] && info "自检    : 迁移后自动比对（selfcheck）"
echo

#-----------------------------------------------------------------------------
# 1. 预检三个步骤能否干净应用
#-----------------------------------------------------------------------------
FAIL=0

info "① 预检 功能补丁-语言支持.patch"
if git apply --check "$PATCH_LANG" 2>/dev/null; then
  echo "    [ OK ] 可干净应用"
else
  echo "    [FAIL] 无法应用（目标树不是干净上游？或已打过？）"
  FAIL=1
fi

info "② 预检 tr() 重放规则表"
RULE_N=$(grep -vc '^#' "$RULES" 2>/dev/null || echo 0)
FILE_N=$(grep -v '^#' "$RULES" 2>/dev/null | cut -f1 | sort -u | wc -l | tr -d ' ')
echo "    规则 $RULE_N 条 / $FILE_N 文件"
if [ "$RULE_N" -gt 0 ]; then
  echo "    [ OK ] 规则表可读"
else
  echo "    [FAIL] 规则表为空"; FAIL=1
fi

info "③ 预检 功能补丁-非机械改动.patch"
# 该补丁的上下文基于「上游 + ① + ②」, 因此单独 --check 在原始上游上必然失败。
# 这里只确认文件非空与可解析, 真正校验放到实际执行时。
if [ -s "$PATCH_NONMECH" ]; then
  echo "    [ OK ] 补丁存在（$(grep -c '^+++' "$PATCH_NONMECH") 个文件）"
  echo "    注: 其上下文依赖 ①+② 结果，须在 ①+② 之后应用"
else
  echo "    [FAIL] 补丁为空"; FAIL=1
fi
echo

if [ "$FAIL" = "1" ]; then
  die "预检未通过，未做任何改动。"
fi

if [ "$DO_APPLY" = "0" ]; then
  info "预检通过。确认无误后加 --apply 实际执行。"
  exit 0
fi

#-----------------------------------------------------------------------------
# 2. 实际执行三步
#-----------------------------------------------------------------------------
info "① 应用 功能补丁-语言支持.patch"
git apply "$PATCH_LANG"
echo "    完成（6 个文件）"

info "② 重放 tr() 包裹"
mkdir -p scripts/i18n
cp "$REPLAY" scripts/i18n/replay_tr.py
cp "$RULES"  scripts/i18n/wrap_tr.rules
python3 scripts/i18n/replay_tr.py --apply --quiet 2>&1 | sed 's/^/    /'

info "③ 应用 功能补丁-非机械改动.patch"
git apply "$PATCH_NONMECH"
echo "    完成（35 个文件）"

#-----------------------------------------------------------------------------
# 3. 迁移后自动比对（--selfcheck）
#-----------------------------------------------------------------------------
if [ "$DO_SELFCHECK" = "1" ]; then
  selfcheck
  SC=$?
  if [ "$SC" != "0" ]; then
    echo
    echo "提示：不一致通常意味着上游改动导致补丁上下文漂移（部分应用/静默失败）。"
    echo "      恢复步骤见 docs/上游升级迁移指南.md「上游大改时怎么办」。"
    exit "$SC"
  fi
fi

#-----------------------------------------------------------------------------
# 4. 收尾提示
#-----------------------------------------------------------------------------
echo
echo "==================== 迁移完成 ===================="
echo "  已应用: ① 语言支持补丁  ② tr() 重放  ③ 非机械改动补丁"
echo
echo "  后续（译文资源与新增资产不在本脚本范围，需另行带入）:"
echo "    cp -r <本仓库>/translations  $TARGET/"
echo "    cp -r <本仓库>/share         $TARGET/"
echo "    cp -r <本仓库>/doc           $TARGET/"
echo "    cp -r <本仓库>/docs          $TARGET/"
echo
echo "  验证:"
echo "    bash scripts/build_windows.sh        # 构建"
echo "    grep -c 'type=\"unfinished\"' translations/zh_CN.ts   # 应为 0"
echo "=================================================="
