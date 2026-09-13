# IQmol 中文版 —— 构建与验证指南

> 项目：IQmol 汉化项目
> 适用版本：IQmol3（CMake 构建体系，v3.2.3）
> 责任人：WorkBuddy（汉化工程）
> 日期：2026-08-28
> 状态：✅ 已在本环境（Ubuntu 24.04）完整编译并验证中文界面加载成功

> **更新说明（2026-09-13）**：本文为汉化早期（8 月）的构建与验证指南，记录了
> 端到端打通翻译管线的关键步骤。其中部分数据已随后续工作更新，请以最新验证记录为准：
> - 译文条数 **78 → 1519**（见 `2026-09-13-编译与运行验证.md`）；
> - OpenBabel 插件加载失败在 Windows 静态构建下已通过 `BUILD_SHARED=OFF` +
>   `--whole-archive` 根治（见 `2026-09-13-OpenBabel插件加载失败诊断与修复.md`），
>   本文的 `BABEL_LIBDIR` 环境变量兜底方案仍适用于系统 OpenBabel 场景。

---

## 一、环境要求

| 类别 | 组件 | 版本/包名 | 说明 |
|------|------|-----------|------|
| 编译器 | g++ / CMake | g++ ≥ 11，CMake ≥ 3.16 | 提供 C++17 支持 |
| Qt5 | qtbase5-dev、qttools5-dev、qttools5-dev-tools | Qt 5.15.x | `qttools5-dev` 提供 `Qt5LinguistTools` 的 CMake 配置；`-tools` 提供 `lrelease`/`lupdate` |
| OpenGL 查看器 | libqglviewer-dev-qt5 | 库名 `QGLViewer-qt5` | Ubuntu 上库名带 `-qt5` 后缀（注意见第六章） |
| 化学/数学 | libopenbabel-dev、openbabel、libyaml-cpp-dev、libopenmesh-dev | — | OpenBabel 3.1.1 |
| 其它 | libssh2-1-dev、libarchive-dev、libboost-all-dev、libhdf5-dev、libqt5svg5-dev、gfortran | — | 编译依赖 |

> **提示**：本环境通过腾讯云镜像源安装上述包，所有 Qt5 组件均可用。之前 Windows 沙箱无法安装 Qt5 的死结在此环境已解开。

---

## 二、获取源码

IQmol3 主仓库已用 CMake 重写，无需 Windows 旧版（2.15.0）的 `.patch` 文件。

```bash
git clone --recursive https://github.com/nutjunkie/IQmol3.git
cd IQmol3
```

> 子模块（libQGLViewer、openbabel 等）在 **Linux 上不编译**——Linux 分支直接链接系统库。
> 若子模块克隆失败（如直连 GitHub 受限），可经代理（如 `ghfast.top`）拉取后单独补齐，但编译 Linux 版本身不依赖子模块源码。

---

## 三、汉化改造已包含内容

| 文件 | 改动 |
|------|------|
| `src/Main/MainWindow.C` | 81 处用户可见 UI 字符串包裹 `tr()`（菜单、对话框、状态栏） |
| `src/Main/IQmolApplication.C` | 新增 `loadTranslations()`，在应用启动时加载 Qt 基础翻译 + 应用中文翻译 |
| `src/Main/IQmolApplication.h` | 声明 `loadTranslations()` 私有方法 |
| `CMakeLists.txt` | 接入 `lrelease`，构建期自动生成 `zh_CN.qm` 并复制到可执行文件同级 `translations/` |
| `src/Math/CMakeLists.txt` | 修正 Linux 下 QGLViewer 链接库名（`QGLViewer` → `${QGLVIEWER_LIBRARY}` = `QGLViewer-qt5`） |
| `translations/zh_CN.ts` | 1519 条中文译文（`lupdate` 提取 + 手工填充，0 unfinished；早期版本为 78 条，随全量 UI 扩展增至 1519） |
| `translations/zh_CN.qm` | `lrelease` 编译产物 |

**保留原文不译**：品牌名 `IQmol`、力场专有名词（`MMFF94`/`UFF`/`Gaff`/`Ghemical` 等，且被 `setData()` 用作数据键）、Qt 资源路径、注释块内文本。

---

## 四、构建步骤

```bash
cd IQmol3
mkdir -p build && cd build
cmake ..          # 配置；会自动 find Qt5 / OpenBabel / yaml-cpp / QGLViewer-qt5 等
make -j$(nproc)   # 编译；POST_BUILD 阶段自动 lrelease 生成 zh_CN.qm
```

构建成功后：
- 可执行文件：`build/IQmol`
- 中文翻译：`build/translations/zh_CN.qm`（由 CMake 的 POST_BUILD 命令生成）

---

## 五、运行中文版

### 5.1 真实桌面（Linux / macOS / Windows）
直接双击或从终端运行 `IQmol`，中文翻译随程序自动加载（见 5.3 说明）。

### 5.2 无显示环境（CI / 沙箱）
需虚拟显示 + 软件 OpenGL：

```bash
xvfb-run -a -s "-screen 0 1280x1024x24" env \
  QT_QPA_PLATFORM=xcb \
  BABEL_LIBDIR=/usr/lib/x86_64-linux-gnu/openbabel/3.1.1 \
  BABEL_DATADIR=/usr/share/openbabel \
  LANG=zh_CN.UTF-8 LC_ALL=zh_CN.UTF-8 \
  ./IQmol
```

| 环境变量 | 作用 |
|----------|------|
| `BABEL_LIBDIR` | 覆盖 OpenBabel 插件目录。IQmol 默认设为 `/usr/lib/openbabel/3.1.1`，**Ubuntu 实际路径为 `/usr/lib/x86_64-linux-gnu/openbabel/3.1.1`**，必须覆盖否则报 `Unable to find OpenBabel plugins` |
| `BABEL_DATADIR` | OpenBabel 数据目录（原子类型、力场参数等） |
| `LANG` / `LC_ALL` | 设置中文区域；本汉化实现为「非中文时默认中文」，故即便未设也会加载 `zh_CN` |

### 5.3 翻译加载逻辑
`IQmolApplication::loadTranslations()` 的行为：
1. 加载 Qt 基础翻译（`qt_<locale>.qm`，标准对话框按钮等）。
2. 应用翻译：取系统 `QLocale::system().name()`；**若非 `zh` 开头则强制使用 `zh_CN`**（满足汉化目标「默认中文界面」）。
3. 按以下顺序搜索 `zh_CN.qm`：`applicationDirPath()/translations` → `applicationDirPath()` → `currentPath()/translations` → `currentPath()`。

---

## 六、已知问题与修复记录

| 问题 | 现象 | 修复 |
|------|------|------|
| Qt5LinguistTools 找不到 | CMake 报 `Qt5LinguistToolsConfig.cmake` 缺失 | 安装 `qttools5-dev`（仅 `-tools` 不含 CMake 配置，需完整 dev 包） |
| QGLViewer 链接失败 | `cannot find -lQGLViewer` | Linux 库名为 `QGLViewer-qt5`；将 `src/Math/CMakeLists.txt` 硬编码的 `QGLViewer` 改为 `${QGLVIEWER_LIBRARY}`（顶层已按平台设为 `QGLViewer-qt5`） |
| `qt5_add_translation` 不产出 qm | 构建期无 lrelease 步骤，复制命令因源缺失失败 | 改用 `find_program(LRELEASE_EXECUTABLE lrelease)` + `add_custom_command(POST_BUILD)` 显式调用 `lrelease -qm`，并用 `$<TARGET_FILE_DIR:...>` 生成器表达式定位 exe 目录 |
| OpenBabel 插件找不到 | `Unable to find OpenBabel plugins` | 系统 OpenBabel 场景：运行时设 `BABEL_LIBDIR=/usr/lib/x86_64-linux-gnu/openbabel/3.1.1`；**Windows 静态构建**已通过 `BUILD_SHARED=OFF` + `--whole-archive` 根治（见独立诊断文档） |
| headless 无 OpenGL | `QOpenGLWidget: Failed to create context` | 用 xvfb + mesa 软件渲染（`libgl1-mesa-dri` / `libosmesa6`） |

---

## 七、验证结果

1. **编译**：`make` 在 Ubuntu 24.04 完整通过，`[100%] Built target IQmol`（早期版本产物约 144 MB；后续验证记录为 11.9 MB，取决于链接方式）。
2. **qm 生成**：构建期 `lrelease` 输出 `Generated 1519 translation(s) (1519 finished and 0 unfinished)`（早期版本为 78 条）。
3. **QTranslator 加载验证**：独立 Qt 程序用 `QTranslator::load()` 加载 `zh_CN.qm`，抽样 10 条（`File→文件`、`Save Changes?→保存更改？`、`Use <esc> to exit full screen mode→按 Esc 退出全屏模式` 等）全部正确。
4. **运行时加载验证**：`xvfb-run` 启动 IQmol，日志输出 `[i18n] Loaded translation: "zh_CN"`，无 OpenBabel 错误、无崩溃。

> 结论：IQmol 中文界面汉化管线（源码 `tr()` 改造 → `lupdate` 提取 → `zh_CN.ts` 翻译 → `lrelease` 编译 → 运行时 `QTranslator` 加载）已在本环境端到端打通，是之前 Windows 沙箱未能完成的关键步骤。
