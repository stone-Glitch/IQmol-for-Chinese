#!/usr/bin/env bash
# check_wiki_sync.sh —— GitHub Wiki 同步提醒钩子（非阻塞）
#
# 作用：在 git commit 前，检查「已被 GitHub Wiki 镜像的文档」是否相对 HEAD 有改动；
#       若有，打印提醒：哪些文档改动后需要同步更新对应 Wiki 页面。
#       本钩子**只提醒、不阻断提交**（始终 exit 0）。
#
# 安装（一次性）：
#   cp scripts/check_wiki_sync.sh .git/hooks/pre-commit && chmod +x .git/hooks/pre-commit
# 或软链（便于随仓库更新钩子本体）：
#   ln -sf ../../scripts/check_wiki_sync.sh .git/hooks/pre-commit
#
# Wiki 仓库：git@github.com:stone-Glitch/IQmol-for-Chinese.wiki.git
set -uo pipefail

root="$(git rev-parse --show-toplevel 2>/dev/null)" || { echo "（非 git 仓库，跳过 wiki 同步检查）"; exit 0; }
cd "$root"

# 文档路径 → 对应 Wiki 页面
# 格式： "<本地相对路径>|<Wiki 页面名>"
MAP=(
  "docs/README.md|Home"
  "docs/仓库结构.md|Home"
  "docs/汉化工程|Localization"
  "docs/构建与打包|Build"
  "docs/汉化工程/无显卡环境运行与录屏.md|Build"
  "scripts/publish_release.sh|Build"
  ".github/workflows|Build"
  "docs/推广视频|Video"
  "scripts/video|Video"
  "scripts/video/narration.py|Video"
  "docs/汉化工程/文档整理报告.md|Home"
)

declare -A page_files
for entry in "${MAP[@]}"; do
  path="${entry%%|*}"; page="${entry##*|}"
  # 相对 HEAD 检测改动（含未暂存与已暂存）
  if git diff --quiet HEAD -- "$path" 2>/dev/null; then
    continue
  fi
  page_files["$page"]+=" $path"
done

if [ "${#page_files[@]}" -eq 0 ]; then
  exit 0
fi

echo
echo "┌──────────────────────────────────────────────────────────────┐"
echo "│  ⚠ Wiki 同步提醒：以下文档相对 HEAD 有改动，请同步 GitHub Wiki │"
echo "└──────────────────────────────────────────────────────────────┘"
for page in "${!page_files[@]}"; do
  echo "  • Wiki 页面【$page】← 改动文件:"
  for f in ${page_files["$page"]}; do
    echo "      - $f"
  done
done
echo "  同步方式：在 /root/iqmol_wiki（或你的 wiki 本地克隆）改对应页后 git push origin master"
echo "  Wiki 地址：https://github.com/stone-Glitch/IQmol-for-Chinese/wiki"
echo
exit 0
