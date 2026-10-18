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

# ---- 跨平台确定性（Windows CI 实测教训，2026-10-18）----
# 本检查曾在 Windows CI 上连续三次误报"modules/hdf5 版本漂移"（run #3/#4/#5），
# 而 Linux 本地与 Ubuntu CI 全部通过。根因是两件事叠加：
#   1. LC_ALL 未固定 —— sort 的排序随 locale 变：en_US.UTF-8 下 modules/hdf5
#      排到 HighFive 之前（字典序忽略大小写），C locale 下相反。于是"第一个
#      被比对的条目"在不同环境不同，报错点名不稳定；
#   2. python3 的 stdout 换行 —— Windows runner 上的 python3 是 hostedtoolcache
#      原生 Windows Python，stdout 文本模式把 \n 写成 \r\n，清单侧每个 sha 带
#      尾随 \r，与 gitlink 侧永远失配；且错误消息里的 \r 会让日志渲染器在
#      该处截断，只剩"清单 <sha>"半句，极难排查。
# 修复：固定 C locale + 双侧剥 \r + python 侧写字节。下面三处措施缺一不可。
export LC_ALL=C

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
git ls-tree HEAD modules/ | awk '$1=="160000"{print $4"\t"$3}' | tr -d '\r' | sort > "$cur"

# ---- 从 MANIFEST 提取 path\tcommit（用 python 解析，避免 jq 依赖）----
man="$(mktemp)"; trap 'rm -f "$cur" "$man"' EXIT
python3 - "$MANIFEST" > "$man" <<'PY'
import json, sys
d = json.load(open(sys.argv[1], encoding="utf-8"))
out = []
for s in d.get("submodules", []):
    out.append("%s\t%s\n" % (s["path"], s["commit"]))
# 用 buffer 写字节而非文本流：规避 Windows Python stdout 的 \n -> \r\n 转换
sys.stdout.buffer.write("".join(out).encode("utf-8"))
PY
# 双保险：再剥一次 \r（防 MSYS2 管道引入的 CR），并用 C locale 排序保证顺序确定
tr -d '\r' < "$man" | sort > "$man.tmp" && mv "$man.tmp" "$man"

drift=0

# ---- 逐项比对 ----
echo "--- 逐子模块比对 ---"
while IFS=$'\t' read -r path sha; do
   [ -z "$path" ] && continue
   cur_sha="$(awk -F'\t' -v p="$path" '$1==p{print $2}' "$cur" | tr -d '\r')"
   if [ -z "$cur_sha" ]; then
      # 详情先打印再 fail：fail() 内部 exit 1，写在它后面的 echo 是死代码
      echo "  ✗ $path        MISSING(gitlink)"
      fail "子模块 $path 在仓库 gitlink 中不存在（.gitmodules 与索引不一致）"
      drift=1
   elif [ "$cur_sha" != "$sha" ]; then
      # 同上：先详情后 fail。历史上这里只有一行被 \r 截断的错误，排查极难
      echo "  ✗ $path"
      echo "     MANIFEST : $sha"
      echo "     仓库实际 : $cur_sha"
      fail "子模块 $path 版本漂移：清单 $sha != 仓库 $cur_sha（详见上方日志）"
      drift=1
   else
      echo "  ✅ $path  $sha"
   fi
done < "$man"

# ---- 检查仓库有、清单无（多余）----
while IFS=$'\t' read -r path sha; do
   [ -z "$path" ] && continue
   if ! awk -F'\t' -v p="$path" '$1==p{found=1} END{exit !found}' "$man"; then
      echo "  ✗ $path        EXTRA(gitlink, 清单缺失)"
      fail "仓库存在子模块 $path，但不在 MANIFEST 中（离线包可能漏打包）"
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
