# IQmol 汉化项目 —— 第一批改造对照表（MainWindow.C）

> 项目：IQmol 汉化项目
> 文件：`src/Main/MainWindow.C`
> 状态：已完成 tr() 包裹，`zh_CN.ts` 已生成，`zh_CN.qm` 已用官方 `lrelease` 编译并通过 `QTranslator` 加载验证
> 责任人：WorkBuddy（汉化工程）
> 日期：2026-08-28

---

## 一、改造范围与方式

本次对 `MainWindow.C` 的所有**用户可见 UI 字符串**进行了 `tr()` 包裹改造，共 **81 处**，涉及：

| 类别 | 数量 | 说明 |
|------|------|------|
| 顶层菜单标题 | 6 | File / Edit / Display / Build / Calculation / Help |
| 菜单项标签 | 55 | About、New Molecule、Undo 等 |
| 对话框消息 | 6 | Save Changes?、Network access available、Wonky molecule detected 等 |
| 状态栏消息 | 4 | Loading、Welcome to IQmol、Use \<esc\> to exit full screen mode |
| 其他可见文本 | 4 | History:、(none)、Clear List、Open File/Open Job Directory |

**未包裹（有意保留原文）的字符串：**

| 字符串 | 保留理由 |
|--------|----------|
| `"IQmol"` | 软件品牌名，不翻译 |
| `"MMFF94"`/`"MMFF94s"`/`"UFF"`/`"Gaff"`/`"Ghemical"` | 力场专有名词，且被 `action->setData(ff)` 用作数据键，翻译会破坏程序逻辑 |
| `"Generate PovRay Input"` | 位于 `/* */` 注释块内，非活动代码 |
| `"Test Internet Connection"` | 位于 `//` 注释行，非活动代码 |
| `":/imageQuestion"` | Qt 资源路径 |

**关键技术点：**
- `MainWindow` 类声明含 `Q_OBJECT` 宏，可直接使用 `tr()`（`QObject` 静态成员）。
- 采用**行号驱动的精确替换**脚本，而非全局正则，避免误伤注释块、内部标识符与专有名词。
- 力场子菜单用独立 `QString ff` 变量（非 `name`），天然避开 `tr()` 包裹，无需特殊处理。

---

## 二、翻译对照表

上下文：`IQmol::MainWindow`

| # | 原文 (source) | 译文 (translation) | 修改理由 |
|---|----------------|--------------------|----------|
| 1 | History: | 历史记录： | 撤销栈空态标签 |
| 2 | Welcome to IQmol | 欢迎使用 IQmol | 启动状态栏欢迎语 |
| 3 | Save Changes? | 保存更改？ | 关闭前保存确认对话框 |
| 4 | Save | 保存 | 标准按钮 |
| 5 | Discard | 放弃 | 标准按钮（放弃更改） |
| 6 | Cancel | 取消 | 标准按钮 |
| 7 | File | 文件 | 顶层菜单 |
| 8 | About | 关于 | 顶层菜单项 |
| 9 | New Molecule | 新建分子 | 顶层菜单项 |
| 10 | New Viewer | 新建查看器 | 顶层菜单项 |
| 11 | Open | 打开 | 顶层菜单项 |
| 12 | Open Dir | 打开目录 | 顶层菜单项 |
| 13 | Open Recent | 打开最近 | 顶层菜单项（子菜单） |
| 14 | Close Viewer | 关闭查看器 | 顶层菜单项 |
| 15 | Save As | 另存为 | 顶层菜单项 |
| 16 | Save Picture | 保存图片 | 顶层菜单项 |
| 17 | Record Animation | 录制动画 | 顶层菜单项 |
| 18 | Show Message Log | 显示消息日志 | 顶层菜单项 |
| 19 | Quit | 退出 | 顶层菜单项 |
| 20 | Edit | 编辑 | 顶层菜单 |
| 21 | Undo | 撤销 | 编辑菜单项 |
| 22 | Redo | 重做 | 编辑菜单项 |
| 23 | Cut | 剪切 | 编辑菜单项 |
| 24 | Copy | 复制 | 编辑菜单项 |
| 25 | Paste | 粘贴 | 编辑菜单项 |
| 26 | Select All | 全选 | 编辑菜单项 |
| 27 | Select None | 取消选择 | 编辑菜单项 |
| 28 | Invert Selection | 反选 | 编辑菜单项 |
| 29 | Reindex Atoms | 原子重新编号 | 编辑菜单项 |
| 30 | Preferences | 首选项 | 编辑菜单项 |
| 31 | Display | 显示 | 顶层菜单 |
| 32 | Full Screen | 全屏 | 显示菜单项 |
| 33 | Reset View | 重置视图 | 显示菜单项 |
| 34 | Show Axes | 显示坐标轴 | 显示菜单项 |
| 35 | Camera | 相机 | 显示菜单项 |
| 36 | Appearance | 外观 | 显示菜单项 |
| 37 | Atom Labels | 原子标签 | 显示菜单项（子菜单） |
| 38 | Element | 元素 | 原子标签子菜单 |
| 39 | Index | 序号 | 原子标签子菜单 |
| 40 | Mass | 质量 | 原子标签子菜单 |
| 41 | NMR | 核磁共振（NMR） | 原子标签子菜单 |
| 42 | Partial Charge | 部分电荷 | 原子标签子菜单 |
| 43 | Spin Densities | 自旋密度 | 原子标签子菜单 |
| 44 | Atom Label | 原子标签 | 原子标签子菜单 |
| 45 | Build | 构建 | 顶层菜单 |
| 46 | Insert Molecule by ID | 按 ID 插入分子 | 构建菜单项 |
| 47 | Fill Valencies With Hydrogens | 用氢原子填充化合价 | 构建菜单项 |
| 48 | Reperceive Bonds | 重新识别键 | 构建菜单项 |
| 49 | Set Isotopes | 设置同位素 | 构建菜单项 |
| 50 | Set Geometric Constraint | 设置几何约束 | 构建菜单项 |
| 51 | Freeze Selected Atoms | 冻结所选原子 | 构建菜单项 |
| 52 | Minimize Structure | 结构最小化 | 构建菜单项 |
| 53 | Select Force Field | 选择力场 | 构建菜单项（子菜单） |
| 54 | Translate To Center | 平移到中心 | 构建菜单项 |
| 55 | Symmetrize Molecule | 分子对称化 | 构建菜单项 |
| 56 | Set Symmetry Tolerance | 设置对称容差 | 构建菜单项 |
| 57 | Auto-detect Symmetry | 自动检测对称性 | 构建菜单项 |
| 58 | Calculation | 计算 | 顶层菜单 |
| 59 | Q-Chem Setup | Q-Chem 设置 | 计算菜单项 |
| 60 | Job Monitor | 任务监视器 | 计算菜单项 |
| 61 | Edit Servers | 编辑服务器 | 计算菜单项 |
| 62 | Gromacs Setup | Gromacs 设置 | 条件编译项（GROMACS） |
| 63 | Edit Gromacs Config | 编辑 Gromacs 配置 | 条件编译项（GROMACS） |
| 64 | Edit Gomacs Server | 编辑 Gromacs 服务器 | 条件编译项（GROMACS，源注释拼写 Gomacs 保留） |
| 65 | Edit Amber Config | 编辑 Amber 配置 | 条件编译项（AMBER） |
| 66 | Amber System Builder | Amber 系统构建器 | 条件编译项（AMBER） |
| 67 | Help | 帮助 | 顶层菜单 |
| 68 | Show Help | 显示帮助 | 帮助菜单项 |
| 69 | Network access available | 网络连接可用 | 网络测试对话框消息 |
| 70 | Open File | 打开文件 | 文件对话框标题（原有 tr()） |
| 71 | Loading | 正在加载 | 状态栏加载提示 |
| 72 | Open Job Directory | 打开任务目录 | 文件对话框标题（原有 tr()） |
| 73 | Only one molecule can be visible when reindexing atoms. | 原子重新编号时只能显示一个分子。 | 重编号限制提示 |
| 74 | Clear List | 清空列表 | 最近文件菜单项 |
| 75 | Use \<esc\> to exit full screen mode | 按 Esc 退出全屏模式 | 全屏模式提示 |
| 76 | Wonky molecule detected | 检测到异常分子 | 分子完整性检查警告（wonky 为化学领域俚语，意为"异常的"） |
| 77 | Do you want to proceed? | 是否继续？ | 异常分子确认对话框 |
| 78 | (none) | （无） | 服务器列表空占位符 |

> 注：表中 1–78 对应 `lupdate` 提取的 78 条 `<source>`。第 70、72 行（Open File / Open Job Directory）是源码中原有的 `tr()`，本次一并纳入 `zh_CN.ts`。

---

## 三、术语一致性说明

遵循全国科学技术名词审定委员会规范译法：
- **Molecule → 分子**（化学名词）
- **Valency → 化合价**（化学名词）
- **Isotope → 同位素**（物理/化学名词）
- **Symmetry → 对称性**（物理/化学名词）
- **Force Field → 力场**（分子力学专用）
- **Geometric Constraint → 几何约束**（结构化学）
- **Partial Charge → 部分电荷**（量子化学）
- **Spin Density → 自旋密度**（量子化学）
- **Reperceive Bonds → 重新识别键**（化学键）

保留英文不译的专有名词：**Q-Chem、Gromacs、Amber、NMR**（国际通用缩写/专有软件名，译出易造成歧义）。

---

## 四、i18n 基础设施改动

| 文件 | 改动 |
|------|------|
| `src/Main/MainWindow.C` | 81 处 UI 字符串包裹 `tr()` |
| `src/Main/IQmolApplication.C` | 构造函数调用 `loadTranslations()`，新增 `QTranslator` 加载逻辑（Qt 基础翻译 + 应用翻译，多路径回退） |
| `src/Main/IQmolApplication.h` | 声明 `loadTranslations()` 私有方法 |
| `CMakeLists.txt` | 添加 `find_package(Qt5LinguistTools)`；新增 `qt5_add_translation` 生成 `.qm` 并复制到 `bin/translations/` |
| `translations/zh_CN.ts` | 78 条中文译文（`lupdate` 生成 + 手工填充） |
| `translations/zh_CN.qm` | `lrelease` 编译产物（5348 字节） |

---

## 五、验证结果

1. **`tr()` 包裹完整性**：`MainWindow.C` 81 处 `tr()`，无遗漏、无二次包裹、无误改注释/品牌/力场。
2. **`lupdate` 提取**：78 条源字符串，与源码 `tr()` 完全一致。
3. **`lrelease` 编译**：78 finished / 0 unfinished。
4. **`QTranslator` 加载验证**：独立验证程序用 `QTranslator::load()` 加载 `zh_CN.qm`，10 条抽样翻译全部正确（File→文件、Save Changes?→保存更改？等）。
