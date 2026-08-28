# IQmol 中文界面截图集

本目录为中文用户手册 / 汉化验证提供 IQmol 界面截图。

## 技术方案

- **放弃 xdotool 自动化**：在沙箱 Xvfb 环境下，`xdotool` 发送的合成键鼠事件**完全无法被 Qt 接收**（已严格验证：连 `Ctrl+N` 普通快捷键都不响应），导致基于菜单导航的对话框触发截图彻底不可行。
- **改用 QUiLoader 静态渲染**：用系统 Qt5 的 `QUiLoader` 动态加载 IQmol 各 `.ui` 文件，加载 `zh_CN.qm` 中文翻译，在 `offscreen` 平台下 `grab()` 截图。该方案**无需 Xvfb、无需 xdotool、无需窗口焦点**。
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

## 仍未覆盖项

| 目标 | 原因 |
|------|------|
| `NewMolecule` | 不是对话框，仅"新建分子"动作，无独立界面 |

## 翻译质量备注

- `zh_CN.ts` 共 **1517** 条字符串，0 未完成、0 空译文，`zh_CN.qm` 可正常加载（运行日志 `[i18n] Loaded translation: "zh_CN"`）。
- 术语译法符合规范：Force Field→力场、Molecule→分子、Atom→原子、Energy→能量 等。
- 约 335 条"译文=原文"均为合理的英文保留（软件名 IQmol、作者名、算法名如 DIIS/HFPT、物理量 a.u./K、变量 X/Y、CSS 代码、服务名 AWS 等），已排除 Designer 占位符（`Label4` / `Lable6` / `checkBox0` 等运行时由 C++ 动态覆盖，不会真正显示）。
