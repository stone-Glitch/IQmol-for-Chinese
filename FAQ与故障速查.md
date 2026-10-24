# FAQ 与故障速查

> README 里只放最关键的几条，完整版在这里。README 顶部链接过来即可。
> **这份文档的价值不在于全面，而在于每条都给出"症状 → 原因 → 解法"的直连路径**——
> 用户遇到问题时是在找答案，不是在读文章。

---

## 一、先回答：我该不该用这个？

**Q：我不会编译，能用吗？**
能。到 [Releases](https://github.com/stone-Glitch/IQmol-for-Chinese/releases) 下载对应平台的包，
Windows 解压后直接运行 `IQmol.exe`，Linux 解压后 `./run.sh`。不需要安装 Qt，不需要编译。

**Q：和官方 iqmol.org 的二进制有什么区别？**
界面是中文，附带 34 页中文手册。IQmol 本身的功能完全一致——本仓库不改上游功能。

**Q：我只用 Gaussian / ORCA / GAMESS，用这个合适吗？**
不太合适。IQmol 是**专门面向 Q-Chem** 的前端。多程序支持请看 [Gabedit](https://gabedit.sourceforge.net/)；
建模为主请看 [Avogadro2](https://avogadro.cc/)。

**Q：能算大分子 / 蛋白质吗？**
不是它的强项。它是小分子与量子化学工作流工具，大体系轨迹分析请用 [VMD](https://www.ks.uiuc.edu/Research/vmd/)。

**Q：中文版会跟上游同步吗？**
会。仓库锁定了上游基线 tag，并提供两条迁移路线（`sync_upstream.sh` / `migrate_to_upstream.sh`）。
每次上游发新版会同步并重新验证。

---

## 二、故障速查表

> 按**你看到的症状**查，不要按章节读。

### 构建阶段

| 症状 | 原因 | 解法 |
|---|---|---|
| `Could not find a package configuration file provided by Qt5` | `CMAKE_PREFIX_PATH` 没指向含 `Qt5Config.cmake` 的目录 | 指向 Qt5 安装下的 `lib/cmake`（不是 Qt5 根目录）。Windows 典型路径：`C:\Qt\5.15.2\mingw81_64\lib\cmake` |
| CMake 报 `Compatibility with CMake < 3.5 has been removed` | 用了 CMake 4.x | 换 CMake 3.x（推荐 3.31）。见下方"关于 CMake 4.x" |
| `git submodule` 卡在 6% 或 `Failed to connect to github.com:443` | 国内网络 | 用离线子模块包（`IQmol-submodules.tar.gz`），不要硬等 |
| OpenBabel configure 报 `FATAL_ERROR`（maeparser / coordgenlibs / rapidjson） | OpenBabel 编译期联网拉依赖失败 | 解压 `IQmol-openbabel-deps.tar.gz` 到 `modules/openbabel/` |
| OpenBabel 报 `not an existing directory` 或 `No SOURCES given to target: pubchem / xmlformat` | 子模块包缺文件（libinchi、test、formats/xml、formats/json） | 解压 `IQmol-openbabel-fix.tar.gz` + `IQmol-openbabel-formats-fix.tar.gz` |
| OpenBabel 报 `ADD_CUSTOM_TARGET(uninstall)` 与 yaml-cpp 重名（CMP0002） | 目标重名冲突 | 同上，补丁包已给 uninstall 加重名保护 |
| **补丁打完又被覆盖回去** | **解压顺序错了** | **顺序必须是：先完整子模块包 → 再打两个补丁包。** 重新解压完整包会把 `openbabel/CMakeLists.txt` 覆盖回未修版 |
| 深层目录解压失败 | Windows 260 字符路径上限 | 仓库放短路径，如 `D:\IQmol`，路径不要含中文和空格 |
| 解压后文件数量明显偏少 | 用了 7-Zip / 360 压缩解 `.tar.gz` | **必须用 MINGW64 终端的 `tar`**。图形工具会静默丢文件，且常只解出中间层 `.tar` |

### 部署与启动阶段

| 症状 | 原因 | 解法 |
|---|---|---|
| 编译成功但启动报 `could not find or load the Qt platform plugin "windows"` | 没跑部署脚本 | 执行 `bash ./scripts/deploy_windows.sh` |
| 启动后文件格式识别异常 / 无法读取分子 | OpenBabel 数据或插件未就位 | 同上，跑部署脚本 |
| 程序能启动但界面是英文 | `zh_CN.qm` 未生成或未加载 | 见下条 |
| 只有从包根目录启动才是中文，换目录就变英文 | 旧包 qm 路径问题 | 新包已修复（qm 同时放包根 `translations/` 与 `bin/translations/`）。仍有问题请报 issue |
| 界面显示方框 / 乱码 | 缺中文字体 | Linux 安装 `fonts-wqy-zenhei` 或 `fonts-noto-cjk` |

### 翻译相关

| 症状 | 原因 | 解法 |
|---|---|---|
| 改了源码里的文字，界面没变 | 没加 `tr()`，或加了没跑 `lupdate` | 加 `tr()` → `./scripts/update_translations.sh` → 重新构建 |
| 跑完 `lupdate` 后 `.ts` 里条目数骤降 | **没加 `-extensions C,ui`** | IQmol 源码是大写 `.C`，`lupdate` 默认不认，不加参数会零提取且**退出码仍为 0**。脚本里已加，手跑 lupdate 时要自己带 |
| 切换语言后界面没变 | 静态生效 | **重启程序**。设计如此，见手册说明 |
| 术语前后不一致 | 术语表未覆盖 | 查 `CONTRIBUTING.md` 术语表；有争议开 issue 讨论，不要单方面改 |

---

## 三、几个需要展开说的问题

### 关于 CMake 4.x

README 里写"必须用 3.x"，准确说法是：**3.x 已验证可用，4.x 未经充分验证**。

CMake 4 移除了对 `cmake_minimum_required(VERSION <3.5)` 的兼容，而 OpenBabel 等第三方
子模块里存在老式声明。理论上可通过 `CMAKE_POLICY_VERSION_MINIMUM` 绕过，但没有实测过。

**如果你在 CMake 4 上成功了，请开 issue 告诉我们**——我们会更新这条说明。

### 关于 Qt6

不支持。IQmol 上游基于 Qt5，Qt6 迁移是独立的大工程，不在本仓库范围内。
用 Qt5 5.15 LTS 最稳。

### 关于 macOS

上游标称支持，**但本仓库没有可复现的 macOS 构建验证记录**。
如果你在 macOS 上构建成功了，请开 issue 附上环境信息，我们会补进文档。
在此之前，不建议 macOS 用户直接尝试从源码构建——用官方 iqmol.org 的二进制更省事。

### 关于仓库里的 70MB zip

历史遗留。早期版本把 Windows 安装包直接提交进了 git，导致每次克隆都要下载 70MB 历史。
**现已全部迁移到 Releases**，仓库保持轻量。如果你克隆很慢，说明拿到的是旧版本。

### 关于「源码 69/69 文件 100% 复现」

这是**汉化改动可在干净上游树上被完整重放**的验证声明，不是"与官方二进制完全等价"。
它的准确含义是：在指定上游 commit 上，本仓库的汉化改动能被完整重建，源码逐字节一致。

它**不包含**：qm 内容比对、OpenBabel 行为比对、功能回归测试。
每次上游同步后会跑 `scripts/verify_replay.sh` 生成可复查的验证报告。

---

## 四、提问前请准备

开 issue 时带上这些，能省掉三轮来回：

```
操作系统与版本：
Qt 版本        (qmake --version)
CMake 版本     (cmake --version)
编译器版本
本仓库 commit  (git rev-parse HEAD)
解压了哪几个包、解压顺序、用的什么工具解压
完整日志（不要只贴最后几行）
```

`CONTRIBUTING.md` 与 issue 模板里有完整的自查清单，**提交前先过一遍**——
上面速查表里的绝大多数问题都能自己解决。
