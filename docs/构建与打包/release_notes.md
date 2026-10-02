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
