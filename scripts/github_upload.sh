#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# 通过 GitHub REST API 上传 / 更新文件
# 用途：沙箱 SSH 不通（或不想用 git）时，把文件直接推到 GitHub 仓库
#
# 用法:
#   export GITHUB_TOKEN="ghp_xxxxxxxxxxxxxxxxxxxx"
#   ./github_upload.sh <本地文件> [仓库内目标路径] [分支] [owner/repo]
#
# 示例:
#   ./github_upload.sh ./build_windows.sh scripts/build_windows.sh
#   ./github_upload.sh ./报告.md doc/报告.md master stone-Glitch/IQmol-for-Chinese
#
# 依赖: curl, base64, python3（拼 JSON 用，避免 shell 转义踩坑）
# ---------------------------------------------------------------------------
set -u

TOKEN="${GITHUB_TOKEN:-}"
LOCAL_FILE="${1:-}"
REMOTE_PATH="${2:-}"
BRANCH="${3:-master}"
REPO="${4:-stone-Glitch/IQmol-for-Chinese}"

# ===== 参数校验 =====
if [ -z "$TOKEN" ]; then
  echo "ERROR: 未设置 GITHUB_TOKEN" >&2
  echo "       创建令牌: https://github.com/settings/tokens  (勾选 repo 权限)" >&2
  echo "       然后执行: export GITHUB_TOKEN=\"ghp_xxx\"" >&2
  exit 1
fi
if [ -z "$LOCAL_FILE" ] || [ -z "$REMOTE_PATH" ]; then
  echo "ERROR: 用法: $0 <本地文件> [仓库内路径] [分支] [owner/repo]" >&2
  exit 1
fi
if [ ! -f "$LOCAL_FILE" ]; then
  echo "ERROR: 本地文件不存在: $LOCAL_FILE" >&2
  exit 1
fi

# Contents API 单文件上限 100MB，base64 后还会膨胀约 33%，
# 所以原始文件建议控制在 70MB 以内；超了请改用 Release 附件。
SIZE=$(stat -c %s "$LOCAL_FILE" 2>/dev/null || stat -f %z "$LOCAL_FILE")
if [ "$SIZE" -gt 73400320 ]; then
  echo "ERROR: 文件 $((SIZE/1048576))MB 超过 Contents API 安全上限(70MB)。" >&2
  echo "       请改用 Release 附件上传，见文档「六、大文件方案」。" >&2
  exit 1
fi

API="https://api.github.com/repos/$REPO/contents/$REMOTE_PATH"

echo "==> 上传 $(basename "$LOCAL_FILE") ($((SIZE/1024)) KB) → $REPO:$BRANCH/$REMOTE_PATH"

# ===== 1. 若文件已存在，先取它的 sha（更新文件必须带 sha，否则 422）=====
SHA="null"
EXISTING=$(curl -s -H "Authorization: token $TOKEN" \
                -H "Accept: application/vnd.github+json" \
                "$API?ref=$BRANCH")
if echo "$EXISTING" | grep -q '"sha"'; then
  SHA=$(echo "$EXISTING" | python3 -c 'import sys,json; print(json.load(sys.stdin)["sha"])' 2>/dev/null)
  echo "    文件已存在，将更新（sha=${SHA:0:12}...）"
else
  echo "    新文件，将创建"
fi

# ===== 2. base64 编码并用 python 拼 JSON（避免内容里有引号/换行把 shell 搞崩）=====
PAYLOAD=$(python3 - "$LOCAL_FILE" "$BRANCH" "$SHA" <<'PY'
import sys, base64, json
path, branch, sha = sys.argv[1], sys.argv[2], sys.argv[3]
with open(path, "rb") as f:
    content = base64.b64encode(f.read()).decode("ascii")
d = {"message": f"chore: update {path.split('/')[-1]} via API",
     "content": content,
     "branch": branch}
if sha != "null":
    d["sha"] = sha
print(json.dumps(d))
PY
)

# ===== 3. PUT 上传 =====
RESP=$(curl -s -w "\n%{http_code}" -X PUT \
  -H "Authorization: token $TOKEN" \
  -H "Accept: application/vnd.github+json" \
  -H "Content-Type: application/json" \
  --data-binary "$PAYLOAD" \
  "$API")

HTTP_CODE=$(echo "$RESP" | tail -1)
BODY=$(echo "$RESP" | sed '$d')

case "$HTTP_CODE" in
  200|201)
    echo "==> 成功 (HTTP $HTTP_CODE)"
    echo "$BODY" | python3 -c 'import sys,json; d=json.load(sys.stdin); print("    提交:", d["commit"]["sha"][:12]); print("    地址:", d["content"]["html_url"])' 2>/dev/null
    ;;
  401)
    echo "ERROR: 令牌无效或已过期 (HTTP 401)" >&2
    echo "       检查 GITHUB_TOKEN 是否正确、是否被撤销" >&2
    exit 1 ;;
  403)
    echo "ERROR: 权限不足或触发速率限制 (HTTP 403)" >&2
    echo "$BODY" | python3 -c 'import sys,json; print("      ", json.load(sys.stdin).get("message",""))' 2>/dev/null
    exit 1 ;;
  404)
    echo "ERROR: 仓库不存在，或令牌无该仓库写权限 (HTTP 404)" >&2
    echo "       私有仓库需要勾选 repo 权限；组织仓库可能需 SSO 授权" >&2
    exit 1 ;;
  422)
    echo "ERROR: 校验失败 (HTTP 422) —— 常见于 sha 不匹配（文件被别人改过）" >&2
    echo "$BODY" | python3 -c 'import sys,json; print("      ", json.load(sys.stdin).get("message",""))' 2>/dev/null
    exit 1 ;;
  *)
    echo "ERROR: 上传失败 (HTTP $HTTP_CODE)" >&2
    echo "$BODY" | head -c 500 >&2
    exit 1 ;;
esac
