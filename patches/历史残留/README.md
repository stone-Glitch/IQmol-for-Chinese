# patches/历史残留

本目录存放**已被取代的早期补丁草稿**，仅供追溯，**不要直接应用**。

| 文件 | 原意 | 状态 |
|---|---|---|
| `补丁-未翻译字符串全量.patch` | 早期对未翻译字符串的全量 `tr()` 包裹草稿 | 已被 `功能补丁-*` 四件套覆盖，可忽略 |
| `补丁-历史记录未翻译字符串.patch` | 历史记录面板未翻译字符串的局部修正（F1 缺陷的精准补丁） | **已迁移并取代**（见下） |

## 迁移完成（2026-10-03）：F1 的 9 处字符串已并入生效补丁集

原说明称"改动已并入 `功能补丁-*`"，但对 F1 涉及的这批字符串**并不成立**。经逐串 grep 核实：
- F1 的字符串（`Reperceive bonds`、`Remove atoms/bonds`、`Translate to center`、`Add EFP fragment`、
  `Add molecule`、`Move items`、`Add Charges`、`Minimize energy`、`Symmetrize structure`）
  在四件套中**全部 0 命中**，在 `wrap_tr.rules` 规则表中也是 **0 命中**。
- 这批字符串属「补丁集的缝隙」——发布版 `v3.2.3-zh_CN` 的「历史记录」面板/撤销栈因此仍显示英文。

**已于 2026-10-03 修复并迁移**：
- 母仓库源码直接修复 9 处（`MoleculeLayer.C` 4 处、`ComponentLayer.C` 1 处、
  `BuildEfpFragmentHandler.C` 1 处、`BuildMoleculeFragmentHandler.C` 1 处、`UndoCommands.h` 2 类共 4 处）。
- 同步并入 [`../功能补丁-非机械改动.patch`](../功能补丁-非机械改动.patch)（该补丁由 36 文件扩至 38 文件）。
  **迁移方式有实质更正**：本目录原草稿把 `UndoCommands.h` 的 4 处直接写成 `tr()`，
  这在 `QUndoCommand`（非 QObject）上下文里**编译不过**，也是它当初被标"不要应用"的技术原因。
  正确做法是 `QCoreApplication::translate()`，且因 `lupdate` 不扫 `.h`，文本改由调用点传入、
  默认文本兜底下沉到 `UndoCommands.C`。
- `lupdate` 抽取 8 条新条目（`Add Charges` 无调用点，未进表）→ 填中文译文 → `lrelease`
  生成 `zh_CN.qm`（2120 条，0 unfinished）。

## 为何保留而非删除

保留在此处是为了保留"当初是怎么发现并修补这些残留的"过程证据，便于审计"哪些字符串是何时补的"。
**F1 的修复已于 2026-10-03 并入生效补丁集，本目录现已可整体删除**——保留仅为留痕。

> 当前生效的迁移/构建补丁是 `../` 下 `功能补丁-*` 四件套（构建层 / 界面资源 / 语言支持 / 非机械改动）
> 及对应的 `.meta.json` 元数据。

> 维护者：@stone-Glitch ｜ 更新：2026-10-03
