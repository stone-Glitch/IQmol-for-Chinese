# OpenBabel 静态链接 undefined reference（第二轮）诊断与修复

**日期**：2026-09-18
**平台**：Windows / MINGW64 / MinGW GCC 16.2.0
**现象**：`--whole-archive` 修复（ded257a）已生效，`linkLibs.rsp` 中 openbabel 已被正确
整段保留，但链接 `IQmol.exe` 仍报 3 类 undefined reference。

---

## 一、错误现场

```
libopenbabel.a(asciiformat.cpp.obj): undefined reference to `OpenBabel::ASCIIPainter::ASCIIPainter(int, int, double)'
libopenbabel.a(asciiformat.cpp.obj): undefined reference to `OpenBabel::ASCIIPainter::DrawLine(...)'
libopenbabel.a(painterformat.cpp.obj): undefined reference to `OpenBabel::CommandPainter::CommandPainter(std::ostream&)'
libopenbabel.a(maeformat.cpp.obj): undefined reference to `__imp__ZN11schrodinger3mae6ReaderC1ESt10shared_ptrISiEy'
libopenbabel.a(wlnformat.cpp.obj): undefined reference to `NMReadWLN(char const*, OpenBabel::OBMol*)'
```

**关键观察**：报错的「引用方」与「被引用方」**都在 libopenbabel.a 内部**。说明
`--whole-archive` 已经把库整段保留，但**这些符号的定义根本没被编进库**。

---

## 二、根因分析（两类独立问题）

### 问题 1：`additional_sources` 漏加（ASCIIPainter / CommandPainter / NMReadWLN）

`modules/openbabel/src/CMakeLists.txt` 第 184-188 行，**静态构建分支**：

```cmake
else(BUILD_SHARED)
  include(formats/formats.cmake)
  foreach(format ${formats})
    set(openbabel_srcs ${openbabel_srcs} formats/${format}.cpp)     # ← 只加了主 .cpp
  endforeach(format ${formats})
```

而 `formats/formats.cmake` 中，这些格式的**实现文件定义在 `<format>_additional_sources`**：

```cmake
set(painterformat_additional_sources ../depict/commandpainter.cpp)   # 第22行
set(asciiformat_additional_sources   ../depict/asciipainter.cpp)     # 第23行
set(wlnformat_additional_sources     wln-nextmove.cpp)               # 第148行
```

**结论**：静态构建时循环只加了 `formats/${format}.cpp`，漏掉 `additional_sources`，
于是 `asciipainter.cpp`/`commandpainter.cpp`/`wln-nextmove.cpp` 从未参与编译，
`libopenbabel.a` 里自然没有对应符号 → 链接失败。

> 对照：共享构建走 `formats/CMakeLists.txt`（第 40-42 行），那里是带
> `${${format}_additional_sources}` 的，所以共享构建不受影响。这是**上游
> OpenBabel 在「静态构建 + formats 分组」路径上的缺陷**，与 IQmol 无关。

### 问题 2：宏名用错（schrodinger::mae）★ 本轮新发现

`__imp_` 前缀表明符号被当作 **DLL 导入**。查 maeparser v1.2.3 的导出宏定义
`MaeParserConfig.hpp`：

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

而 `maeparser/CMakeLists.txt` 只做了：

```cmake
target_compile_definitions(maeparser PRIVATE "STATIC_MAEPARSER")   # ← PRIVATE，不传播
```

**`PRIVATE` 不会传播给消费者**（openbabel 的 `maeformat.cpp`），因此消费者编译时
`STATIC_MAEPARSER` 未定义，`EXPORT_MAEPARSER` 展开为 `__declspec(dllimport)`，
产生 `__imp_` 前缀符号，与静态库中的实际符号名不匹配 → undefined reference。

> **本轮修正**：之前 IQmol 定义的是 `MAEPARSER_STATIC_DEFINE`——这个名字在整个
> maeparser v1.2.3 源码中**根本不存在**（实测 `grep` 零命中），等于没起作用。
> 正确宏名是 **`STATIC_MAEPARSER`**。

---

## 三、修复内容

| 文件 | 改动 |
|---|---|
| `CMakeLists.txt:183` | `add_compile_definitions(MAEPARSER_STATIC_DEFINE)` → `add_compile_definitions(STATIC_MAEPARSER)` |
| `scripts/openbabel_src_CMakeLists.txt`（新增） | 上游 `openbabel/src/CMakeLists.txt` 修复版：静态分支循环补 `${${format}_additional_sources}`（跳过 inchiformat 以免与 WITH_STATIC_INCHI 分支重复） |
| `scripts/build_windows.sh` | 新增步骤 2d：检测并替换 `openbabel/src/CMakeLists.txt`；指纹增加 `OB_SRC_ADDITIONAL` / `OB_ROOT_PATCHED` 两项 |

### 修复后 CMake 展开验证

```
formats/painterformat.cpp;../depict/commandpainter.cpp
formats/asciiformat.cpp;../depict/asciipainter.cpp
formats/wlnformat.cpp;wln-nextmove.cpp
```

（用最小 CMake 工程实跑 `foreach` 变量间接展开，输出与预期一致。）

---

## 四、验证方式

在 Windows 侧执行：

```bash
cd /d/IQmol/IQmol-src
bash scripts/build_windows.sh --clean     # 必须 --clean 以重跑 configure
```

expect：

1. 步骤 2d 打印「检测到 openbabel/src/CMakeLists.txt 静态分支漏加 additional_sources，自动修复」；
2. 编译日志中 `asciipainter.cpp` / `commandpainter.cpp` / `wln-nextmove.cpp` 出现编译行；
3. 链接阶段不再出现 `ASCIIPainter` / `CommandPainter` / `NMReadWLN` / `__imp_...schrodinger3mae`；
4. `[100%] Built target IQmol`，产物 `build/bin/IQmol.exe`。

---

## 五、说明

- 本问题是**独立于** ded257a（`$<LINK_LIBRARY:WHOLE_ARCHIVE>`）之外的第二层原因。
  第一层解决「库被整段保留」，本层解决「符号根本没被编进库」。两层都需要。
- `additional_sources` 的修复文件是**整份替换**上游 `src/CMakeLists.txt`，故若解压过
  submodules 离线包会把该文件覆盖回未修版——build 脚本的步骤 2d 会自动重新修复，
  与已有的 openbabel 根 CMakeLists 修复（步骤 2b）机制一致。
