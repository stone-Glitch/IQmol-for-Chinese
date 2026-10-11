# 重链接与合规说明（Relinking Notice）

> 适用对象：本仓库分发的 **IQmol 简体中文版** 及其 Windows / Linux / macOS 分发包。
> 关联文档：[THIRD_PARTY_LICENSES.md](THIRD_PARTY_LICENSES.md)
> 维护者：@stone-Glitch ｜ 最后更新：2026-10-11

本软件在构建与分发时链接了 **Qt 5**（QtCore / Gui / Widgets / OpenGL / Sql /
PrintSupport / Xml + LinguistTools），其许可为 **LGPL-3.0-only**。依据 LGPL-3.0
第 4 条，当以 LGPL 方式合规时，接收者必须能够**用其修改后的 Qt 库重新链接（或替换）**
本程序。本说明给出实现该权利的两条可行路径与源码获取要约。

---

## 一、所用 Qt 版本

| 平台 | Qt 版本 | 备注 |
|---|---|---|
| macOS | 5.15.13_1 | `scripts/mac_deploy.sh` 锁定 `qt@5/5.15.13_1` |
| Linux | 5.15.x（随发行版，如 Ubuntu 24.04 的 `qtbase5-dev`） | 由包管理器提供 |
| Windows | 5.15.x（MinGW-w64 构建） | `scripts/build_windows.sh` 使用的 MinGW Qt |

> 若你的实际构建使用了不同小版本，请以构建所链接的 Qt 库版本及其随附许可证为准。

---

## 二、Qt 源码获取要约（书面要约）

依据 LGPL-3.0 §4(d)(1)，提供以下获取 Qt 适用版本源码的途径：

- **官方源码镜像**：<https://download.qt.io/archive/qt/5.15/5.15.13/single/>
- **Qt 代码仓库**：<https://code.qt.io/cgit/qt/qt5.git>（按上述版本 tag 检出）
- **完整 LGPL-3.0 文本**：<https://www.gnu.org/licenses/lgpl-3.0.txt>

如需本仓库**特定构建**对应的 Qt 修改/补丁，请在本仓库提交 Issue 索取；本仓库未对 Qt 自身打补丁，仅使用上游原版 Qt。

---

## 三、重链接路径（二选一）

### 路径 A（推荐）：动态链接 + 随包附 Qt 动态库

将 Qt 以动态库形式提供，接收者即可直接替换 `.so`（Linux）/ `.dylib`（macOS）/
`.dll`（Windows）来使用其修改后的 Qt，无需重新编译 IQmol。

- Windows 包已包含 Qt 运行 DLL（采用 DLL 部署），满足"可替换"要求；
- 重新构建以获取最新链接产物的命令见 [docs/构建与打包/构建与部署指南.md](docs/构建与打包/构建与部署指南.md)
  与 `scripts/build_windows.sh` / `scripts/mac_deploy.sh`。

### 路径 B：提供目标文件（.o / .obj）重链接材料

若采用静态链接分发，应随包提供应用程序的目标文件（object files），使接收者能与
修改后的 Qt 静态库重新链接。本仓库在 `main` 分支提供**完整源码树**，等价地满足
"可重新构建/重链接"要求——接收者可按上述构建指南自行编译出目标文件并完成重链接。

> 当前 Windows 包为便于「双击即用」默认采用静态/捆绑方式；如希望以纯 LGPL 方式合规，
> 采用路径 A（改为动态链接并随包附 Qt DLL）即可，无需额外提供目标文件。

---

## 四、反汇编与重链接权限制

LGPL-3.0 不禁止对二进制进行必要反汇编以达成重链接/调试目的（§4 的反向工程例外），
但不得借此获取 Qt 以外的本程序专有逻辑。本仓库分发的程序本身即为开源（GPL-3.0），
不存在此类限制的实际障碍。

---

## 五、免责声明

本说明为合规操作的**可执行指引**，不构成法律意见。如对开源合规有更严格的法务要求，
建议咨询熟悉 GPL/LGPL 的专业人士。
