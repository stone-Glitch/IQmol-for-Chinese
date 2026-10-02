# Release 手动创建包 — v3.2.3-zh_CN

> 用途：**你稍后自行在 GitHub 网页创建 Release** 时可直接复制粘贴本包内容。
> 生成：WorkBuddy ｜ 时间：2026-10-01 ｜ 仓库：`stone-Glitch/IQmol-for-Chinese`

---

## 〇、创建前须知

1. **tag 已就位**：`v3.2.3-zh_CN` 已指向最新提交 `584be17`，远端已同步。创建时直接选它。
2. **校验和已实测**：两个分发包已通过镜像下载到本地并校验；Linux 包的 SHA256/MD5 **与仓库记录逐字节一致**，证明无损。Windows 包 SHA256 为本次首算。
3. **附件已在工作区备好**（已实测校验通过，无需再下载）：
   - `/workspace/IQmol-win64-3.2.3-zh_CN.zip`（53.1 MB）
   - `/workspace/IQmol-linux-x86_64.tar.gz`（40.1 MB）← 已从临时目录固化，避免沙箱清理丢失
   - `/workspace/SHA256SUMS.txt`
4. **拿到 token 后可直接一键发布**：在 `/workspace` 执行
   ```
   GITHUB_TOKEN=ghp_xxxxxxxx bash publish_release.sh
   ```
   脚本会自动创建 Release（已存在则复用）、上传三个附件、处理同名附件覆盖，最后打印 Release 链接。
   发布说明正文取自 `/workspace/release_notes.md`（同一份内容，手动粘贴也用它）。

---

## 一、创建步骤（GitHub 网页）

1. 打开 <https://github.com/stone-Glitch/IQmol-for-Chinese/releases/new?tag=v3.2.3-zh_CN>（已预填 tag）
2. **Choose a tag** → 确认是 **`v3.2.3-zh_CN`**（已存在，勿新建）
3. **Release title** 填：

   ```
   IQmol 简体中文本地化版 v3.2.3-zh_CN
   ```

4. **Describe this release** → 粘贴 `/workspace/release_notes.md` 的全文（= 下方「第三节」内容）
5. **Attach binaries** → 把 `/workspace` 下的 `IQmol-win64-3.2.3-zh_CN.zip`、`IQmol-linux-x86_64.tar.gz`、`SHA256SUMS.txt` 拖进上传框
6. 点 **Publish release**

---

## 二、附件清单

| 附件 | 仓库内路径 | 大小 | SHA256 |
|---|---|---|---|
| `IQmol-win64-3.2.3-zh_CN.zip` | 仓库根 | 55,665,466 字节（53.1 MB） | `d064a6bb98d48bb189e15ff7c95cd61ae2b6bb093fff6945d33ea665e0ba0580` |
| `IQmol-linux-x86_64.tar.gz` | `submodules-package/linux-build/` | 42,034,132 字节（40.1 MB） | `bee6dfec94ec566eb41a3780c3575e2093ff0c11193d2a5deca2c4b7065e2ded` |
| `SHA256SUMS.txt` | （需新建，内容见下） | <1 KB | — |

> ✅ **校验可靠性**：两个包已通过镜像（ghfast.top）下载并实测。
> Linux 包 **SHA256 与 MD5 均与仓库 `使用说明.md` 记录值逐字节一致**（MD5 = `24a6adcd24c0229c4d5f898c71f98698`），证明下载无损。

> 可选：子模块离线包 `IQmol-submodules.tar.gz`（75,761,144 字节 / 72.3 MB）**体积大**，
> 建议**不作为 Release 附件**，仍放在仓库 `submodules-package/` 内（README 已有指引）。

### `SHA256SUMS.txt` 内容（可直接新建此文件后上传）

```text
d064a6bb98d48bb189e15ff7c95cd61ae2b6bb093fff6945d33ea665e0ba0580  IQmol-win64-3.2.3-zh_CN.zip
bee6dfec94ec566eb41a3780c3575e2093ff0c11193d2a5deca2c4b7065e2ded  IQmol-linux-x86_64.tar.gz
```

---

## 三、发布说明全文（粘贴到 Describe this release）

<!-- ↓↓↓ 从下一行开始整段复制 ↓↓↓ -->

# IQmol 简体中文本地化版 v3.2.3-zh_CN

> 基于上游 [nutjunkie/IQmol3](https://github.com/nutjunkie/IQmol3) **v3.2.3**（commit `94356ab`）的简体中文本地化衍生版本。
> 汉化仅覆盖**界面 / 帮助 / Q-Chem 关键词文案**；上游的计算功能、SSH 实现、文件解析未做改动。

## ✨ 本版亮点

- **界面全量汉化**：`translations/zh_CN.ts` 共 **2112 条**翻译、**153 个 context**、`0 unfinished`；构建时由 CMake 自动调用 `lrelease` 生成 `zh_CN.qm`。
- **Windows 预编译包**：解压即用，含 `IQmol.exe`、Qt 运行库与 900+ 依赖 DLL，无需自行编译。
- **Linux 预编译包**：`x86_64` 解压即用，自带 Qt5 / OpenBabel / OpenMesh / QGLViewer 等全部依赖，不污染系统。
- **中文用户手册**：仓库 `doc/IQmolUserGuide.pdf`（34 页，全中文）。
- **中文界面截图集**：`dialog_screenshots/`（顶层核心对话框 + 全量 81 个 `.ui` + 多卡片界面）。
- **国内网络友好**：提供子模块离线包，跳过 `git submodule update` 的断连噩梦。

## 📦 下载

| 附件 | 大小 | 适用平台 | 说明 |
|---|---|---|---|
| `IQmol-win64-3.2.3-zh_CN.zip` | ~53 MB | Windows 64 位 | 解压即用，含全部运行库 |
| `IQmol-linux-x86_64.tar.gz` | ~40 MB | Linux x86_64 | 解压即用（`glibc 2.35+`） |
| `SHA256SUMS.txt` | <1 KB | — | 上述文件的 SHA256 校验和 |

> 子模块离线包（源码构建用）与更多说明见仓库 [`submodules-package/`](https://github.com/stone-Glitch/IQmol-for-Chinese/tree/main/submodules-package)。

### 校验下载完整性

```bash
# Linux / macOS
sha256sum -c SHA256SUMS.txt

# Windows PowerShell
Get-FileHash .\IQmol-win64-3.2.3-zh_CN.zip -Algorithm SHA256
```

## 🚀 快速开始

**Windows**

1. 解压 `IQmol-win64-3.2.3-zh_CN.zip`；
2. 双击 `IQmol.exe` 启动。免安装，不写注册表。

**Linux**

```bash
tar xzf IQmol-linux-x86_64.tar.gz
cd IQmol-linux-x86_64
./run.sh                 # 启动
./run.sh 分子文件.xyz     # 启动并打开指定文件
```

## 📖 文档

| 你想做什么 | 看这里 |
|---|---|
| 编译（Windows / Linux / macOS）、部署、排错 | [`docs/构建与打包/构建与部署指南.md`](https://github.com/stone-Glitch/IQmol-for-Chinese/blob/main/docs/构建与打包/构建与部署指南.md) |
| 了解目录结构、汉化文件在哪 | [`docs/仓库结构.md`](https://github.com/stone-Glitch/IQmol-for-Chinese/blob/main/docs/仓库结构.md) |
| 全部文档索引 | [`docs/README.md`](https://github.com/stone-Glitch/IQmol-for-Chinese/blob/main/docs/README.md) |
| 参与贡献 / 报告翻译问题 | [CONTRIBUTING.md](https://github.com/stone-Glitch/IQmol-for-Chinese/blob/main/CONTRIBUTING.md) |
| 报告安全漏洞（请勿公开） | [SECURITY.md](https://github.com/stone-Glitch/IQmol-for-Chinese/blob/main/SECURITY.md) |

## ⚠️ 已知问题（源自上游）

> 本节所列问题**源自 IQmol 上游本身**，并非本汉化引入。完整列表见 [README](https://github.com/stone-Glitch/IQmol-for-Chinese/blob/main/README.md#已知问题源自上游)。

- **部分运行期字符串仍为英文**：上游源码中未被 `tr()` 包裹的字符串无法被翻译体系识别，会保持英文显示。
- **帮助文档部分内嵌截图为英文**：`doc/IQmolUserGuide.*` 的部分配图为上游英文截图，汉化尚未重渲染（计划下个版本处理）。
- **MinGW-w64 为唯一验证的 Windows 工具链**：MSVC 路径未验证、未支持。

## 📄 许可

IQmol 遵循 **GNU General Public License v3**。本包为 GPL 衍生作品，同样遵循 **GPLv3**。
第三方依赖许可证清单见 [`THIRD_PARTY_LICENSES.md`](https://github.com/stone-Glitch/IQmol-for-Chinese/blob/main/THIRD_PARTY_LICENSES.md)。

> Qt 静态 / 捆绑说明：Windows 包为「双击即用」采用捆绑 / 静态链接 Qt，请按 Qt LGPL-3.0 或 GPL 条款评估合规。

## 🙏 致谢

- 上游作者 **Andrew Gilbert** 及 [nutjunkie/IQmol3](https://github.com/nutjunkie/IQmol3) 项目
- 所有第三方库作者（OpenBabel、OpenMesh、libQGLViewer、Qt 等，详见 `THIRD_PARTY_LICENSES.md`）

<!-- ↑↑↑ 复制到上一行结束 ↑↑↑ -->

---

## 四、发布后可选（后续升级路径）

若希望**把这些大文件移出 git 仓库**（当前约 146 MB 在 `submodules-package/`）：

1. Release 发布后，附件有了稳定链接；
2. 在仓库里把大 `.tar.gz` / `.zip` 从 git 移除（`git rm --cached`），加进 `.gitignore`；
3. 更新 `submodules-package/使用说明.md` 与 `README.md`，把「按文件下载」链接改指向 **Release 附件**；
4. 这一步会改变工作树内容（不重写历史），需单独一次提交，建议届时再做。

> ⚠️ 注意：`git rm` 大文件后，历史中的 blob **仍然存在**，仓库 `.git` 体积不会立刻下降；
> 彻底瘦身需 `git filter-repo` 重写历史（破坏性，谨慎）。当前「轻整理」策略下**暂不做**。
