#!/usr/bin/env bash
#=============================================================================
# sync_upstream.sh —— 上游 IQmol 升级迁移助手
#
# 用途: 当上游 nutjunkie/IQmol3 发布新版本 / 新提交后, 用本脚本把汉化改动
#       安全地迁移到新基线之上。
#
# 背景: 本仓库 fork 自上游, 与上游共享 git 历史。汉化改动全部是对上游的
#       "增量修改", 因此可以用标准 git merge 吸收上游更新, 冲突通常很少。
#
# 用法:
#   scripts/sync_upstream.sh            # 检查上游是否有更新并试合并(不提交)
#   scripts/sync_upstream.sh --merge    # 实际执行合并并提交
#   scripts/sync_upstream.sh --po       # 额外生成可移植补丁集(cherry-pick 用)
#   scripts/sync_upstream.sh --status   # 只报告当前与上游的差距
#=============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$SRC_DIR"

UPSTREAM_REMOTE="${UPSTREAM_REMOTE:-origin}"   # 上游远程名(默认 origin)
UPSTREAM_BRANCH="${UPSTREAM_BRANCH:-master}"
PATCH_DIR="${PATCH_DIR:-$SRC_DIR/patches}"
DO_MERGE=0
DO_PATCH=0
STATUS_ONLY=0

for a in "$@"; do
  case "$a" in
    --merge)  DO_MERGE=1 ;;
    --po)     DO_PATCH=1 ;;
    --status) STATUS_ONLY=1 ;;
    -h|--help) sed -n '2,20p' "$0"; exit 0 ;;
    *) echo "未知参数: $a" >&2; exit 2 ;;
  esac
done

hr() { printf '%s\n' "------------------------------------------------------------"; }
info() { printf '==> %s\n' "$*"; }
warn() { printf 'WARN: %s\n' "$*" >&2; }

#-----------------------------------------------------------------------------
# 0. 前置检查
#-----------------------------------------------------------------------------
if [ -n "$(git status --porcelain)" ]; then
  warn "工作区有未提交改动，请先 commit 或 stash。"
  git status -s | head
  exit 1
fi

#-----------------------------------------------------------------------------
# 1. 拉取上游
#-----------------------------------------------------------------------------
info "拉取上游 $UPSTREAM_REMOTE/$UPSTREAM_BRANCH ..."
if ! git fetch "$UPSTREAM_REMOTE" "$UPSTREAM_BRANCH" 2>&1 | tail -3; then
  warn "拉取上游失败(网络?)。国内可设 UPSTREAM_REMOTE 指向带代理的远程。"
  exit 1
fi
UPSTREAM_REF="FETCH_HEAD"

#-----------------------------------------------------------------------------
# 2. 计算差距
#-----------------------------------------------------------------------------
BASE="$(git merge-base HEAD "$UPSTREAM_REF")"
OURS_AHEAD="$(git log --oneline "$BASE"..HEAD | wc -l | tr -d ' ')"
THEIRS_AHEAD="$(git log --oneline "$BASE".."$UPSTREAM_REF" | wc -l | tr -d ' ')"

hr
info "上游基线(merge-base): $(git rev-parse --short "$BASE")"
info "我方独有提交: $OURS_AHEAD 个"
info "上游新增提交: $THEIRS_AHEAD 个"
hr

if [ "$THEIRS_AHEAD" = "0" ]; then
  info "上游无新提交，无需迁移。当前已是最新。"
  [ "$STATUS_ONLY" = "1" ] && exit 0
  exit 0
fi

echo "上游新增提交列表："
git log --oneline "$BASE".."$UPSTREAM_REF" | head -30
hr
echo "这些提交改动的文件："
git diff --name-only "$BASE" "$UPSTREAM_REF" | head -40
hr

if [ "$STATUS_ONLY" = "1" ]; then
  info "--status 模式，仅报告，不合并。"
  exit 0
fi

#-----------------------------------------------------------------------------
# 3. 预判冲突面（我方也改过的文件 = 潜在冲突）
#-----------------------------------------------------------------------------
OURS_FILES="$(git diff --name-only "$BASE" HEAD || true)"
THEIRS_FILES="$(git diff --name-only "$BASE" "$UPSTREAM_REF" || true)"
OVERLAP="$(comm -12 <(echo "$OURS_FILES" | sort -u) <(echo "$THEIRS_FILES" | sort -u) || true)"

if [ -n "$OVERLAP" ]; then
  warn "以下文件【双方都改过】，合并时可能冲突，需人工确认："
  echo "$OVERLAP" | sed 's/^/    /'
else
  info "双方改动无文件重叠 —— 预计可干净合并。"
fi
hr

#-----------------------------------------------------------------------------
# 4. 生成可移植补丁集（--po）
#-----------------------------------------------------------------------------
if [ "$DO_PATCH" = "1" ]; then
  mkdir -p "$PATCH_DIR"
  info "生成补丁集到 $PATCH_DIR ..."
  # 按主题拆分：i18n 源码改动 / 构建修复 / 文档资产
  git format-patch "$BASE"..HEAD -o "$PATCH_DIR" >/dev/null
  echo "  共 $(ls "$PATCH_DIR"/*.patch 2>/dev/null | wc -l | tr -d ' ') 个补丁"
  info "上游换基线后可用: git am $PATCH_DIR/*.patch"
fi

#-----------------------------------------------------------------------------
# 5. 合并（--merge）
#-----------------------------------------------------------------------------
if [ "$DO_MERGE" = "1" ]; then
  info "执行合并: 把上游 $THEIRS_AHEAD 个提交并入当前分支 ..."
  if git merge "$UPSTREAM_REF" -m "merge: 吸收上游更新（$(git rev-parse --short "$UPSTREAM_REF")，$THEIRS_AHEAD 个提交）"; then
    info "合并成功，无冲突。"
  else
    warn "合并存在冲突，请解决后 commit。冲突文件："
    git diff --name-only --diff-filter=U | sed 's/^/    /'
    warn "解决要点："
    echo "    - 若冲突在 tr() 包裹处: 以上游新代码为准，重新套 tr()"
    echo "    - 若冲突在 CMakeLists.txt: 保留双方的构建修复 + 汉化集成段"
    echo "    - 若冲突在 .ts: 以上游的 source 为准，重新 lupdate 后合并译文"
    exit 1
  fi
  info "提交后建议跑一次构建验证: bash scripts/build_windows.sh --clean"
fi

if [ "$DO_MERGE" = "0" ]; then
  info "（未加 --merge，仅做预检。确认无误后加 --merge 实际合并）"
  echo ""
  echo "预检合并(不落盘)："
  git merge --no-commit --no-ff "$UPSTREAM_REF" >/dev/null 2>&1 && \
    { echo "    ✓ 可干净合并"; git merge --abort 2>/dev/null || true; } || \
    { echo "    ⚠ 有冲突，需人工处理"; git merge --abort 2>/dev/null || true; }
fi
