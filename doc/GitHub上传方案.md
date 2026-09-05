# 沙箱受限环境下把文件上传到 GitHub

**日期**: 2026-09-05
**场景**: WorkBuddy 沙箱（Ubuntu 22.04）无法用常规方式推送 GitHub 时的可行通道
**实测环境**: 本项目仓库 `stone-Glitch/IQmol-for-Chinese`

---

## 〇、一句话结论

沙箱里 **`github.com` 网页端和 SSH-443 不通，但 `api.github.com` 和 SSH-22 通**。
所以有两条活路：

1. **首选**：把 SSH 配到 **22 端口**，正常 `git push`（本文已用此法成功推送 3 个提交）。
2. **备选**：走 **GitHub REST API**（`api.github.com`），用脚本直接上传文件，不依赖 git。

---

## 一、沙箱网络实测数据

以下是 2026-09-05 在沙箱内逐条实测的结果，不是猜测：

| 通道 | 地址 | 结果 | 说明 |
|------|------|------|------|
| HTTPS | `api.github.com` | ✅ HTTP 200 | **REST API 完全可用** |
| SSH | `ssh.github.com:22` | ✅ 认证成功 | 返回 `Hi stone-Glitch! You've successfully authenticated` |
| HTTPS | `codeload.github.com` | ⚠️ HTTP 301 | 下载 tarball 可能可用 |
| SSH | `ssh.github.com:443` | ❌ 连接被关 | 被网络策略掐断 |
| HTTPS | `github.com` | ❌ 失败 | 网页端 / git-over-https 不走 |
| HTTPS | `uploads.github.com` | ❌ HTTP 000 | Release 附件**不可用** |
| HTTPS | `objects.githubusercontent.com` | ❌ HTTP 000 | Git LFS **不可用** |
| HTTPS | `raw.githubusercontent.com` | ❌ HTTP 000 | 读原始文件不可用 |

**关键推论**：

- `git push` 走的是 `github.com`，所以**默认不通**；但只要把 SSH 指向 `ssh.github.com:22` 就能通。
- 大文件方案里的 Release 附件和 LFS **都用不了**（对应域名不通），这是硬约束。

---

## 二、方案 A：SSH over 22（首选）

### 2.1 为什么之前不通

`~/.ssh/config` 里如果写的是 `Port 443`，就会撞上被掐断的通道，表现为：

```
Connection closed by 198.18.0.10 port 443
fatal: Could not read from remote repository.
```

这个报错极具误导性——看起来像权限问题、仓库不存在，实际是**端口被网络策略拦截**。

### 2.2 正确配置

编辑 `~/.ssh/config`：

```
Host github.com
    HostName ssh.github.com
    Port 22
    User git
    IdentityFile ~/.ssh/id_ed25519
    StrictHostKeyChecking accept-new
```

> 关键点：`Port 22`，**不是 443**。GitHub 官方文档确实推荐 443 作为穿透防火墙的备选，但在本沙箱里恰好相反。

### 2.3 验证

```bash
ssh -T git@github.com
```

看到 `Hi <用户名>! You've successfully authenticated` 就成了。

### 2.4 推送

```bash
git push chinese master
```

---

## 三、方案 B：GitHub REST API（不依赖 git）

适合：只想丢几个文件上去、不想处理 git 历史，或者 SSH 也断了的时候。

### 3.1 拿到令牌

1. 打开 https://github.com/settings/tokens
2. **Generate new token (classic)**
3. 权限勾选 **`repo`**（私有仓库必须；公开仓库上传也需要写权限）
4. 生成后复制（只显示一次）

```bash
export GITHUB_TOKEN="ghp_xxxxxxxxxxxxxxxxxxxx"
```

### 3.2 用现成脚本上传

随本文档提供 `github_upload.sh`：

```bash
chmod +x github_upload.sh
export GITHUB_TOKEN="ghp_xxx"

# 上传单个文件
./github_upload.sh ./build_windows.sh scripts/build_windows.sh

# 指定分支和仓库
./github_upload.sh ./报告.md doc/报告.md master stone-Glitch/IQmol-for-Chinese
```

脚本已经处理好的细节：

- 自动检测文件是否已存在，**存在则带 `sha` 更新**（不带 sha 会返回 422）
- 用 Python 拼 JSON，避免文件内容里的引号 / 换行搞崩 shell
- 区分 401 / 403 / 404 / 422 并给出人话提示
- 超过 70 MB 直接拒绝并提示改用 Release

### 3.3 手写版（不想用脚本时）

```bash
# 新文件
CONTENT=$(base64 -w 0 ./myfile.txt)
curl -X PUT \
  -H "Authorization: token $GITHUB_TOKEN" \
  -H "Accept: application/vnd.github+json" \
  -d "{\"message\":\"add myfile\",\"content\":\"$CONTENT\",\"branch\":\"master\"}" \
  https://api.github.com/repos/OWNER/REPO/contents/path/to/myfile.txt

# 更新已有文件：先取 sha
SHA=$(curl -s -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/OWNER/REPO/contents/path/to/myfile.txt?ref=master \
  | python3 -c 'import sys,json; print(json.load(sys.stdin)["sha"])')

# 再 PUT，JSON 里带上 "sha":"$SHA"
```

### 3.4 限制

| 项目 | 限制 |
|------|------|
| 单文件大小 | 100 MB（base64 后膨胀 33%，**实操建议 ≤ 70 MB**） |
| 速率 | 认证用户 5000 次/小时 |
| 单次提交 | 建议 ≤ 100 个文件 |

---

## 四、方案 C：Git Data API（无 git 也能提交）

想完整同步提交历史、但 `git push` 不通时的进阶做法。原理是手工拼 git 对象：

```
blob（文件内容）→ tree（目录结构）→ commit（提交）→ ref（移动分支指针）
```

```bash
# 1. 创建 blob
BLOB_SHA=$(curl -s -X POST \
  -H "Authorization: token $GITHUB_TOKEN" \
  -d "{\"content\":\"$(base64 -w 0 file.txt)\",\"encoding\":\"base64\"}" \
  https://api.github.com/repos/OWNER/REPO/git/blobs \
  | python3 -c 'import sys,json; print(json.load(sys.stdin)["sha"])')

# 2. 建 tree（base_tree 用当前 HEAD，实现增量修改）
TREE_SHA=$(curl -s -X POST \
  -H "Authorization: token $GITHUB_TOKEN" \
  -d "{\"base_tree\":\"$BASE_TREE\",\"tree\":[{\"path\":\"file.txt\",\"mode\":\"100644\",\"type\":\"blob\",\"sha\":\"$BLOB_SHA\"}]}" \
  https://api.github.com/repos/OWNER/REPO/git/trees \
  | python3 -c 'import sys,json; print(json.load(sys.stdin)["sha"])')

# 3. 建 commit
COMMIT_SHA=$(curl -s -X POST \
  -H "Authorization: token $GITHUB_TOKEN" \
  -d "{\"message\":\"update\",\"tree\":\"$TREE_SHA\",\"parents\":[\"$PARENT_SHA\"]}" \
  https://api.github.com/repos/OWNER/REPO/git/commits \
  | python3 -c 'import sys,json; print(json.load(sys.stdin)["sha"])')

# 4. 移动分支指针
curl -X PATCH \
  -H "Authorization: token $GITHUB_TOKEN" \
  -d "{\"sha\":\"$COMMIT_SHA\"}" \
  https://api.github.com/repos/OWNER/REPO/git/refs/heads/master
```

> 麻烦，且每次只能改有限个文件。**只在方案 A、B 都不可用时才用这个。**

---

## 五、方案 D：兜底交付（无网络也能用）

两条都不通时的最后手段，也是本项目前期实际在用的办法：

1. 在沙箱里把准备好的文件放到 `/workspace/`
2. 通过对话界面的文件卡片交付给用户
3. 用户手动下载，覆盖到本地对应位置

**优点**：零依赖，100% 可靠。
**缺点**：文件一多就繁琐，且无法同步 git 历史（用户本地不是 git 仓库时尤其麻烦）。

---

## 六、大文件方案（本项目 73 MB 子模块包）

这是本项目的**硬伤**，必须说清楚：

| 方案 | 可行性 | 原因 |
|------|--------|------|
| Contents API | ⚠️ 仅 ≤70 MB | 100 MB 硬上限 |
| Release 附件 | ❌ 不可用 | `uploads.github.com` 不通（HTTP 000） |
| Git LFS | ❌ 不可用 | `objects.githubusercontent.com` 不通 |
| 直接进 git 仓库 | ⚠️ 不推荐 | 会让仓库体积暴涨，拖垮 clone |

**本项目采用的解法**：把 73 MB 的子模块离线包放在**孤儿分支** `submodules-package` 上，与主分支 `master` 完全隔离。这样：

- `git clone` 主分支的人不会被 73 MB 拖累；
- 需要离线包的人单独拉该分支：

```bash
git clone -b submodules-package --single-branch \
  https://github.com/stone-Glitch/IQmol-for-Chinese.git pkg
```

> 附加好处：孤儿分支不共享提交历史，不会污染主分支的 `git log`。

---

## 七、排查清单

按顺序自查，能省掉 90% 的瞎猜：

```bash
# 1. SSH 到底通不通（注意看返回，别只看红字）
ssh -T git@github.com

# 2. SSH 配置用的哪个端口
grep -A3 "Host github.com" ~/.ssh/config

# 3. API 通不通
curl -s -o /dev/null -w "%{http_code}\n" https://api.github.com

# 4. 令牌有没有效
curl -s -H "Authorization: token $GITHUB_TOKEN" https://api.github.com/user \
  | python3 -c 'import sys,json; d=json.load(sys.stdin); print("用户:", d.get("login") or d.get("message"))'

# 5. 远程分支实际指向哪（别信本地记忆）
git ls-remote <remote>
```

### 常见报错对照表

| 报错 | 真实原因 | 处理 |
|------|----------|------|
| `Connection closed by ... port 443` | SSH 走了被掐的 443 | `~/.ssh/config` 改 `Port 22` |
| `Could not read Username for 'https://...'` | HTTPS 方式但无凭据 | 换 SSH，或配 PAT |
| `Permission denied (publickey)` | 密钥没加 / 加错 | `ssh-add -l` 检查，或指定 `IdentityFile` |
| API 返回 `401` | 令牌无效或过期 | 重新生成 PAT |
| API 返回 `404` | 仓库名错，或 PAT 缺 `repo` 权限 | 检查权限勾选 |
| API 返回 `422` | 更新文件时 sha 不对 | 重新 GET 取最新 sha |
| `HTTP 000` | 域名根本连不上 | 换方案，别死磕 |

---

## 八、本次顺带修掉的一个真问题

排查过程中发现远程 **`main` 分支落后 `master` 整整 5 个提交**：

```
分叉点:      412d088
master:      777ba77  (领先 5 个提交)
main:        412d088  (0 个独有提交)
远程 HEAD:   → main
```

后果很实际：**默认分支 `main` 是旧快照，不含 `scripts/build_windows.sh`**，
这正是用户在自己机器上 `bash ./scripts/build_windows.sh` 报
`No such file or directory` 的根因之一。

因为 `main` 没有任何独有提交，可以直接快进，零风险：

```bash
git push chinese master:main
```

现已完成，`main` / `master` / `HEAD` 三者统一指向 `777ba77`。

> **教训**：多分支仓库要定期检查 `git ls-remote` 看各分支实际指向，
> 别默认「推送了 master 就等于所有人都能拿到」。默认分支是哪个，才是用户真正会拿到的东西。
