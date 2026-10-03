> 🏠 [项目首页](../README.md) › [文档中心](../docs/README.md)

---

> # ⚠️ 下载源码想直接打包的人，请先看这一句
>
> **你不需要、也不应该 `git apply` 本目录下任何补丁。**
>
> 当前 `main` 分支的源码**已经是完整汉化成果版**——语言支持、tr() 包裹、QChem 关键词库汉化（477/504）等全部改动都已合入源码树。
> `patches/` 里的三个 `.patch` 仅用于**维护者从干净官方上游树重新做「版本升级迁移」**，
> 对「下载 → 构建 → 打包」这条普通路径**完全不需要**。对其误 apply 会因改动已合入而失败。
>
> 👉 下载后如何零补丁直接出包，见 [`下载源码直接打包.md`](../docs/构建与打包/下载源码直接打包.md)。

# patches/ 目录说明（上游升级迁移用）

本目录下的补丁仅供**上游版本升级迁移**使用。四个补丁按序构成迁移的 ①②③③.5④ 步。

## 目录索引

| 补丁 | 迁移步骤 | 覆盖 | 作用 |
|---|---|---|---|
| [`功能补丁-语言支持.patch`](功能补丁-语言支持.patch) | ① | 6 个文件 | 语言加载 / Language 偏好 / GCC15 cstdint |
| （规则表，非补丁）`scripts/i18n/wrap_tr.rules` | ② | 487 条 / 58 文件 | tr() 包裹机械重放 |
| [`功能补丁-非机械改动.patch`](功能补丁-非机械改动.patch) | ③ | 38 个文件 | 无法机械重放的源码逻辑改动 |
| [`功能补丁-界面资源.patch`](功能补丁-界面资源.patch) | ③.5 | 22 个文件 | `.ui` 文本汉化 + 高分屏修正（**见下节**） |
| [`功能补丁-构建层.patch`](功能补丁-构建层.patch) | ④ | 4 个文件 | 构建体系 + 工程配置（**见下节**） |

## 迁移四步（在干净上游树上）

```bash
# ① 语言支持功能补丁（loadTranslations / Language 偏好 / GCC15 cstdint）
git apply patches/功能补丁-语言支持.patch

# ② tr() 包裹重放（规则表 487 条 / 58 文件）
cp scripts/i18n/replay_tr.py scripts/i18n/wrap_tr.rules <目标树>/scripts/i18n/
cd <目标树> && python3 scripts/i18n/replay_tr.py --apply

# ③ 非机械改动补丁（38 个文件）
git apply patches/功能补丁-非机械改动.patch

# ③.5 界面资源补丁（22 个文件）
git apply patches/功能补丁-界面资源.patch

# ④ 构建层补丁（4 个文件）
git apply patches/功能补丁-构建层.patch
```

> ⚠️ 顺序不可颠倒：③ 的 diff 上下文基于「上游 + ① + ②」的结果。
>
> 上述各步已由 [`scripts/migrate_to_upstream.sh`](../scripts/migrate_to_upstream.sh) 一条命令封装，
> 并附带第 ⑤ 步「新增资产同步」（`translations/`、`share/`、`doc/`、`docs/`、`scripts/`、`resources/`）。
> 手工执行请优先用该脚本，避免漏步。

---

## ③.5 界面资源补丁

### 为什么需要它

迁移的 ①②③ 步有一条**共同的表达边界**：规则表按「原文精确匹配」工作，
只能抓 `.C/.h` 源码里的 `tr()` 包裹。而本仓库还有一类改动完全在这个框架之外：

- **17 个 Qt Designer `.ui` 文件** —— 界面文本汉化、`font-size` 高分屏修正（`px` → `pt`）
- **`src/main.C`** —— `Qt::AA_EnableHighDpiScaling` 属性（高分屏适配）
- **`src/Math/CMakeLists.txt`** —— 链接目标修正（`QGLViewer` → `${QGLVIEWER_LIBRARY}`）

### 少了它会怎样

`.ui` 文件定义的是**界面元素本身**（按钮文字、标签、标题、菜单项）。
少了这一步，源码里的 `tr()` 包裹再完整，这些由 `.ui` 直接写死的文字**依然是英文** ——
表现为"部分界面中文、部分英文"的半汉化状态，且不会报任何错。

> **这个缺口是 2026-10-02 端到端验证时发现的。** 当时 selfcheck 只有 95 项基线，
> 而基线本身由补丁清单生成 —— 也就是说，"用补丁清单做基线"这个做法
> 天然看不见补丁之外的缺口。追查 selfcheck 报出的 2 个不一致文件时，
> 才顺带发现 `.ui` 全类文件（17 个）从未被任何机制覆盖。

### 覆盖的 22 个文件

| 类别 | 数量 | 内容 |
|---|---|---|
| `.ui` 文件 | 17 个 | `<string>` 文本汉化 + stylesheet 的 `font-size: Npx` → `Npt` |
| `src/main.C` | 1 个 | `setAttribute(Qt::AA_EnableHighDpiScaling, true)` |
| `src/Math/CMakeLists.txt` | 1 个 | 链接目标 `QGLViewer` → `${QGLVIEWER_LIBRARY}` |
| （其余） | 3 个 | `Process/` 与 `Process/save/` 下的 JobMonitor/QueueOptions 等 |

### 冲突处理（上游也改了同名 `.ui` 时）

`.ui` 是结构化 XML，冲突通常好认。处理原则：

1. **以上游 `.ui` 为基准**（它可能新增了控件、改了布局）；
2. 重新贴回两处：
   - `<string>` 元素里的中文文本；
   - stylesheet 中 `font-size` 的 `px` → `pt` 修正；
3. `main.C` 与 `Math/CMakeLists.txt` 是单点改动，直接照搬即可。

> 若上游**删除**了某个 `.ui`，该块会失败 —— 此时先确认上游是否把它合并到了别的界面。

---

## ④ 构建层补丁（本目录中最"重"的一个）

### 为什么需要它

迁移的 ①②③ 步覆盖的是 **`src/` 下的源码改动**。但本仓库相对上游还有一类改动
不在源码补丁的表达范围内：

- **上游已有、但被我们整体重写的构建文件** —— `CMakeLists.txt`
  （上游 **224 行** / 本仓库 **646 行**）
- **工程配置类改动** —— `README.md`、`.gitignore`、CI 工作流

### 少了它会怎样

`CMakeLists.txt` 里有一段与汉化直接相关的集成：

```cmake
option(IQMOL_STRICT_L10N "Fail build if zh_CN.ts has unfinished/empty translations" OFF)
find_program(LRELEASE_EXECUTABLE NAMES lrelease lrelease-qt5)
# ... add_custom_command POST_BUILD:
#     lrelease zh_CN.ts -qm <构建目录>/translations/zh_CN.qm
#     + check_l10n_strict.cmake 严格校验
```

不带这个文件，目标树**构建期不会生成 `zh_CN.qm`** → Qt 找不到译文资源 →
**界面静默回退英文**，且不报任何错。这是最难排查的一类迁移事故。

### 覆盖的 4 个文件

| 文件 | 相对上游 | 内容 |
|---|---|---|
| `CMakeLists.txt` | 修改 `+439 / -17` | 汉化集成段 + 十余项 Windows/MinGW 构建修复 |
| `README.md` | 修改 `+194 / -2` | 项目说明中文版 |
| `.gitignore` | 修改 `+49` | 构建产物 / 中间文件忽略规则 |
| `.github/workflows/ubuntu-2404.yml` | 修改 `+4` | CI 增加中文化检查 |

### `CMakeLists.txt` 里除了汉化还包含什么

该文件的改动是**混合**的。除汉化集成段外，还有一批与汉化无关、但 Windows 构建
必需的修复（缺任何一项都会链接失败）：

| 修复项 | 不通的后果 |
|---|---|
| `QGLVIEWER_STATIC` / `YAML_CPP_STATIC_DEFINE` 宏 | 大量 `undefined reference to __imp__ZN9QGLViewer...` |
| OpenGL / GLU 链接目标兜底（`OPENGL_TARGET` / `GLU_TARGET`） | `glStencil*` / `gluNewQuadric` 等符号未定义 |
| `babelconfig.h` 兜底生成 | `elements.h` 包含 `<openbabel/babelconfig.h>` 失败 |
| OpenBabel `BUILD_SHARED` 跟随顶层 `BUILD_SHARED_LIBS` | 插件不被内联，运行时找不到 `.obf` 插件 |
| `WHOLE_ARCHIVE` 静态链接 + 低版本 CMake 降级 | openbabel 静态库符号被链接器丢弃 |
| `STATIC_MAEPARSER` / `STATIC_COORDGEN` 宏 | Maeparser / coordgen 同类链接错误 |
| `additional_sources` 补全 | 静态分支漏加 `asciipainter` 等源文件 |

> 因此这个补丁**不能**被理解为"只加了几行汉化"。它是一个构建体系补丁。

### 冲突处理（上游也改了 `CMakeLists.txt` 时）

上游 224 行 / 本仓库 646 行，差异巨大，**上游一改这个文件，本补丁必然冲突**。
处理原则是 **两边都要保留**：

1. 以上游的新文件为基准（它包含上游的功能修复、新增源文件、依赖调整）；
2. 在其上重新贴上本仓库的两段内容：汉化集成段 + 上表中的各项 Windows 构建修复；
3. 用 `bash scripts/migrate_to_upstream.sh --selfcheck-only --target <目标树>` 复验。

详细步骤见 [`docs/汉化工程/上游升级迁移指南.md`](../docs/汉化工程/上游升级迁移指南.md)。

---

## ③ 非机械改动补丁（技术细节）

本补丁收集**无法由 `replay_tr.py` 规则表重放**的 38 个源文件改动，
是「上游升级迁移」流程的第 ③ 步。

> **2026-10-02 扩充**：由 35 个文件增至 36 个，补入 `src/Main/IQmolApplication.C`
> 与 `src/Qui/InputDialog.C`。这两个文件的改动此前既不在规则表、也不在本补丁内，
> 属端到端验证时查出的漏网项（详见两个补丁的 `.meta.json` `changelog`）。
>
> **2026-10-03 扩充**：增至 38 个，补入 `src/Layer/ComponentLayer.C`、
> `src/Viewer/BuildEfpFragmentHandler.C`、`src/Viewer/BuildMoleculeFragmentHandler.C`、
> `src/Viewer/UndoCommands.h`，并扩充 `src/Layer/MoleculeLayer.C` 与
> `src/Viewer/UndoCommands.C`。修复 9 处未翻译的**撤销/操作命令名**（用户反馈 F1：
> 撤销栈与操作提示显示英文）。这批字符串在 `wrap_tr.rules` 中 **0 命中**、
> 也不在原有补丁集，属「补丁集的缝隙」。
>
> ⚠️ **附带发现的一类新坑**：`lupdate` 只扫描 `.C` / `.ui`，**不扫描 `.h`**。
> 凡写在头文件里的 `tr()` / `QCoreApplication::translate()` 字面量永远抽不进士林表、
> 译文永不生效。因此本批修复把操作名文本**改为由调用点传入**（`MoleculeLayer.C` 的
> `tr("Minimize energy")` 等），`MoveObjects` 的默认文本兜底则**下沉到 `UndoCommands.C`
> 的构造实现**（空串时 `QCoreApplication::translate("UndoCommands", "Move items")`）。

## 实测验证

在上游 `af7ff60` 干净树上执行 ①→②→③→③.5→④→⑤ 后：
- ① 功能补丁：干净应用 ✅
- ② 重放：新增 323 处包裹，55 个文件 ✅
- ③ 非机械改动补丁：干净应用（36 个文件）✅
- ③.5 界面资源补丁：干净应用（22 个文件）✅
- ④ 构建层补丁：干净应用（4 个文件）✅
- ⑤ 资产同步：全部落地 ✅
- **结果：95 / 95 个文件与成果版完全一致（100% 复现）** ✅
  （源码 69 + 界面资源 22 + 构建层 4，去重后 95）

## 为什么这 36 个文件无法机械重放

| 根因 | 说明 | 举例 |
|---|---|---|
| 字面量文本改变 | 上游是拼接式 `"X "` + `s += ...`，我们改成占位符式 `tr("X %1")`；规则表按原文精确查找必然落空 | `MolecularGridEvaluator.C`、`GeometryConstraint.C` |
| 我方新增代码行 | 上游不存在对应字面量，无处可包 | `ShaderDialog.C`（数据/显示分离）、`OrbitalsConfigurator.C` |
| 构造函数初始化列表重构 | 初始化列表中的标签为裸字符串，改由构造体内 `setText(tr(...))` 覆盖 | `CubeDataLayer.C`、`DipoleLayer.C`、`FrequenciesLayer.C` 等 |
| 常量 → 可翻译字面量 | `DefaultMoleculeName` → `"Untitled"` | `MoleculeLayer.C` |
| 非 QObject 类需 `translate()` | 普通 C++ 类无 `tr()`，须 `QCoreApplication::translate("Ctx", ...)` | `HelpBrowser.C`、`OpenBabelParser.C`、`SurfaceType.C`、`JobInfo.C` |

## 覆盖的 38 个文件

- `src/Configurator/ConstraintConfigurator.C`
- `src/Configurator/GeminalOrbitalsConfigurator.C`
- `src/Configurator/MolecularSurfacesConfigurator.C`
- `src/Configurator/MullikenDecompositionsDialog.C`
- `src/Configurator/OrbitalsConfigurator.C`
- `src/Configurator/SurfaceAnimatorDialog.C`
- `src/Data/SurfaceType.C`
- `src/Data/SurfaceType.h`
- `src/Grid/MolecularGridEvaluator.C`
- `src/Layer/ComponentLayer.C` ⬅ 2026-10-03 新增
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
- `src/Viewer/BuildEfpFragmentHandler.C` ⬅ 2026-10-03 新增
- `src/Viewer/BuildMoleculeFragmentHandler.C` ⬅ 2026-10-03 新增
- `src/Viewer/ShaderDialog.C`
- `src/Viewer/UndoCommands.C`
- `src/Viewer/UndoCommands.h` ⬅ 2026-10-03 新增
- `src/Qui/InputDialog.C`

> 注：`src/Main/IQmolApplication.C` 见上方 `src/Main/` 段。

---

> 维护者：@stone-Glitch ｜ 最后整理：2026-10-02
