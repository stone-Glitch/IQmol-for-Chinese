# OpenBabel 静态构建风险清单（全量核对，2026-09-18）

**目的**：在 Windows 侧编译之前，把所有同类坑一次性找出来，避免反复试错。
**方法**：以 CMake 真实展开 + 源码逐一核对，每条给出文件与行号证据。
**核对对象**：`modules/openbabel`（含 external 的 maeparser / coordgen / rapidjson）。

---

## 一、风险类别总览

| # | 风险类别 | 命中项 | 状态 |
|---|---|---|---|
| 1 | 源文件收集遗漏（静态分支漏加 `additional_sources`） | 3 个文件 | ✅ 已修（c3ff679） |
| 2 | 外部库导出宏为 `PRIVATE`，不传播给消费者（`__imp_`） | maeparser | ✅ 已修（c3ff679） |
| 2b | 同上，coordgen | 1 个 | ⚠️ 当前不触发（见 §3） |
| 3 | 同类导出宏（yaml-cpp / libQGLViewer） | 2 个 | ✅ 早已覆盖 |
| 4 | 格式列表完整性 | 106/106 | ✅ 无遗漏 |
| 5 | 源文件路径存在性 | 109/109 | ✅ 无缺失 |

---

## 二、风险 1：`additional_sources` 收集遗漏（已修）

**证据**：`modules/openbabel/src/formats/formats.cmake`

```
22: set(painterformat_additional_sources ../depict/commandpainter.cpp)
23: set(asciiformat_additional_sources   ../depict/asciipainter.cpp)
148: set(wlnformat_additional_sources    wln-nextmove.cpp)
172: set(png2format_additional_sources   ../depict/cairopainter.cpp)   ← 条件格式
205: set(inchiformat_additional_sources  getinchi.cpp ../ops/unique.cpp) ← 另一分支已显式处理
```

**上游缺陷**：`modules/openbabel/src/CMakeLists.txt` 第 186-188 行静态分支循环
只加了 `formats/${format}.cpp`，未加 `${${format}_additional_sources}`。

**CMake 真实展开验证**（静态构建，`BUILD_SHARED=OFF`）：

```
asciiformat   -> ../depict/asciipainter.cpp
painterformat -> ../depict/commandpainter.cpp
wlnformat     -> wln-nextmove.cpp
（仅这 3 个；png2format / inchiformat 在静态默认配置下不出现）
```

**最终路径存在性**（相对 `src/formats/` 解析）：

```
OK  src/depict/asciipainter.cpp
OK  src/depict/commandpainter.cpp
OK  src/formats/wln-nextmove.cpp
```

**依赖闭合性**：
- `NMReadWLN` 定义于 `wln-nextmove.cpp:2177`，声明/调用于 `wlnformat.cpp:23,144`——收集该文件后闭合。
- `ASCIIPainter` 定义于 `depict/asciipainter.cpp`，被 `asciiformat.cpp` 使用。
- `CommandPainter` 定义于 `depict/commandpainter.cpp`，被 `painterformat.cpp` 使用。

---

## 三、风险 2：maeparser 导出宏（已修）

**证据**：maeparser v1.2.3 `MaeParserConfig.hpp:3`

```cpp
#ifndef STATIC_MAEPARSER               // ← 宏名 STATIC_MAEPARSER
  #ifdef IN_MAEPARSER
    #define EXPORT_MAEPARSER __declspec(dllexport)
  #else
    #define EXPORT_MAEPARSER __declspec(dllimport)   // 消费者侧
  #endif
#else
  #define EXPORT_MAEPARSER                // 静态：空
#endif
```

**缺陷**：`maeparser/CMakeLists.txt:37`

```cmake
target_compile_definitions(maeparser PRIVATE "STATIC_MAEPARSER")   # PRIVATE 不传播
```

消费者 `maeformat.cpp` 看不到该宏 → `EXPORT_MAEPARSER` 展开为 `dllimport` → `__imp_` 符号。

**规模**：maeparser 头文件中共 **27 处** `EXPORT_MAEPARSER`（`Buffer.hpp`、`MaeBlock.hpp`、
`Reader.hpp`、`Writer.hpp` 等），全部会变成 `__imp_` 引用。

**修复**：IQmol 顶层 `CMakeLists.txt:183` 定义 `STATIC_MAEPARSER`（在 `add_subdirectory` 之前）。
> 旧值 `MAEPARSER_STATIC_DEFINE` 在整个 maeparser 源码中 **grep 零命中**，从未生效。

### 附：coordgen（同类缺陷，当前不触发）

**证据**：coordgenlibs `CoordgenConfig.hpp`

```cpp
#ifndef STATIC_COORDGEN
  #ifdef WIN32
    #ifdef IN_COORDGEN
      #define EXPORT_COORDGEN __declspec(dllexport)
    #else
      #define EXPORT_COORDGEN __declspec(dllimport)
    #endif
#else
  #define EXPORT_COORDGEN
#endif
```

**缺陷**：`coordgenlibs/CMakeLists.txt:59`
```cmake
target_compile_definitions(coordgen PRIVATE "STATIC_COORDGEN")   # ⚠️ 同样的 PRIVATE 模式
```

**为何当前不触发**：
1. `WITH_COORDGEN` 在静态构建下默认为 `OFF`（`openbabel/CMakeLists.txt:480-481`：
   `if(BUILD_SHARED) ... ON / else() ... OFF`），coordgen 根本不会被 `add_subdirectory`。
2. 且 `grep -rn "coordgen" openbabel/src/` **零命中**——openbabel 自身源码不引用
   coordgen 的任何头文件或类，故即使构建也不会产生 `__imp_` 消费点。

**结论**：无需处理。若将来有人把 `WITH_COORDGEN` 打开，需同步定义 `STATIC_COORDGEN`。

---

## 四、风险 3：其他导出宏（早已覆盖）

| 库 | 宏名 | 证据 | IQmol 处理 |
|---|---|---|---|
| yaml-cpp | `YAML_CPP_STATIC_DEFINE` | `yaml-cpp/include/yaml-cpp/dll.h:10` | ✅ `CMakeLists.txt:31` |
| libQGLViewer | `QGLVIEWER_STATIC` | `libQGLViewer/QGLViewer/config.h` | ✅ `CMakeLists.txt:31` |
| maeparser | `STATIC_MAEPARSER` | `MaeParserConfig.hpp:3` | ✅ `CMakeLists.txt:183` |

---

## 五、风险 4-5：完整性与存在性

**格式列表完整性**：用 CMake `include(formats.cmake)` 真实展开，`formats` 共 **106** 项
（静态默认配置下），逐一核对 `formats/<name>.cpp` 全部存在，**0 缺失**。

**全部源文件存在性**：按修复后的收集逻辑展开，共 **109** 个源文件
（106 format 主文件 + 3 个 additional_sources），逐一解析路径，**109/109 存在，0 缺失**。

> 注：`APIInterface` / `chemdrawct` 虽不含 `format` 后缀，但确实是 `formats/` 下的合法
> 格式成员（文件存在），会正常参与编译。

---

## 六、结论

| 状态 | 项 |
|---|---|
| **已修复（本次推送 c3ff679）** | ① `additional_sources` 漏加（3 文件）② maeparser 宏名错误 |
| **已确认无风险** | ③ 格式列表完整性 ④ 源文件存在性 ⑤ yaml-cpp / libQGLViewer 宏 ⑥ rapidjson（纯头文件） |
| **已知但当前不触发** | ⑦ coordgen 的 `STATIC_COORDGEN` PRIVATE 问题（`WITH_COORDGEN=OFF` + 无消费点） |

**预期**：下一次 `--clean` 构建，链接期不应再出现 undefined reference。
若仍有残留，仅剩可能性是外部系统库（Boost / libxml2 / zlib 等）的静态/动态混用问题，
那属于另一类（环境依赖），可另行排查。
