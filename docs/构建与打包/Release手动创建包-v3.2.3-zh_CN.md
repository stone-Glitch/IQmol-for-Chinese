# Release 手动创建包 — v3.2.3-zh_CN

> 用途：**你稍后自行在 GitHub 网页创建 Release** 时可直接照此操作。
> 仓库：`stone-Glitch/IQmol-for-Chinese` ｜ 关联 tag：`v3.2.3-zh_CN`

---

## 〇、创建前须知

1. **tag 已就位**：`v3.2.3-zh_CN` 为本次发布 tag，创建时直接选它（请勿新建）。
2. **校验和已实测**：两个分发包已通过镜像下载到本地并校验；Linux 包的 SHA256/MD5 与仓库记录逐字节一致，证明无损。Windows 包 SHA256 为本次首算（见下方附件清单）。
3. **附件准备**：`IQmol-win64-3.2.3-zh_CN.zip`、`IQmol-linux-x86_64.tar.gz`、`SHA256SUMS.txt`
   三个文件来自 GitHub Release 附件（或本地归档）；发布前请确保已下载到本次操作的工作目录。
4. **自动发布（可选）**：在脚本所在目录执行

   ```
   GITHUB_TOKEN=ghp_xxxxxxxx bash publish_release.sh
   ```

   脚本会自动创建 Release（已存在则复用）、上传三个附件、处理同名附件覆盖，最后打印 Release 链接。
   发布说明正文取自仓库 `docs/构建与打包/release_notes.md`（唯一真源；见第三节）。

---

## 一、创建步骤（GitHub 网页）

1. 打开 <https://github.com/stone-Glitch/IQmol-for-Chinese/releases/new?tag=v3.2.3-zh_CN>（已预填 tag）
2. **Choose a tag** → 确认是 **`v3.2.3-zh_CN`**（已存在，勿新建）
3. **Release title** 填：

   ```
   IQmol 简体中文本地化版 v3.2.3-zh_CN
   ```

4. **Describe this release** → 粘贴 `docs/构建与打包/release_notes.md` 的全文（见「第三节」说明）
5. **Attach binaries** → 把三个附件拖进上传框
6. 点 **Publish release**

---

## 二、附件清单

| 附件 | 仓库内路径 | 大小 | SHA256 |
|---|---|---|---|
| `IQmol-win64-3.2.3-zh_CN.zip` | 仓库根 | 55,665,466 字节（53.1 MB） | `d064a6bb98d48bb189e15ff7c95cd61ae2b6bb093fff6945d33ea665e0ba0580` |
| `IQmol-linux-x86_64.tar.gz` | `submodules-package/linux-build/` | 42,034,132 字节（40.1 MB） | `bee6dfec94ec566eb41a3780c3575e2093ff0c11193d2a5deca2c4b7065e2ded` |
| `SHA256SUMS.txt` | （需新建，内容见下） | <1 KB | — |

> ✅ **校验可靠性**：两个包已通过镜像（ghfast.top）下载并实测。
> Linux 包 **SHA256 与 MD5 均与仓库 `submodules-package/linux-build/使用说明.md` 记录值逐字节一致**（MD5 = `24a6adcd24c0229c4d5f898c71f98698`），证明下载无损。

> 可选：子模块离线包 `IQmol-submodules.tar.gz`（75,761,144 字节 / 72.3 MB）**体积大**，
> 建议**不作为 Release 附件**，仍放在仓库 `submodules-package/` 内（README 已有指引）。

### `SHA256SUMS.txt` 内容（可直接新建此文件后上传）

```text
d064a6bb98d48bb189e15ff7c95cd61ae2b6bb093fff6945d33ea665e0ba0580  IQmol-win64-3.2.3-zh_CN.zip
bee6dfec94ec566eb41a3780c3575e2093ff0c11193d2a5deca2c4b7065e2ded  IQmol-linux-x86_64.tar.gz
```

---

## 三、发布说明正文

> **正文不在此内嵌**（避免与源文件不同步）。请直接复制仓库源文件
> **`docs/构建与打包/release_notes.md`** 的全文，粘贴到「Describe this release」。

该文件是发布说明的**唯一真源**，两种发布方式都依赖它：

- **手动发布（本指南）**：复制其全文粘贴到 Release 描述框；
- **自动发布（`scripts/publish_release.sh`）**：脚本读取同目录下的 `release_notes.md` 作为正文，
  因此用脚本发布时需把该文件与三个附件一起放到脚本所在目录（或从仓库复制出来）。

---

## 四、发布后可选（后续升级路径）

若希望**把这些大文件移出 git 仓库**（当前约 147 MB 在 `submodules-package/`）：

1. Release 发布后，附件有了稳定链接；
2. 在仓库里把大 `.tar.gz` / `.zip` 从 git 移除（`git rm --cached`），加进 `.gitignore`；
3. 更新 `submodules-package/使用说明.md` 与 `README.md`，把「按文件下载」链接改指向 **Release 附件**；
4. 这一步会改变工作树内容（不重写历史），需单独一次提交，建议届时再做。

> ⚠️ 注意：`git rm` 大文件后，历史中的 blob **仍然存在**，仓库 `.git` 体积不会立刻下降；
> 彻底瘦身需 `git filter-repo` 重写历史（破坏性，谨慎）。当前「轻整理」策略下**暂不做**。
