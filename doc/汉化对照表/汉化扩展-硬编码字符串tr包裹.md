# IQmol 汉化扩展（第 2 阶段）：C++ 硬编码字符串 tr() 包裹

> 本阶段将此前未被 `tr()` 包裹、但用户可见的 C++ 硬编码字符串（窗口标题、坐标轴标签、按钮、列表头、撤销命令名等）全部包裹 `tr()` 并翻译，使其纳入 Qt Linguist 国际化体系。

> **修改理由**：这些字符串直接传给 `setText`/`setWindowTitle`/`QUndoCommand` 等 UI 函数，原未标记可翻译，故运行中始终显示英文。包裹 `tr()` 后由 `zh_CN.ts` 统一翻译；非 `QObject` 派生的 `UndoCommands` 类改用 `QCoreApplication::translate("UndoCommands", ...)` 以保证 lupdate 可提取且运行时可翻译。品牌名 `IQmol` 保留原文。

> **责任人**：IQmol 汉化组

## 改动统计

| 指标 | 数值 |
| --- | --- |
| 修改源文件数 | 18 |
| 新增 tr() 包裹点 | 45 |
| 新增翻译源串（ts） | 41 条（含 UndoCommands 构造基类 3 条 + 字符串字面量 38 条） |
| 翻译总条数（全量） | 1514 条（1473 + 41） |
| 全量 qm 验证 | 1514 通过, 0 失败 |

## 逐项对照（文件 / 行号 / 原文 / 译文 / 修改理由 / 责任人）

| 文件 | 行号 | 原文 | 译文 | 修改理由 | 责任人 |
| --- | --- | --- | --- | --- | --- |
| `Configurator/ConstraintConfigurator.C` | 41 | Set Position | 设置位置 | 窗口标题：为 setWindowTitle 字符串加 tr() 包裹 | IQmol 汉化组 |
| `Configurator/ConstraintConfigurator.C` | 127 | Configure Distance | 配置距离 | 窗口标题 tr() 包裹 | IQmol 汉化组 |
| `Configurator/ConstraintConfigurator.C` | 148 | Configure Angle | 配置角 | 窗口标题 tr() 包裹 | IQmol 汉化组 |
| `Configurator/ConstraintConfigurator.C` | 170 | Configure Torsion | 配置扭转 | 窗口标题 tr() 包裹 | IQmol 汉化组 |
| `Configurator/FrequenciesConfigurator.C` | 47 | Freq. (cm⁻¹) | 频率(cm⁻¹) | 表格列表头 tr() 包裹，保留单位符号 | IQmol 汉化组 |
| `Configurator/FrequenciesConfigurator.C` | 48 | Intens. (km/mol) | 强度(km/mol) | 表格列表头 tr() 包裹，保留单位 | IQmol 汉化组 |
| `Configurator/FrequenciesConfigurator.C` | 49 | Raman (Å4/amu) | 拉曼 (Å⁴/amu) | 表格列表头 tr() 包裹，保留单位与 Å 码点 | IQmol 汉化组 |
| `Configurator/FrequenciesConfigurator.C` | 52 | Frequency (cm⁻¹) | 频率 (cm⁻¹) | 表格列表头 tr() 包裹 | IQmol 汉化组 |
| `Configurator/FrequenciesConfigurator.C` | 53 | Intensity (km/mol) | 强度 (km/mol) | 表格列表头 tr() 包裹 | IQmol 汉化组 |
| `Configurator/IsotopesConfigurator.C` | 45 | Element | 元素 | 列表头 tr() 包裹 | IQmol 汉化组 |
| `Configurator/IsotopesConfigurator.C` | 46 | Isotopic Mass | 同位素质量 | 列表头 tr() 包裹 | IQmol 汉化组 |
| `Configurator/IsotopesConfigurator.C` | 47 | Indicies | 索引 | 列表头 tr() 包裹（原文拼写 Indicies 按界面语义译索引） | IQmol 汉化组 |
| `Configurator/MolecularSurfacesConfigurator.C` | 58 | Scale | 缩放 | 标签 tr() 包裹 | IQmol 汉化组 |
| `Configurator/MolecularSurfacesConfigurator.C` | 64 | Isovalue | 等值 | 标签 tr() 包裹 | IQmol 汉化组 |
| `Configurator/MolecularSurfacesConfigurator.C` | 70 | Isovalue | 等值 | 标签 tr() 包裹 | IQmol 汉化组 |
| `Configurator/NmrConfigurator.C` | 51 | Resolution | 分辨率 | 标签 tr() 包裹 | IQmol 汉化组 |
| `Configurator/OrbitalsConfigurator.C` | 757 | Orbital(s): | 轨道： | 标签 tr() 包裹 | IQmol 汉化组 |
| `Configurator/OrbitalsConfigurator.C` | 780 | Function(s): | 函数: | 标签 tr() 包裹 | IQmol 汉化组 |
| `Configurator/SurfaceAnimatorDialog.C` | 355 | Difference Surface | 差分表面 | 标签 tr() 包裹 | IQmol 汉化组 |
| `Layer/BackgroundLayer.C` | 36 | Background | 背景 | 图层名 tr() 包裹 | IQmol 汉化组 |
| `Layer/ConstraintLayer.C` | 125 | Invalid | 无效 | 状态提示 tr() 包裹 | IQmol 汉化组 |
| `Layer/InfoLayer.C` | 42 | Info | 信息 | 图层名 tr() 包裹 | IQmol 汉化组 |
| `Layer/SolventLayer.C` | 46 | Solvent | 溶剂 | 图层名 tr() 包裹 | IQmol 汉化组 |
| `Layer/SystemLayer.C` | 57 | Ribbons | 飘带 | 显示模式名 tr() 包裹（分子 ribbon 表示法） | IQmol 汉化组 |
| `Layer/SystemLayer.C` | 90 | Molecule | 分子 | 图层名 tr() 包裹 | IQmol 汉化组 |
| `Layer/SystemLayer.C` | 103 | Molecule | 分子 | 图层名 tr() 包裹 | IQmol 汉化组 |
| `Main/MainWindow.C` | 75 | IQmol | IQmol | 窗口标题 tr() 包裹（品牌名保留原文） | IQmol 汉化组 |
| `Process/QueueOptionsDialog.C` | 60 | Download | 下载 | 按钮文本 tr() 包裹 | IQmol 汉化组 |
| `Process/QueueOptionsDialog.C` | 63 | Job Info | 作业信息 | 标签 tr() 包裹 | IQmol 汉化组 |
| `Process/QueueOptionsDialog.C` | 64 | Download | 下载 | 按钮文本 tr() 包裹 | IQmol 汉化组 |
| `Process/QueueOptionsDialog.C` | 69 | Executable | 可执行 | 标签 tr() 包裹 | IQmol 汉化组 |
| `Qui/OptionEditors.C` | 41 | New option | 新建选项 | 占位文本 tr() 包裹 | IQmol 汉化组 |
| `Util/LogMessageDialog.C` | 68 | Logging disabled | 日志已禁用 | 状态文本 tr() 包裹 | IQmol 汉化组 |
| `Viewer/CameraDialog.C` | 49 | Time (s) | 时间 (s) | 坐标轴标签 tr() 包裹，保留单位 | IQmol 汉化组 |
| `Viewer/CameraDialog.C` | 50 | Camera Position | 相机位置 | 坐标轴标签 tr() 包裹 | IQmol 汉化组 |
| `Viewer/UndoCommands.C` | 46 | Add hydrogens | 添加氢原子 | QUndoCommand 构造文本加 QCoreApplication::translate 包裹（非 QObject 类） | IQmol 汉化组 |
| `Viewer/UndoCommands.C` | 262 | Add constraint | 添加约束 | 构造文本 translate 包裹 | IQmol 汉化组 |
| `Viewer/UndoCommands.C` | 265 | Add scan coordinated | 添加扫描约束 | setText 改 translate 包裹（原文 coordinated 按语义译约束） | IQmol 汉化组 |
| `Viewer/UndoCommands.C` | 295 | Change atom type | 更改原子类型 | 构造文本 translate 包裹 | IQmol 汉化组 |
| `Viewer/UndoCommands.C` | 341 | Change bond order | 更改键级 | 构造文本 translate 包裹 | IQmol 汉化组 |
| `Viewer/UndoCommands.C` | 385 | New molecule | 新建分子 | setText 改 translate 包裹 | IQmol 汉化组 |
| `Viewer/UndoCommands.C` | 387 | New system | 新建体系 | setText 改 translate 包裹 | IQmol 汉化组 |
| `Viewer/UndoCommands.C` | 435 | Remove molecule | 移除分子 | setText 改 translate 包裹 | IQmol 汉化组 |
| `Viewer/UndoCommands.C` | 437 | Remove system | 移除体系 | setText 改 translate 包裹 | IQmol 汉化组 |
| `Viewer/UndoCommands.C` | 440 | Remove  | 移除  | 前缀文本改 translate 包裹（拼接文件名） | IQmol 汉化组 |

## 验证方式

1. `lupdate @filelist.txt -ts zh_CN_full.ts` 重新提取 → 1514 条源串（37 new + 3 UndoCommand 修正后共 41 新增）。
2. `translate_iqmol.py` 注入译文 → 1514 条全部 finished，0 unfinished。
3. `lrelease` 编译 `zh_CN.qm` → 1514 finished。
4. `cmake --build` 重编 IQmol 可执行文件（含新 tr 代码）→ 0 错误。
5. `verify_ext.cpp` 按真实 `(context, source)` 全量核对 qm → **1514 通过, 0 失败**。`