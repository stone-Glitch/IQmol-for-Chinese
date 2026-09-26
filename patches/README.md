> # ⚠️ 下载源码想直接打包的人，请先看这一句
>
> **你不需要、也不应该 `git apply` 本目录下任何补丁。**
>
> 当前 `main` 分支的源码**已经是完整汉化成果版**——语言支持、tr() 包裹、QChem 关键词库汉化（477/504）等全部改动都已合入源码树。
> `patches/` 里的两个 `.patch` 仅用于**维护者从干净官方上游树重新做「版本升级迁移」**，
> 对「下载 → 构建 → 打包」这条普通路径**完全不需要**。对其误 apply 会因改动已合入而失败。
>
> 👉 下载后如何零补丁直接出包，见 [`../构建与打包/下载源码直接打包.md`](../构建与打包/下载源码直接打包.md)。

# patches/ 目录说明（上游升级迁移用）

本目录下的补丁仅供**上游版本升级迁移**使用，下文以"非机械改动补丁"为例说明其技术细节。

## 用途

本补丁收集**无法由 `replay_tr.py` 规则表重放**的 35 个源文件改动，
是「上游升级迁移」流程的第 ③ 步（最后一步）。

## 迁移三步（在干净上游树上）

```bash
# ① 语言支持功能补丁（loadTranslations / Language 偏好 / GCC15 cstdint）
git apply patches/功能补丁-语言支持.patch

# ② tr() 包裹重放（规则表 487 条 / 58 文件）
cp scripts/i18n/replay_tr.py scripts/i18n/wrap_tr.rules <目标树>/scripts/i18n/
cd <目标树> && python3 scripts/i18n/replay_tr.py --apply

# ③ 非机械改动补丁（本文件，35 个文件）
git apply patches/功能补丁-非机械改动.patch
```

> ⚠️ 顺序不可颠倒：本补丁的 diff 上下文基于「上游 + ① + ②」的结果。

## 实测验证

在上游 `af7ff60` 干净树上执行 ①→②→③ 后：
- ① 功能补丁：干净应用 ✅
- ② 重放：新增 323 处包裹，55 个文件 ✅
- ③ 本补丁：干净应用 ✅
- **结果：69 / 69 个源码文件与成果版完全一致（100% 复现）** ✅

## 为什么这 35 个文件无法机械重放

| 根因 | 说明 | 举例 |
|---|---|---|
| 字面量文本改变 | 上游是拼接式 `"X "` + `s += ...`，我们改成占位符式 `tr("X %1")`；规则表按原文精确查找必然落空 | `MolecularGridEvaluator.C`、`GeometryConstraint.C` |
| 我方新增代码行 | 上游不存在对应字面量，无处可包 | `ShaderDialog.C`（数据/显示分离）、`OrbitalsConfigurator.C` |
| 构造函数初始化列表重构 | 初始化列表中的标签为裸字符串，改由构造体内 `setText(tr(...))` 覆盖 | `CubeDataLayer.C`、`DipoleLayer.C`、`FrequenciesLayer.C` 等 |
| 常量 → 可翻译字面量 | `DefaultMoleculeName` → `"Untitled"` | `MoleculeLayer.C` |
| 非 QObject 类需 `translate()` | 普通 C++ 类无 `tr()`，须 `QCoreApplication::translate("Ctx", ...)` | `HelpBrowser.C`、`OpenBabelParser.C`、`SurfaceType.C`、`JobInfo.C` |

## 覆盖的 35 个文件

- `src/Configurator/ConstraintConfigurator.C`
- `src/Configurator/GeminalOrbitalsConfigurator.C`
- `src/Configurator/MolecularSurfacesConfigurator.C`
- `src/Configurator/MullikenDecompositionsDialog.C`
- `src/Configurator/OrbitalsConfigurator.C`
- `src/Configurator/SurfaceAnimatorDialog.C`
- `src/Data/SurfaceType.C`
- `src/Data/SurfaceType.h`
- `src/Grid/MolecularGridEvaluator.C`
- `src/Layer/CubeDataLayer.C`
- `src/Layer/DipoleLayer.C`
- `src/Layer/EfpFragmentListLayer.C`
- `src/Layer/ExcitedStatesLayer.C`
- `src/Layer/FrequenciesLayer.C`
- `src/Layer/GeminalOrbitalsLayer.C`
- `src/Layer/MolecularSurfacesLayer.C`
- `src/Layer/MoleculeLayer.C`
- `src/Layer/NmrLayer.C`
- `src/Layer/OctreeLayer.C`
- `src/Layer/SurfaceLayer.C`
- `src/Layer/SymmetryLayer.C`
- `src/Layer/VibronicLayer.C`
- `src/Main/FragmentTable.C`
- `src/Main/HelpBrowser.C`
- `src/Main/IQmolApplication.C`
- `src/Main/PreferencesBrowser.C`
- `src/Parser/OpenBabelParser.C`
- `src/Process/JobInfo.C`
- `src/Qui/GeometryConstraint.C`
- `src/Qui/LJParametersSection.C`
- `src/Qui/MoleculeSection.C`
- `src/Qui/RemSection.C`
- `src/Util/ColorDialog.C`
- `src/Viewer/ShaderDialog.C`
- `src/Viewer/UndoCommands.C`
