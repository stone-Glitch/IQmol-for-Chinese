# OpenBabel 构建故障排查（合并版）
> 合并自 4 篇：`2026-09-13-OpenBabel插件加载失败诊断与修复.md`、`2026-09-13-OpenBabel-Windows静态链接undefined-reference诊断.md`、`2026-09-18-OpenBabel静态构建风险全量核对.md`、`2026-09-18-OpenBabel静态链接additional_sources与maeparser宏诊断.md`。
> 平台：Windows / MSYS2 MINGW64 / MinGW GCC 16.2.0；影响版本 IQmol 3.2.3 静态构建（`BUILD_SHARED_LIBS OFF`）；相关提交：`e4f5857`、`5111a63`、`45a09a0`、`dc6a133`、`ded257a`、`c3ff679`。

---

## 一、问题速查表

| 症状（关键报错） | 根因 | 修复方案 | 状态 | 原记录文件 |
|---|---|---|---|---|
| `Failed to load force field: UFF` / `Unable to compute energy` | OpenBabel 私有开关 `BUILD_SHARED` 默认 `ON`，与顶层 `BUILD_SHARED_LIBS` 无关，插件未静态内联 | 在 `add_subdirectory(modules/openbabel)` **之前** `set(BUILD_SHARED OFF CACHE BOOL ... FORCE)` | 已修复 | 2026-09-13-OpenBabel插件加载失败诊断与修复.md |
| `Unable to find OpenBabel plugins. Try setting the BABEL_LIBDIR environment variable.` | 同上：`-DUSING_DYNAMIC_LIBS` 生效，但 `plugin_*` 因 `EXCLUDE_FROM_ALL` 未产出 `.obf` | 同上（静态内联后不再需要 `BABEL_LIBDIR`） | 已修复 | 同上 |
| 插件内联后 UFF 仍找不到，**编译链接启动全程无报错** | GNU ld 按符号引用提取静态库成员，纯「全局构造副作用」的 `.o` 被整体丢弃 | `-Wl,--whole-archive openbabel -Wl,--no-whole-archive` | 已修复 | 同上 |
| `No rule to make target 'modules/openbabel/src/libopenbabel.a', needed by 'bin/IQmol.exe'` | 首版用 `$<TARGET_FILE:openbabel>` 把真实路径写进 `link.txt`，绕过 CMake 依赖跟踪 | 改用**目标名** `openbabel` 书写 + `add_dependencies()` | 已修复 | 同上 |
| `undefined reference to OpenBabel::ASCIIPainter::*` / `CommandPainter::*` / `NMReadWLN` | 上游静态分支循环只加 `formats/${format}.cpp`，漏加 `${${format}_additional_sources}` | 整份替换 `openbabel/src/CMakeLists.txt` 为修复版（构建脚本步骤 2d 自动执行） | 已修复（待 Windows 端 `--clean` 复验） | 2026-09-18-OpenBabel静态链接additional_sources与maeparser宏诊断.md |
| `undefined reference to __imp__ZN11schrodinger3mae6Reader...` | maeparser 以 `PRIVATE` 定义 `STATIC_MAEPARSER` 不传播给消费者，符号带 `__imp_` | 顶层 `add_compile_definitions(STATIC_MAEPARSER)`（`CMakeLists.txt:183`） | 已修复 | 同上 |
| 早期记录给出的宏名 `MAEPARSER_STATIC_DEFINE` | 该名字在 maeparser v1.2.3 源码中 `grep` **零命中**，从未生效 | 更正为 `STATIC_MAEPARSER`；**旧记录结论已过时** | 已修正 | 2026-09-13-OpenBabel-Windows静态链接undefined-reference诊断.md |
| coordgen 的 `STATIC_COORDGEN` 同为 `PRIVATE` | 同类导出宏缺陷 | 暂不处理；将来若打开 `WITH_COORDGEN` 需同步定义 | 仍需注意（当前不触发） | 2026-09-18-OpenBabel静态构建风险全量核对.md |
| 部署自检每次误报缺 `MMFF94.prm` | MMFF94 参数表编译进二进制，`data/` 下本无此文件 | 不列入自检名单 | 已修复 | 2026-09-13-OpenBabel插件加载失败诊断与修复.md |
| 静态内联构建下 `lib/openbabel/` 无插件被判为异常 | 静态构建本就不产出 `.obf` | 脚本改为：无 `.obf` 属正常；出现 `.obf` 反而告警「构建被误配为动态」 | 已修复 | 同上 |
| 怀疑 `BABEL_DATADIR` / 数据缺失 | 实测数据齐备（63 个文件），报错文案具有**误导性** | 问题不在数据，见 §2 | 已排除 | 同上 |

---

## 二、两个 `BUILD_SHARED` 互不相干 → 插件既没内联、磁盘上又找不到

### 现象

```
Failed to load force field: UFF
Unable to compute energy
BABEL_DATADIR environment variable may not be set correctly.

*** Open Babel Error  in LoadAllPlugins
  Unable to find OpenBabel plugins. Try setting the BABEL_LIBDIR environment variable.
```

代码位置：`src/Layer/MoleculeLayer.C:2080-2095`（`OBForceField::FindForceField(obff)` 返回 `NULL`）、`modules/openbabel/src/plugin.cpp:62`。

### 排查过程

两条报错是**同一根因的两个层次**：① 力场找不到；② 插件没被编进程序、运行期去磁盘找。先排除数据/路径问题（文案把矛头指向 `BABEL_DATADIR`，实测数据齐备）：`build/share/openbabel/` 与 `modules/openbabel/data/` 各 **63** 个文件；`build/share/openbabel/UFF.prm` 存在（12573 字节）；构建产物中 `.obf` 插件文件数 **0**。

`modules/openbabel/src/tokenst.cpp:192` `OpenDatafile()` 查找顺序：① 当前工作目录 ② `${BABEL_DATADIR}/<BABEL_VERSION>/<文件名>` ③ `${BABEL_DATADIR}/<文件名>`，第 3 条扁平目录本身可用；`IQmolApplication.C:198-207` 在 Windows 下已正确设置 `BABEL_DATADIR`。**结论：报错文案是误导性的，问题不在数据文件也不在路径。**

### 根因

| 变量 | 定义位置 | 改动前的值 | 作用范围 |
|---|---|---|---|
| `BUILD_SHARED_LIBS` | IQmol 顶层 `CMakeLists.txt:17` | `OFF` | 决定 IQmol 各模块编成静态库 |
| `BUILD_SHARED` | `modules/openbabel/CMakeLists.txt:105` `option(... ON)` | **`ON`** | 决定 OpenBabel 是否动态构建 |

`option(BUILD_SHARED ...)` 与标准变量 `BUILD_SHARED_LIBS` **无任何自动关联**。`modules/openbabel/CMakeLists.txt:110-118`：

```cmake
if(BUILD_SHARED)
  set(BUILD_TYPE SHARED)
  set(PLUGIN_TYPE MODULE)
  add_definitions(-DUSING_DYNAMIC_LIBS)     # ← 关键
```

`USING_DYNAMIC_LIBS` 一旦定义，`src/plugin.cpp:46` 的 `LoadAllPlugins()` 就进入动态分支，去 `BABEL_LIBDIR` 找文件、找不到即报 ②；而 `#else` 静态分支是 `count = 1;` 直接跳过、无任何报错。同时 `src/CMakeLists.txt:288-304` 把插件编成独立 MODULE（Windows 后缀 `.obf`），这些 `.obf` **既没被 IQmol 链接，也没被 `install()`/部署**。

`find build -name "*.obf"` 返回 0 的原因是 `add_subdirectory(modules/openbabel EXCLUDE_FROM_ALL)`：`plugin_*` 不属默认构建目标，`make` 不构建它们 —— **编译宏生效了，产物却没生成**。

**为什么 Linux 不暴露**：Linux 构建中 `openbabel` 目标解析到系统动态库 `/usr/lib/x86_64-linux-gnu/libopenbabel.so.7.0.0`（系统包自带完整插件），根本不走嵌入静态分支。

### 解决方案（提交 `e4f5857`）

```cmake
if (NOT BUILD_SHARED_LIBS)
   set(BUILD_SHARED OFF CACHE BOOL "OpenBabel: build shared library + dynamic plugins" FORCE)
else()
   set(BUILD_SHARED ON CACHE BOOL "OpenBabel: build shared library + dynamic plugins" FORCE)
endif()

add_subdirectory(modules/openbabel  EXCLUDE_FROM_ALL)
```

要点：**必须在 `add_subdirectory` 之前** —— `option()` 对已存在的 cache 变量不覆盖，放之后则子模块已用默认 `ON` 完成配置；用 `CACHE ... FORCE` 覆盖上一次配置遗留的缓存值。修复后静态构建下插件源码在 `modules/openbabel/src/CMakeLists.txt:197-199` 并入 `openbabel_srcs`（`foreach(plugingroup descriptors fingerprints forcefields ops charges) set(openbabel_srcs ${openbabel_srcs} ${${plugingroup}})`），`USING_DYNAMIC_LIBS` 不再定义，运行期不再需要 `BABEL_LIBDIR`。

### 结论

修复是**两层叠加**、缺一不可：`e4f5857`（同步 `BUILD_SHARED`，让插件被编进程序，根治 ②）+ `45a09a0`（`--whole-archive`，让已编入的注册对象不被丢弃，防护 ①）。只有前者则插件会被链接器丢弃；只有后者则插件根本没进静态库。

**来源：2026-09-13-OpenBabel插件加载失败诊断与修复.md**

---

## 三、静态插件注册对象被链接器静默丢弃

### 现象与排查（最小复现工程）

插件内联后 UFF 仍 `FindForceField("UFF")` 返回 `NULL`。**静默失效：编译、链接、启动全程无任何报错。** 把「注册对象」与「查找函数」拆到**不同**目标文件，还原被丢弃的条件：

```cpp
// registry.cpp（被 main 引用）
std::map<std::string,int>& Reg() { static std::map<std::string,int> m; return m; }
// uff.cpp（全局自注册，无任何外部引用）
std::map<std::string,int>& Reg();
struct AutoReg { AutoReg(const char* n){ Reg()[n]=1; } };
namespace { AutoReg theUFF("UFF"); }
// main.cpp
int main(){ printf("UFF found: %s\n", Reg().count("UFF") ? "YES" : "NO"); }
```

| 链接方式 | 运行结果 |
|---|---|
| 普通链接 `-lplug` | `UFF found: NO` ← **精确复现用户现象** |
| `-Wl,--whole-archive ./libplug.a -Wl,--no-whole-archive` | `UFF found: YES` ← **修复生效** |

### 根因

OpenBabel 插件采用**全局对象自注册**，`modules/openbabel/src/forcefields/forcefielduff.cpp:579`：

```cpp
//Make a global instance
OBForceFieldUFF theForceFieldUFF("UFF", true);
```

构造函数把实例写入 `OBForceField::Map()` 静态表（`include/openbabel/plugin.h` 的 `MAKE_PLUGIN` 宏）。插件内联后这些 `.cpp` 成为静态库成员目标文件，而 GNU ld 提取静态库成员的唯一依据是**符号引用** —— `forcefielduff.o` 中不存在被任何地方引用的符号，其全部作用是全局构造函数的副作用，于是被整体丢弃，自注册从未执行。

### 解决方案（提交 `45a09a0`）

```cmake
if (WIN32 AND NOT BUILD_SHARED_LIBS)
   if (TARGET openbabel)
      target_link_libraries (${targetName}
         -Wl,--whole-archive
         openbabel
         -Wl,--no-whole-archive
      )
      add_dependencies(${targetName} openbabel)
   endif()
else()
   if (NOT BUILD_SHARED_LIBS AND TARGET openbabel)
      # 同上的 -Wl,--whole-archive openbabel -Wl,--no-whole-archive + add_dependencies
   else()
      target_link_libraries (${targetName} openbabel)
   endif()
endif()
```

即非 WIN32 的静态分支写法与 WIN32 完全一致，动态分支则退化为裸链接 `openbabel`；同时移除原链接列表中裸写的 `openbabel`，避免重复链接。

### 结论

凡采用「全局对象自注册」模式的库（OpenBabel 插件、Qt 静态插件、各类 factory 注册表）静态链接时都必须用 `--whole-archive` 包裹，或用 `--undefined=<符号>` 强制拉入。

**来源：2026-09-13-OpenBabel插件加载失败诊断与修复.md**

---

## 四、踩坑：`$<TARGET_FILE:openbabel>` 导致 No rule to make target

### 现象与根因

```
mingw32-make[2]: *** No rule to make target
    'modules/openbabel/src/libopenbabel.a', needed by 'bin/IQmol.exe'.  Stop.
```

`--whole-archive` 首版写法用生成器表达式 `"$<TARGET_FILE:openbabel>"`（提交 `5111a63`）。它把库的**真实文件路径**直接写进 `link.txt`，**绕过 CMake 的目标依赖跟踪**；而 `openbabel` 以 `EXCLUDE_FROM_ALL` 方式引入（不属默认 `all` 目标），MinGW Makefile 后端因此找不到生成该文件的规则。

### 解决方案（提交 `45a09a0`）

用**目标名** `openbabel` 书写，由 CMake 自动建立依赖边并解析为相对构建目录的库路径，同时补 `add_dependencies()` 双保险。实测 `link.txt`：

```
-Wl,--whole-archive sub/libsub.a -Wl,--no-whole-archive
```

### 结论

在 `target_link_libraries` 中混写选项与目标名时，CMake **保持书写顺序**输出到链接行；但**只要用了 `$<TARGET_FILE:...>`，就等于放弃了依赖管理** —— 对 `EXCLUDE_FROM_ALL` 引入的子模块尤其致命。

**来源：2026-09-13-OpenBabel插件加载失败诊断与修复.md**

---

## 五、静态分支漏加 `additional_sources` → ASCIIPainter / CommandPainter / NMReadWLN

### 现象（`--whole-archive` 已生效，`linkLibs.rsp` 中 openbabel 被整段保留）

```
libopenbabel.a(asciiformat.cpp.obj): undefined reference to `OpenBabel::ASCIIPainter::ASCIIPainter(int, int, double)'
libopenbabel.a(asciiformat.cpp.obj): undefined reference to `OpenBabel::ASCIIPainter::DrawLine(...)'
libopenbabel.a(painterformat.cpp.obj): undefined reference to `OpenBabel::CommandPainter::CommandPainter(std::ostream&)'
libopenbabel.a(wlnformat.cpp.obj): undefined reference to `NMReadWLN(char const*, OpenBabel::OBMol*)'
```

**关键观察**：引用方与被引用方**都在 `libopenbabel.a` 内部** —— 库已被整段保留，但这些符号**根本没被编进库**。

### 排查过程

`modules/openbabel/src/CMakeLists.txt` 第 184-188 行静态构建分支：

```cmake
else(BUILD_SHARED)
  include(formats/formats.cmake)
  foreach(format ${formats})
    set(openbabel_srcs ${openbabel_srcs} formats/${format}.cpp)     # ← 只加了主 .cpp
  endforeach(format ${formats})
```

而实现文件定义在 `formats/formats.cmake` 的 `<format>_additional_sources`：

```cmake
22:  set(painterformat_additional_sources ../depict/commandpainter.cpp)
23:  set(asciiformat_additional_sources   ../depict/asciipainter.cpp)
148: set(wlnformat_additional_sources    wln-nextmove.cpp)
172: set(png2format_additional_sources   ../depict/cairopainter.cpp)   ← 条件格式
205: set(inchiformat_additional_sources  getinchi.cpp ../ops/unique.cpp)
```

CMake 真实展开验证（静态构建，`BUILD_SHARED=OFF`），泄漏点只有 3 个：

```
asciiformat   -> ../depict/asciipainter.cpp
painterformat -> ../depict/commandpainter.cpp
wlnformat     -> wln-nextmove.cpp
（png2format / inchiformat 在静态默认配置下不出现）
```

路径存在性（相对 `src/formats/` 解析）：三个文件全部 `OK`。依赖闭合性：`NMReadWLN` 定义于 `wln-nextmove.cpp:2177`，声明/调用于 `wlnformat.cpp:23,144`；`ASCIIPainter` 定义于 `depict/asciipainter.cpp` 被 `asciiformat.cpp` 使用；`CommandPainter` 定义于 `depict/commandpainter.cpp` 被 `painterformat.cpp` 使用。

### 根因

上游 OpenBabel 在「静态构建 + formats 分组」路径上的缺陷（与 IQmol 无关）：静态分支循环只加主 `.cpp`，三个实现文件从未参与编译。

> 对照：共享构建走 `formats/CMakeLists.txt`（第 40-42 行），那里是带 `${${format}_additional_sources}` 的，故共享构建不受影响。

### 解决方案（提交 `c3ff679`）

| 文件 | 改动 |
|---|---|
| `scripts/openbabel_src_CMakeLists.txt`（新增） | 上游 `openbabel/src/CMakeLists.txt` 修复版：静态分支循环补 `${${format}_additional_sources}`（跳过 inchiformat 以免与 `WITH_STATIC_INCHI` 分支重复） |
| `scripts/build_windows.sh` | 新增步骤 2d：检测并替换 `openbabel/src/CMakeLists.txt`；指纹增加 `OB_SRC_ADDITIONAL` / `OB_ROOT_PATCHED` 两项 |

修复后 CMake 展开验证：

```
formats/painterformat.cpp;../depict/commandpainter.cpp
formats/asciiformat.cpp;../depict/asciipainter.cpp
formats/wlnformat.cpp;wln-nextmove.cpp
```

### 结论

本问题**独立于** `ded257a`（`$<LINK_LIBRARY:WHOLE_ARCHIVE>`）之外，是第二层原因：第一层解决「库被整段保留」，本层解决「符号根本没被编进库」，两层都需要。另因修复方式是**整份替换**上游 `src/CMakeLists.txt`，解压 submodules 离线包会把它覆盖回未修版 —— 步骤 2d 会自动重新修复（与已有的 openbabel 根 CMakeLists 修复步骤 2b 机制一致）。

**来源：2026-09-18-OpenBabel静态链接additional_sources与maeparser宏诊断.md / 2026-09-18-OpenBabel静态构建风险全量核对.md**

---

## 六、maeparser 导出宏：宏名写错 + `PRIVATE` 不传播 → `__imp_` 符号

### 现象与排查

```
libopenbabel.a(maeformat.cpp.obj): undefined reference to `__imp__ZN11schrodinger3mae6ReaderC1ESt10shared_ptrISiEy'
```

`__imp_` 前缀表明符号被当作 **DLL 导入**。缺失的 `schrodinger::mae::*` 涉及 Reader / Writer / Block。`schrodinger::mae` 命名空间来自 OpenBabel **捆绑的独立 maeparser 库**（MAE 分子格式），`maeformat.cpp` 包含 `<maeparser/Reader.hpp>` 等头文件，不在 `openbabel` 自身源码里。查 maeparser v1.2.3 `MaeParserConfig.hpp:3`：

```cpp
#ifndef STATIC_MAEPARSER                    // ← 宏名是 STATIC_MAEPARSER
#ifdef IN_MAEPARSER
  #define EXPORT_MAEPARSER __declspec(dllexport)
#else
  #define EXPORT_MAEPARSER __declspec(dllimport)   // 消费者侧默认 DLL 导入
#endif
#else
  #define EXPORT_MAEPARSER                    // 静态：展开为空
#endif
```

而 `maeparser/CMakeLists.txt:37` 只做了：

```cmake
target_compile_definitions(maeparser PRIVATE "STATIC_MAEPARSER")   # ← PRIVATE，不传播
```

规模：maeparser 头文件中共 **27 处** `EXPORT_MAEPARSER`（`Buffer.hpp`、`MaeBlock.hpp`、`Reader.hpp`、`Writer.hpp` 等），全部会变成 `__imp_` 引用。

### 根因

1. **`PRIVATE` 不会传播给消费者**：openbabel 的 `maeformat.cpp` 编译时 `STATIC_MAEPARSER` 未定义，`EXPORT_MAEPARSER` 展开为 `__declspec(dllimport)`，产生 `__imp_` 前缀符号，与静态 `.a` 中的实际符号名不匹配。
2. **IQmol 之前定义的宏名是错的**：`MAEPARSER_STATIC_DEFINE` 在整个 maeparser v1.2.3 源码中 `grep` **零命中**，从未生效。正确宏名是 **`STATIC_MAEPARSER`**。

### 解决方案（提交 `c3ff679`）

| 文件 | 改动 |
|---|---|
| `CMakeLists.txt:183` | `add_compile_definitions(MAEPARSER_STATIC_DEFINE)` → `add_compile_definitions(STATIC_MAEPARSER)` |
| `CMakeLists.txt`（`add_subdirectory(modules/openbabel)` 之前，且 `NOT BUILD_SHARED_LIBS` 时） | 定义 `STATIC_MAEPARSER`，让 maeparser 子目录继承；若 maeparser 是独立 CMake 目标，一并用 `--whole-archive` 整体保留 |
| `scripts/build_windows.sh` | 把该宏纳入配置指纹（`BUILD_SHARED_SYNC` / `WHOLE_ARCHIVE` / `MAEPARSER_STATIC`），否则用户本地已有 `--whole-archive` 时指纹不变、不会重配，宏不生效 |

### 结论

`MaeParserConfig.hpp` 用 `GenerateExportHeader` 生成导出宏；Windows 静态构建下若未被告知「静态使用」，默认按 `__declspec(dllimport)` 处理外部符号，必然与静态库符号不匹配。

> 注：本仓离线子模块包**不含** maeparser（与用户机器上的完整子模块不同），故本仓 Linux 构建无法复现；诊断基于错误信息与 OpenBabel 3.1.1 源码结构推演。

**来源：2026-09-18-OpenBabel静态链接additional_sources与maeparser宏诊断.md / 2026-09-18-OpenBabel静态构建风险全量核对.md / 2026-09-13-OpenBabel-Windows静态链接undefined-reference诊断.md（该篇宏名结论已被更正）**

---

## 七、同类导出宏风险全量核对

| 库 | 宏名 | 证据 | IQmol 处理 |
|---|---|---|---|
| yaml-cpp | `YAML_CPP_STATIC_DEFINE` | `yaml-cpp/include/yaml-cpp/dll.h:10` | ✅ `CMakeLists.txt:31` |
| libQGLViewer | `QGLVIEWER_STATIC` | `libQGLViewer/QGLViewer/config.h` | ✅ `CMakeLists.txt:31` |
| maeparser | `STATIC_MAEPARSER` | `MaeParserConfig.hpp:3` | ✅ `CMakeLists.txt:183` |

**coordgen（同类缺陷，当前不触发）**：`CoordgenConfig.hpp` 用 `STATIC_COORDGEN`，`coordgenlibs/CMakeLists.txt:59` 同样是 `target_compile_definitions(coordgen PRIVATE "STATIC_COORDGEN")`。不触发理由：① `WITH_COORDGEN` 在静态构建下默认为 `OFF`（`openbabel/CMakeLists.txt:480-481`：`if(BUILD_SHARED) ... ON / else() ... OFF`），coordgen 根本不会被 `add_subdirectory`；② `grep -rn "coordgen" openbabel/src/` **零命中**，即使构建也不会产生 `__imp_` 消费点。**结论：无需处理。若将来有人把 `WITH_COORDGEN` 打开，需同步定义 `STATIC_COORDGEN`。**

**完整性与存在性核对**：

| 核对项 | 结果 |
|---|---|
| 格式列表（`include(formats.cmake)` 真实展开） | `formats` 共 **106** 项，逐一核对 `formats/<name>.cpp` 全部存在，**0 缺失** |
| 全部源文件（修复后收集逻辑） | **109** 个（106 format 主文件 + 3 个 additional_sources），**109/109 存在，0 缺失** |
| rapidjson | 纯头文件，无风险 |

> 注：`APIInterface` / `chemdrawct` 虽不含 `format` 后缀，但确实是 `formats/` 下的合法格式成员（文件存在），会正常参与编译。

**核对结论**：

| 状态 | 项 |
|---|---|
| **已修复（`c3ff679`）** | ① `additional_sources` 漏加（3 文件）② maeparser 宏名错误 |
| **已确认无风险** | ③ 格式列表完整性 ④ 源文件存在性 ⑤ yaml-cpp / libQGLViewer 宏 ⑥ rapidjson |
| **已知但当前不触发** | ⑦ coordgen 的 `STATIC_COORDGEN` PRIVATE 问题 |

预期：下一次 `--clean` 构建链接期不应再出现 undefined reference；若仍有残留，仅剩可能性是外部系统库（Boost / libxml2 / zlib 等）的静态/动态混用，属另一类（环境依赖），可另行排查。

**来源：2026-09-18-OpenBabel静态构建风险全量核对.md**

---

## 八、部署侧加固与 Windows 复现步骤

### 8.1 `scripts/deploy_windows.sh` 加固项

| 加固项 | 说明 |
|---|---|
| 双布局数据目录 | 同时铺 `share/openbabel/`（扁平）与 `share/openbabel/<版本>/`（版本子目录）。版本号从 `modules/openbabel/CMakeLists.txt` 的 `BABEL_MAJ_VER` / `BABEL_MIN_VER` / `BABEL_PATCH_VER` 解析，当前得出 `3.1.1`，解析失败时回退为 `3.1.1` |
| 力场参数自检 | 检查 `UFF.prm` / `ghemical.prm` / `gaff.prm` / `mm2.prm`，缺失即告警 |
| 自检名单修正 | **不**把 `MMFF94.prm` 列入自检 —— MMFF94 参数表编译进二进制，`data/` 目录下本就没有该文件，列入会导致每次部署误报 |
| 插件目录逻辑修正 | 静态内联构建下 `lib/openbabel/` 无插件属**正常**，不再误导；若确实发现 `.obf` 则说明构建被误配为动态模式，给出明确告警 |

### 8.2 Windows 端复现 / 验证步骤

```bash
cd /d/IQmol/IQmol-src
curl -sLo CMakeLists.txt "https://ghfast.top/https://raw.githubusercontent.com/stone-Glitch/IQmol-for-Chinese/master/CMakeLists.txt"
curl -sLo scripts/deploy_windows.sh "https://ghfast.top/https://raw.githubusercontent.com/stone-Glitch/IQmol-for-Chinese/master/scripts/deploy_windows.sh"

# 两个修复点都要能看到
grep -n "whole-archive" CMakeLists.txt      # 应看到 4 处以上
grep -n "BUILD_SHARED OFF CACHE" CMakeLists.txt

rm -f build/CMakeCache.txt                  # 只删缓存，不要删整个 build
bash scripts/build_windows.sh
bash scripts/deploy_windows.sh
cd build/bin && ./IQmol.exe
```

第二轮（additional_sources / maeparser）**必须 `--clean`** 以重跑 configure：`bash scripts/build_windows.sh --clean`。

预期：

| 阶段 | 应看到 |
|---|---|
| configure | `[IQmol] 已对 openbabel 启用 --whole-archive`（若 maeparser 为独立目标，还有 `[IQmol] 已对 maeparser 启用 --whole-archive`） |
| 编译 | 时间明显变长（所有格式插件改为内联编译，属预期）；`asciipainter.cpp` / `commandpainter.cpp` / `wln-nextmove.cpp` 出现编译行 |
| 链接 | 不再出现 `ASCIIPainter` / `CommandPainter` / `NMReadWLN` / `__imp_...schrodinger3mae`；`[100%] Built target IQmol`，产物 `build/bin/IQmol.exe` |
| 部署 | `力场参数已就位: UFF.prm / ghemical.prm / gaff.prm / mm2.prm` |
| 部署 | `OpenBabel 为静态内联构建（无 .obf），lib/openbabel/ 无需插件文件` |
| 运行 | 不再出现 `Unable to find OpenBabel plugins`；执行能量计算不再出现 `Failed to load force field: UFF` |

构建脚本步骤 2d 应打印「检测到 openbabel/src/CMakeLists.txt 静态分支漏加 additional_sources，自动修复」。

### 8.3 最小工程验证 `BUILD_SHARED` 同步

顶层 `set(BUILD_SHARED_LIBS OFF)` 后 `set(BUILD_SHARED OFF CACHE BOOL "ob" FORCE)`，再 `add_subdirectory(sub EXCLUDE_FROM_ALL)`；`sub/CMakeLists.txt`（模拟 openbabel 子模块）里 `option(BUILD_SHARED "enable shared build support" ON)`，`if(BUILD_SHARED)` 则 `add_definitions(-DUSING_DYNAMIC_LIBS)` 并打印「插件需外部加载 << 故障态」，否则打印「插件静态内联 (USING_DYNAMIC_LIBS 未定义) << 修复后」。

实测输出 `-- 子模块: BUILD_SHARED=OFF -> 插件静态内联 (USING_DYNAMIC_LIBS 未定义)  << 修复后`；修复前该行应为 `BUILD_SHARED=ON`（未同步时 `option` 的默认值）。

Linux 全量构建侧：`--whole-archive` 生效、链接通过、`Generated 1519 translation(s) (1519 finished and 0 unfinished)`。

### 8.4 回退方案

若 `STATIC_MAEPARSER` 未覆盖实际宏名（极少数 OpenBabel 分支用不同导出宏），可改用 **OpenBabel 共享构建**：`BUILD_SHARED` 设 `ON`，IQmol 链接 `openbabel` 导入库，运行时随 `openbabel-3.dll` / `maeparser.dll` 加载。代价是需在 `deploy_windows.sh` 中正确部署 DLL、插件 `.obf` 与 `BABEL_LIBDIR` / `BABEL_DATADIR`（否则会回到「Unable to find OpenBabel plugins」）。

**来源：2026-09-13-OpenBabel插件加载失败诊断与修复.md / 2026-09-13-OpenBabel-Windows静态链接undefined-reference诊断.md / 2026-09-18-OpenBabel静态链接additional_sources与maeparser宏诊断.md**

---

## 九、附带记录：OpenBabel 上游的一处笔误

`modules/openbabel/src/data.cpp:685` 在 `if` 内重新声明了同名变量（内层 `string fn_open` 是**新的局部变量**，离开 `if` 作用域即销毁，外层 `fn_open` 始终为 `""`，导致随后的判断恒为假）：

```cpp
string fn_open = OpenDatafile(ifs, _filename, _envvar);
if (fn_open == "")
   string fn_open = OpenDatafile(ifs, _filename, _subdir);   // ← 重新声明，遮蔽外层
if (fn_open != "" && (ifs))   // ← 恒为假
```

**不影响本次问题**（UFF 走 `forcefielduff.cpp:1616` 中独立的 `OpenDatafile` 调用，不经过 `OBGlobalDataBase::Init()`），但排查 OpenBabel 数据加载问题时需注意，避免被带偏。

**来源：2026-09-13-OpenBabel插件加载失败诊断与修复.md**

---

## 十、经验沉淀

1. **子模块私有开关不会跟随 CMake 标准变量。** 第三方库若用 `option(BUILD_SHARED ...)` 之类的私有开关控制动态/静态构建，顶层设置标准的 `BUILD_SHARED_LIBS` 对它**无效**。嵌入构建前必须显式同步这些私有开关，且**必须放在 `add_subdirectory()` 之前**并用 `CACHE ... FORCE`（`option()` 不覆盖已存在的 cache 变量）。

2. **编译宏生效 ≠ 产物生成。** 本次最隐蔽的一点：`EXCLUDE_FROM_ALL` 让 `plugin_*` 目标不参与默认构建，磁盘上没有任何 `.obf`，但 `-DUSING_DYNAMIC_LIBS` 已生效，程序按「应从磁盘加载插件」的逻辑运行必然失败。排查时**不能只看产物有无，必须同时核对编译宏**。

3. **静态库中「只有全局构造函数副作用」的目标文件会被静默丢弃。** 凡采用「全局对象自注册」模式的库（OpenBabel 插件、Qt 静态插件、各类 factory 注册表），静态链接时都必须用 `--whole-archive` 包裹或用 `--undefined=<符号>` 强制拉入。这类问题**不会在编译链接期报错**，只表现为运行期「功能莫名其妙不存在」，且常被误导到配置/路径方向 —— 本次两条报错文案（都在提示设置环境变量）恰好都是**误导性的**。

4. **`--whole-archive` 只解决「保留」，不解决「编进来」；`target_link_libraries` 里也不要用 `$<TARGET_FILE:...>`。** 链接期报 undefined reference 时先判断引用方与被引用方是否在同一 `.a` 内：若在，说明 `--whole-archive` 已生效，问题在源文件收集（如上游静态分支漏加 `${${format}_additional_sources}`）而非链接器丢弃。另外 `$<TARGET_FILE:...>` 会把真实路径写进 `link.txt`、绕过 CMake 目标依赖跟踪，对 `EXCLUDE_FROM_ALL` 子模块表现为 `No rule to make target`，应写目标名并补 `add_dependencies()`。

5. **静态链接时外部库的导出宏必须显式告知「静态使用」，且宏名要以源码 `grep` 为准。** maeparser 的正确宏名是 `STATIC_MAEPARSER`（`MaeParserConfig.hpp:3`，头文件 27 处 `EXPORT_MAEPARSER`），而 `MAEPARSER_STATIC_DEFINE` 零命中、从未生效；同时上游 `target_compile_definitions(... PRIVATE ...)` **不会传播给消费者**，必须在顶层定义。coordgen 的 `STATIC_COORDGEN` 属同类隐患，当前因 `WITH_COORDGEN=OFF` 且不被引而不触发。

6. **改构建配置后必须清缓存重配，并对上游文件修复做兜底。** 新增编译宏 / `--whole-archive` 后若配置指纹不变则不会重跑 configure，旧 `link.txt` 会沿用 —— 需删除 `build/CMakeCache.txt`（或整个 build 目录），并把新开关纳入构建脚本指纹（`BUILD_SHARED_SYNC` / `WHOLE_ARCHIVE` / `OB_SRC_ADDITIONAL` / `OB_ROOT_PATCHED`）。对上游文件的**整份替换**型修复还需在脚本中做「解压离线包后自动重新修复」的兜底。
