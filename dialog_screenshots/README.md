> 🏠 [项目首页](../README.md) › [文档中心](../docs/README.md)

---

# IQmol 中文界面截图集

本目录为中文用户手册 / 汉化验证提供 IQmol 界面截图。

## 技术方案

- **放弃 xdotool 自动化**：在沙箱 Xvfb 环境下，`xdotool` 发送的合成键鼠事件**完全无法被 Qt 接收**（已严格验证：连 `Ctrl+N` 普通快捷键都不响应），导致基于菜单导航的对话框触发截图彻底不可行。
- **改用 QUiLoader 静态渲染**：用系统 Qt5 的 `QUiLoader` 动态加载 IQmol 各 `.ui` 文件，在 `offscreen` 平台下 `grab()` 截图。该方案**无需 Xvfb、无需 xdotool、无需窗口焦点**。
- ⚠️ **重要更正（2026-10-02 实测）**：Qt5 的 `QUiLoader` **没有 `setTranslator`**（Qt4 遗 API），加载 `.ui` 时**不应用任何翻译**——即使装上 `QTranslator(zh_CN.qm)` 也不生效。因此 `all/`、`cards/` 共 150+ 张截图中，**所有应用级文本（对话框内标签、按钮、标签页名）显示的是 `.ui` 英文原文，不是真实运行时的中文**；「重置/取消/关闭」等标准按钮的中文是截图驱动的**后处理**写上去的（见第 4 条）。真实运行时界面（uic 生成代码 + QTranslator）是全中文的——运行时采样实测英文残留率 `E_r=0%`，真机录屏见 `build-video/out/`。**本截图集只能用于「对话框结构清单 / 布局核对」，不能用于展示中文效果，也不能直接进推广视频。**
- **补漏与修正**：
  1. 发现 `.ui` 顶层不只有 `QDialog`，还存在 `QMainWindow`、`QFrame`、`QWidget` 等类型。重新渲染后覆盖全部 **82** 个 `.ui` 文件，0 失败。
  2. 系统 `QFileDialog`（打开文件 / 打开目录）使用自定义 Qt 渲染 + 系统 `qt_zh_CN.qm` 翻译文件生成中文截图。
  3. 修正了 3 处界面标签：`CPUs` → `CPU 数`、`Omega` → `Ω（衰减参数）`、`Alpha` → `不透明度 (α)`；同时 `zh_CN.ts` 已重新 `lupdate` 并 `lrelease`。
  4. 由于系统 Qt 自带翻译未提供 `OK/Cancel/Apply` 等标准按钮映射，截图驱动对 `QDialogButtonBox` 做了后处理，确保所有截图中的标准按钮均显示为中文（确定 / 取消 / 应用 / 关闭 等）。

## 文件清单

### 顶层：核心对话框（11 个）+ 主窗口

| 文件 | 对应菜单 / 界面 |
|------|----------------|
| `AboutDialog.png` | 关于 IQmol（文件→关于） |
| `AppearanceDialog.png` | 外观（显示→Appearance，对应 `ShaderDialog.ui`） |
| `CameraDialog.png` | 相机设置（显示→Camera） |
| `ConstraintDialog.png` | 几何约束（构建→Set Geometric Constraint） |
| `InsertMolecule.png` | 按 ID 插入分子（构建→Insert Molecule by ID） |
| `IsotopeDialog.png` | 同位素设置（构建→Set Isotopes） |
| `JobMonitor.png` | 任务监视器（计算→Job Monitor） |
| `OpenDir.png` | 打开目录（系统 QFileDialog，已加载 Qt 中文翻译） |
| `OpenFile.png` | 打开文件（系统 QFileDialog，已加载 Qt 中文翻译） |
| `QUI.png` | Q-Chem 计算设置（计算→Q-Chem Setup） |
| `ServerDialog.png` | 服务器配置（计算→Edit Servers） |
| `Viewer_zh.png` | 中文主窗口（菜单栏/工具栏已中文化） |

### `all/`：全部 82 个可静态渲染的 `.ui` 界面

包含 `PreferencesBrowser`、`JobMonitor`、`InputDialog`、`ToolBar`、各类 `*Tab` / `*Configurator`、以及 Aberration、Axes、Background、Camera、ClippingPlane、Color、CubeData、Dipole、EfpFragmentList、ExcitedStates、Frequencies、GeminalOrbitals、GenerateConformers、Geometry、GeometryConstraint、GeometryList、GridInfo、Gromacs*、HelpBrowser、Info、MolecularSurfaces、Mulliken、Nmr、Octree、Orbitals、ProteinChain、ScalarConstraint、Surface、SurfaceAnimator、Symmetry、VectorConstraint、Isotopes 等全部可渲染对话框与配置面板。

### `cards/`：多卡片界面的逐卡片截图（73 张）

IQmol 部分对话框用 `QTabWidget`（标签页）、`QToolBox`（折叠卡片）、`QStackedWidget`（堆叠页）把内容分成多张"卡片"，`all/` 里的整窗截图只能看到默认激活的第一张。`cards/` 把每张卡片单独渲染，便于逐卡核对中文。

| 子目录 | 卡片数 | 说明 |
|--------|--------|------|
| `InputDialog/` | 54 | Q-Chem 输入文件编辑器：设置/高级 2 个标签页 + SCF 控制/波函数分析折叠卡 + 高级选项堆叠 36 页 + 溶剂 7 页 + 大分子 5 页 |
| `SystemBuilderDialog/` | 8 | 体系构建器：输入/输出标签页 + 源/参数/溶剂/抗衡离子折叠卡 |
| `ShaderDialog/` | 6 | 外观（着色器/效果/POV-Ray 标签页） |
| `GromacsDialog/` | 4 | Gromacs：EditConf/溶剂化标签页 |
| `GeometryTab/` | 1 | 几何选项卡的静态部分（其 `geomOptStack` 堆叠页由 C++ 运行时按单选按钮动态添加，静态渲染不可得，需真实 QUI 运行态） |

文件命名：`{类型}{容器序号}_{容器objectName}_{页序}_{页标签}.png`。

## 仍未覆盖项

| 目标 | 原因 |
|------|------|
| `NewMolecule` | 不是对话框，仅"新建分子"动作，无独立界面 |

## 翻译质量备注

- `zh_CN.ts` 共 **1517** 条字符串，0 未完成、0 空译文，`zh_CN.qm` 可正常加载（运行日志 `[i18n] Loaded translation: "zh_CN"`）。
- 术语译法符合规范：Force Field→力场、Molecule→分子、Atom→原子、Energy→能量 等。
- 约 335 条"译文=原文"均为合理的英文保留（软件名 IQmol、作者名、算法名如 DIIS/HFPT、物理量 a.u./K、变量 X/Y、CSS 代码、服务名 AWS 等），已排除 Designer 占位符（`Label4` / `Lable6` / `checkBox0` 等运行时由 C++ 动态覆盖，不会真正显示）。

---

> 维护者：@stone-Glitch ｜ 最后整理：2026-10-01
