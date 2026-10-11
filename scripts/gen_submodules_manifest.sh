#!/usr/bin/env bash
#
# gen_submodules_manifest.sh — 生成子模块版本清单（P2-8 供应链校验）
#
# 背景：本仓库的 CI 走「解包 submodules-package/IQmol-submodules.tar.gz」内嵌构建，
# 而非 `git submodule update --init`。README 声称离线包内子模块"版本与 .gitmodules
# 记录的 commit 完全一致"，但此前无任何自动校验：上游 bump 了子模块 commit、或重新
# 打包时漏更新，CI 会静默用旧版本编出包且不报错。
#
# 本脚本生成 submodules-package/MANIFEST.json，记录每个子模块的：
#   path      —— 相对仓库根的路径（如 modules/openbabel）
#   commit    —— 仓库 gitlink 记录的 commit sha（即 .gitmodules 索引树里的值）
#   url       —— .gitmodules 声明的上游地址
#   pack_time —— 生成本清单的时间（UTC）
#
# 配套 scripts/check_submodules_drift.sh 在 CI 解包后读此清单，与当前仓库的
# gitlink sha 逐一比对，不一致即 fail。
#
# 用法（在仓库根执行）：
#   scripts/gen_submodules_manifest.sh
#
set -euo pipefail

cd "$(dirname "$0")/.."
ROOT="$(pwd)"
MANIFEST="submodules-package/MANIFEST.json"
PACK_TIME="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

# 校验前提：必须在 git 仓库内
if ! git rev-parse --git-dir >/dev/null 2>&1; then
   echo "::error::当前目录不是 git 仓库，无法读取子模块 gitlink" >&2
   exit 1
fi

# 从 .gitmodules 读取 path -> url
declare -A URLS
cur_path=""
while IFS= read -r line; do
   case "$line" in
      "[submodule "*)
         cur_path="" ;;
      *"path = "*)
         cur_path="${line#*path = }" ;;
      *"url = "*)
         if [ -n "$cur_path" ]; then URLS["$cur_path"]="${line#*url = }"; fi ;;
   esac
done < .gitmodules

# 从 git 索引读取每个子模块的 gitlink commit（type=commit 的 160000 条目）
# 输出形如：160000 commit <sha>\tmodules/openbabel
tmp="$(mktemp)"
trap 'rm -f "$tmp"' EXIT
git ls-tree HEAD modules/ | awk '$1=="160000"{print $3"\t"$4}' > "$tmp"

# 组装 JSON
{
   printf '{\n'
   printf '  "generated_at": "%s",\n' "$PACK_TIME"
   printf '  "source": "git ls-tree HEAD modules/ (gitlink commits)",\n'
   printf '  "note": "该清单记录离线包打包时的子模块快照；CI 解包后由 scripts/check_submodules_drift.sh 比对仓库 gitlink sha，不一致即 fail",\n'
   printf '  "submodules": [\n'
   first=1
   while IFS=$'\t' read -r sha path; do
      [ -z "$sha" ] && continue
      url="${URLS[$path]:-}"
      if [ "$first" = "1" ]; then first=0; else printf ',\n'; fi
      printf '    { "path": "%s", "commit": "%s", "url": "%s" }' "$path" "$sha" "$url"
   done < "$tmp"
   printf '\n  ]\n'
   printf '}\n'
} > "$MANIFEST"

n="$(grep -c '"path"' "$MANIFEST" || true)"
echo "✅ 已生成 $MANIFEST（$n 个子模块，打包时间 $PACK_TIME）"
