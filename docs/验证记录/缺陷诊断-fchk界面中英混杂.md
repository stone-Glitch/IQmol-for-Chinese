# 缺陷诊断报告（修订版）— Windows 双击 `.fchk` 界面英文混杂

> 报告：WorkBuddy ｜ 更新：2026-10-01 17:45 ｜ 对应反馈：**F1**
> 复现环境：Windows 包（v3.2.3-zh_CN）+ Wine 9.0 + Xvfb
> **本报告取代前一版结论**（前一版基于 Linux 包，方向有误）

---

## 一、复现结论（一句话）

**Windows 双击 `.fchk` 时，翻译加载完全正常——菜单栏是中文的。**
用户看到的"未汉化"实际是**历史记录面板里的操作名称**这类
**源码中漏加 `tr()` 的硬编码字符串**，它们从设计上就无法被翻译。

---

## 二、实测证据

### 2.1 复现条件

| 项 | 值 |
|---|---|
| 包 | `IQmol-win64-3.2.3-zh_CN.zip`（解包为 `/tmp/winpkg/IQmol/`） |
| 运行层 | Wine 9.0 + Xvfb 虚拟显示 |
| 操作 | `IQmol.exe <path>\water.fchk`，**CWD 设为 fchk 所在目录**（模拟双击） |

### 2.2 运行日志（证明文件确实打开）

```
IQmol Version:  v3.2.3
Setting BABEL_LIBDIR =  "Z:/tmp/winpkg/IQmol/lib/openbabel"
Parsing file:  "Z:\tmp\winpkg\testdir\water.fchk"
File parsed successfully:  "Z:\tmp\winpkg\testdir\water.fchk"   ← fchk 解析成功
Adding  "water" IQmol::Layer::Molecule(...)                      ← 分子已加载
```

### 2.3 界面截图（关键证据）

菜单栏：**文件　编辑　显示　构建　计算　帮助** ← **全中文，说明翻译工作正常**

模型视图面板：**全局 / 未命名 / water** ← 中文

历史记录面板：

```
Reperceive bonds     ← ★ 英文（未翻译）
新建分子              ← 中文
```

> 截图见 `/tmp/win_final.png`、放大图 `/tmp/h_b.png`

### 2.4 二进制反证（决定性）

从 `IQmol.exe` 提取字符串，**翻译加载路径已包含完整候选**：

```
zh_CN
/translations
/../translations              ← ★ 已含"上一级"候选，说明此前的路径隐患已修
/../share/iqmol/translations
[i18n] Loaded translation:
[i18n] searched paths:
```

检查已编译的 `translations/zh_CN.qm`（175,701 字节）：

| 字符串 | 是否存在于 qm |
|---|---|
| `Reperceive Bonds`（大写 B） | ✅ 存在 |
| `Reperceive bonds`（小写 b） | ★ **不存在** |
| `Remove atoms/bonds` | ★ **不存在** |
| `Translate to center` | ★ **不存在** |
| `Add molecule` | ★ **不存在** |

> Qt 翻译查找**区分大小写**。`tr("Reperceive Bonds")` 与裸字符串 `"Reperceive bonds"`
> 是两个完全不同的条目，后者永远不会被翻译。

---

## 三、根因

### 3.1 直接原因：源码漏加 `tr()`

`src/Layer/MoleculeLayer.C:2439`：

```cpp
Command::EditPrimitives* cmd(new Command::EditPrimitives("Reperceive bonds", this));
//                                                 ^^^^^^^^^^^^^^^^^^ 裸字符串
```

对比同一文件里被正确包裹的写法（`UndoCommands.h`）：

```cpp
: EditPrimitives(tr("Add Charges"), molecule) { ... }   // ← 有 tr()
```

### 3.2 传播链路

```
lupdate 扫描源码
   ↓  只提取 tr() / QObject::tr() 包裹的字符串
裸字符串 "Reperceive bonds" 被忽略
   ↓
zh_CN.ts 中没有该条目
   ↓
zh_CN.qm 中没有该条目
   ↓
运行时 QUndoCommand 把该字符串直接显示到「历史记录」面板
   ↓
用户看到英文
```

**这不是翻译遗漏，而是"源字符串根本没进入翻译流程"**——属于**代码缺陷**，翻译人员无法通过修改 `.ts` 修复。

### 3.3 全量扫描结果

对全部命令类构造点扫描，共发现 **8 处**同类缺陷：

| # | 文件 : 行 | 裸字符串 | 触发场景 |
|---|---|---|---|
| 1 | `src/Layer/MoleculeLayer.C:2439` | `Reperceive bonds` | 重新识别化学键 |
| 2 | `src/Layer/MoleculeLayer.C:1548` | `Remove atoms/bonds` | 删除原子/键 |
| 3 | `src/Layer/ComponentLayer.C:114` | `Translate to center` | 平移到中心 |
| 4 | `src/Viewer/BuildEfpFragmentHandler.C:86` | `Add EFP fragment` | 添加 EFP 片段 |
| 5 | `src/Viewer/BuildMoleculeFragmentHandler.C:65` | `Add molecule` | 添加分子片段 |
| 6 | `src/Viewer/UndoCommands.h:101,103` | `Move items` | 拖动对象（默认文本） |
| 7 | `src/Viewer/UndoCommands.h:151` | `Add Charges` | 添加电荷 |
| 8 | `src/Viewer/UndoCommands.h:161,169` | `Minimize energy` / `Symmetrize structure` | 能量最小化 / 对称化 |

> 这些字符串**全部显示在「历史记录」面板**——用户每执行一次操作就会看到，
> 因此观感是"界面一半中文一半英文"。

---

## 四、修复方案

### 4.1 补丁（已产出）

见 `patches/历史残留/补丁-历史记录未翻译字符串.patch`，对上述 8 处逐一加 `tr()`：

```cpp
- Command::EditPrimitives* cmd(new Command::EditPrimitives("Reperceive bonds", this));
+ Command::EditPrimitives* cmd(new Command::EditPrimitives(tr("Reperceive bonds"), this));
```

**注意**：`UndoCommands.h` 中作为默认参数的三处，`tr()` 在头文件内需确认类有 `Q_OBJECT`；
`MoveObjects` 继承 `QUndoCommand`（非 QObject），建议改为在 `.C` 实现内处理，
或使用 `QObject::tr()` / `QCoreApplication::translate()`。

### 4.2 必须配套的后续步骤

加 `tr()` 只是第一步，**不重新生成翻译文件的话，界面依然显示英文**：

```bash
# 1. 重新提取字符串（会新增上述 8 条 source）
lupdate src/ -ts translations/zh_CN.ts

# 2. 翻译新增条目（8 条，见下表）

# 3. 重新编译
lrelease translations/zh_CN.ts -qm translations/zh_CN.qm

# 4. 重新打包
```

### 4.3 建议译文

| 原文 | 建议译文 | 依据 |
|---|---|---|
| `Reperceive bonds` | 重新识别化学键 | 与已有 `Reperceive Bonds` 译文保持一致 |
| `Remove atoms/bonds` | 删除原子/键 | 与菜单「删除」术语统一 |
| `Translate to center` | 平移到中心 | 与「平移」菜单项一致 |
| `Add EFP fragment` | 添加 EFP 片段 | EFP 为专有名词，保留 |
| `Add molecule` | 添加分子 | 简洁 |
| `Move items` | 移动对象 | 与「移动」术语统一 |
| `Add Charges` | 添加电荷 | 与已有条目一致 |
| `Minimize energy` | 能量最小化 | 与菜单项一致 |
| `Symmetrize structure` | 结构对称化 | 与菜单项一致 |

### 4.4 防复发建议

在 CI 或发布前脚本中加入检查：

```bash
# 扫描可能未加 tr() 的裸字符串（启发式）
grep -rnE '(EditPrimitives|MoveObjects|AddConstraint)\("[A-Z][a-z]' src/ | grep -v 'tr('
```

同时建议开启 `lupdate` 的 `-no-obsolete` 并定期比对 `.ts` 条目数变化。

---

## 五、对前一版报告的更正

| 项 | 前一版结论 | 修订后结论 |
|---|---|---|
| 复现平台 | Linux 包 | **Windows 包**（按用户补充） |
| 现象 | 整窗回落英文 | **菜单正常，历史记录等处的操作名英文** |
| 根因 | `loadTranslations()` 缺 `../translations` 候选 | **源码漏加 `tr()`**（Windows exe 中路径候选已完整） |

> ❌ 前一版"路径候选缺失"的推断**不成立**：Windows 包二进制中已含
> `/../translations` 与 `/../share/iqmol/translations` 候选，路径无问题。
> 该结论仅对**旧版 Linux 包**在特定 CWD 下成立，不适用于本次 Windows 场景。

---

## 六、影响与优先级

| 项 | 评估 |
|---|---|
| 严重程度 | **中** — 不影响功能，但"半中半英"严重影响汉化完整度观感 |
| 影响范围 | Windows / Linux / macOS **全平台**（源码级缺陷） |
| 修复成本 | 低（8 处加 `tr()`）+ 中（重跑 lupdate/lrelease、补译文、重打包） |
| 建议优先级 | **P1**，建议纳入下一版 |

> 关联：这也部分解释了 **H2「标签不全」** 的观感——用户看到的中英混杂，
> 很可能有一大部分来自这类未进翻译流程的硬编码字符串。
