#!/usr/bin/env bash
# 一键发布 GitHub Release —— IQmol-for-Chinese v3.2.3-zh_CN
# 用法：
#   GITHUB_TOKEN=ghp_xxxxxxxx bash publish_release.sh
#   或先把 token 写进同目录 .token 文件：echo 'ghp_xxx' > .token && bash publish_release.sh
# token 所需权限：公开仓库勾选 public_repo（或细粒度 Contents: Read and write）
#
# 路径约定（已消除三向不一致）：
#   • 发布说明唯一真源：仓库根 docs/构建与打包/release_notes.md（脚本目录下同名文件为旧兼容位）
#   • 附件默认在脚本目录（向后兼容）；也可用 ASSETS_DIR=/path bash publish_release.sh 指定，
#     脚本会依次在 ASSETS_DIR → 仓库根 → 脚本目录 查找，首个命中即用之
#   • SHA256SUMS.txt 与待校验包需放在同一目录（脚本自动 cd 到其所在目录执行 sha256sum -c）
set -euo pipefail

REPO="stone-Glitch/IQmol-for-Chinese"
TAG="v3.2.3-zh_CN"
TITLE="IQmol 简体中文本地化版 v3.2.3-zh_CN"
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# 仓库根（scripts/ 的上一级），用于定位文档真源与回退查找附件
REPO_ROOT="$(cd "$DIR/.." && pwd)"
API="https://api.github.com"
UPLOADS="https://uploads.github.com"

TOKEN="${GITHUB_TOKEN:-${GH_TOKEN:-}}"
if [ -z "$TOKEN" ] && [ -f "$DIR/.token" ]; then
  TOKEN="$(tr -d '[:space:]' < "$DIR/.token")"
fi
if [ -z "$TOKEN" ]; then
  echo "✗ 缺少 GitHub Token。"
  echo "  用法：GITHUB_TOKEN=ghp_xxxxxxxx bash $0"
  echo "  也可：echo 'ghp_xxxxxxxx' > $DIR/.token 后重跑（.token 已在 .gitignore 风险内，用完请删）"
  exit 1
fi

# 附件清单（相对脚本目录）
ASSETS=(
  "IQmol-win64-3.2.3-zh_CN.zip"
  "IQmol-linux-x86_64.tar.gz"
  "SHA256SUMS.txt"
)

# 发布说明唯一真源：docs/构建与打包/release_notes.md（scripts/ 下同名文件为旧兼容位置）
NOTES_FILE="$REPO_ROOT/docs/构建与打包/release_notes.md"
[ -f "$NOTES_FILE" ] || NOTES_FILE="$DIR/release_notes.md"
[ -f "$NOTES_FILE" ] || { echo "✗ 缺少发布说明（已尝试 $REPO_ROOT/docs/构建与打包/release_notes.md 与 $DIR/release_notes.md）"; exit 1; }

# 附件目录：可用 ASSETS_DIR 环境变量覆盖；默认脚本目录（向后兼容），并回退到仓库根
ASSETS_DIR="${ASSETS_DIR:-$DIR}"
find_asset() {
  local f="$1" d
  for d in "$ASSETS_DIR" "$REPO_ROOT" "$DIR"; do
    [ -f "$d/$f" ] && { printf '%s' "$d/$f"; return 0; }
  done
  return 1
}
for f in "${ASSETS[@]}"; do
  find_asset "$f" >/dev/null || { echo "✗ 缺少附件：$f（已搜索 $ASSETS_DIR、$REPO_ROOT、$DIR）"; exit 1; }
done

auth=(-H "Authorization: Bearer $TOKEN" -H "Accept: application/vnd.github+json")

echo "▶ 1/3 校验附件完整性"
SHA_FILE="$(find_asset SHA256SUMS.txt)"
( cd "$(dirname "$SHA_FILE")" && sha256sum -c SHA256SUMS.txt )

echo "▶ 2/3 创建 Release（tag: $TAG）"
BODY_FILE="$NOTES_FILE"
payload="$(python3 -c "
import json, sys
print(json.dumps({
    'tag_name': sys.argv[1],
    'name': sys.argv[2],
    'body': open(sys.argv[3], encoding='utf-8').read(),
    'draft': False,
    'prerelease': False
}))
" "$TAG" "$TITLE" "$BODY_FILE")"

resp="$(curl -sS -X POST "${auth[@]}" "$API/repos/$REPO/releases" -d "$payload")"
upload_url="$(printf '%s' "$resp" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('upload_url',''))" 2>/dev/null || true)"

if [ -z "$upload_url" ]; then
  msg="$(printf '%s' "$resp" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('message',''))" 2>/dev/null || true)"
  if printf '%s' "$msg" | grep -qi "already_exists"; then
    echo "  ℹ Release 已存在，改为向现有 Release 追加/覆盖附件"
    resp="$(curl -sS "${auth[@]}" "$API/repos/$REPO/releases/tags/$TAG")"
    upload_url="$(printf '%s' "$resp" | python3 -c "import json,sys; print(json.load(sys.stdin).get('upload_url',''))")"
  else
    echo "✗ 创建失败：$resp"
    exit 1
  fi
fi
upload_base="${upload_url%\{*}"
html_url="$(printf '%s' "$resp" | python3 -c "import json,sys; print(json.load(sys.stdin).get('html_url',''))" 2>/dev/null || true)"
echo "  ✓ Release 就绪：$html_url"

echo "▶ 3/3 上传附件"
upload_one() {
  local f="$1" ctype="$2" code af
  af="$(find_asset "$f")" || { echo "✗ 缺少附件：$f"; return 1; }
  code="$(curl -sS -o /tmp/_up.json -w '%{http_code}' -X POST \
    -H "Authorization: Bearer $TOKEN" -H "Accept: application/vnd.github+json" \
    -H "Content-Type: $ctype" \
    --data-binary "@$af" "$upload_base?name=$f")"
  if [ "$code" = "201" ]; then return 0; fi
  # 同名附件已存在 → 先删旧的后重试
  if [ "$code" = "422" ]; then
    local old_id
    old_id="$(printf '%s' "$resp" | python3 -c "
import json,sys
for a in json.load(sys.stdin).get('assets', []):
    if a['name'] == sys.argv[1]:
        print(a['id']); break
" "$f" 2>/dev/null || true)"
    if [ -n "$old_id" ]; then
      curl -sS -o /dev/null -X DELETE "${auth[@]}" "$API/repos/$REPO/releases/assets/$old_id"
      code="$(curl -sS -o /tmp/_up.json -w '%{http_code}' -X POST \
        -H "Authorization: Bearer $TOKEN" -H "Accept: application/vnd.github+json" \
        -H "Content-Type: $ctype" \
        --data-binary "@$af" "$upload_base?name=$f")"
      [ "$code" = "201" ] && return 0
    fi
  fi
  echo "  ✗ 上传失败 $f（HTTP $code）：$(head -c 400 /tmp/_up.json)"
  return 1
}

for f in "${ASSETS[@]}"; do
  case "$f" in
    *.zip)     ctype="application/zip" ;;
    *.tar.gz)  ctype="application/gzip" ;;
    *)         ctype="text/plain" ;;
  esac
  upload_one "$f" "$ctype" && echo "  ✓ 已上传 $f" || exit 1
done

rm -f /tmp/_up.json
echo
echo "✅ 发布完成：$html_url"
