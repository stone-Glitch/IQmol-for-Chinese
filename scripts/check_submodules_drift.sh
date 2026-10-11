#!/usr/bin/env bash
#
# check_submodules_drift.sh — 子模块版本漂移校验（P2-8 供应链校验）
#
# 对应外部评审报告 P2-8：
#   "CI 靠仓库内 tar.gz 解包子模块，不走 git submodule，且无版本漂移校验"
#
# 作用：比对 submodules-package/MANIFEST.json（离线包打包时的子模块快照）
# 与当前仓库 .gitmodules / gitlink 记录的实际 commit：
#   - 若某个子模块的 gitlink sha 与 MANIFEST 不一致 → 说明仓库已 bump 子模块
#     但离线包未重打，CI 会用旧源码构建 → 报错退出。
#   - 若缺失/多余子模块 → 同样报错。
#
# 用法（在仓库根执行，CI 解包后调用）：
#   scripts/check_submodules_drift.sh                 # 严格模式，drift 即 fail
#   DRIFT_WARN_ONLY=1 scripts/check_submodules_drift.sh   # 仅告警不 fail（本地调试）
#
set -euo pipefail

cd "$(dirname "$0")/.."
MANIFEST="submodules-package/MANIFEST.json"
WARN_ONLY="${DRIFT_WARN_ONLY:-0}"

fail() {
   if [ "$WARN_ONLY" = "1" ]; then
      echo "::warning::$1"
   else
      echo "::error::$1"
      exit 1
   fi
}

# ---- 前置检查 ----
if [ ! -f "$MANIFEST" ]; then
   fail "缺少 $MANIFEST —— 请先运行 scripts/gen_submodules_manifest.sh 生成子模块清单"
   echo "（仅告警模式）跳过漂移校验"
   exit 0
fi

if ! git rev-parse --git-dir >/dev/null 2>&1; then
   fail "当前目录不是 git 仓库，无法读取子模块 gitlink"
   exit 0
fi

echo "== 子模块版本漂移校验 =="
echo "清单：$MANIFEST"

# ---- 读取当前 gitlink（真实值）----
cur="$(mktemp)"; trap 'rm -f "$cur"' EXIT
git ls-tree HEAD modules/ | awk '$1=="160000"{print $4"\t"$3}' | sort > "$cur"

# ---- 从 MANIFEST 提取 path\tcommit（用 python 解析，避免 jq 依赖）----
man="$(mktemp)"; trap 'rm -f "$cur" "$man"' EXIT
python3 - "$MANIFEST" > "$man" <<'PY'
import json, sys
d = json.load(open(sys.argv[1], encoding="utf-8"))
for s in d.get("submodules", []):
    sys.stdout.write("%s\t%s\n" % (s["path"], s["commit"]))
PY
sort -o "$man" "$man"

drift=0

# ---- 逐项比对 ----
echo "--- 逐子模块比对 ---"
while IFS=$'\t' read -r path sha; do
   [ -z "$path" ] && continue
   cur_sha="$(awk -F'\t' -v p="$path" '$1==p{print $2}' "$cur")"
   if [ -z "$cur_sha" ]; then
      fail "子模块 $path 在仓库 gitlink 中不存在（.gitmodules 与索引不一致）"
      echo "  $path        MISSING(gitlink)"
      drift=1
   elif [ "$cur_sha" != "$sha" ]; then
      fail "子模块 $path 版本漂移：清单 $sha != 仓库 $cur_sha"
      echo "  $path"
      echo "     MANIFEST : $sha"
      echo "     仓库实际 : $cur_sha"
      drift=1
   else
      echo "  ✅ $path  $sha"
   fi
done < "$man"

# ---- 检查仓库有、清单无（多余）----
while IFS=$'\t' read -r path sha; do
   [ -z "$path" ] && continue
   if ! awk -F'\t' -v p="$path" '$1==p{found=1} END{exit !found}' "$man"; then
      fail "仓库存在子模块 $path，但不在 MANIFEST 中（离线包可能漏打包）"
      echo "  $path        EXTRA(gitlink, 清单缺失)"
      drift=1
   fi
done < "$cur"

if [ "$drift" = "0" ]; then
   echo "✅ 全部子模块版本一致，无漂移"
else
   echo ""
   echo "⚠️ 检测到子模块版本漂移。若为有意 bump，请重打离线包："
   echo "   重新生成 IQmol-submodules.tar.gz 后，运行 scripts/gen_submodules_manifest.sh 更新清单"
fi
