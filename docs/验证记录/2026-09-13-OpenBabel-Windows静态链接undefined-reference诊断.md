# OpenBabel Windows 静态链接 undefined reference 诊断与修复

> 日期：2026-09-13
> 平台：Windows / MinGW64 / GCC 16.2.0
> 现象：链接 `bin/IQmol.exe` 失败，`ld.exe` 报一批 `undefined reference`
> 相关提交：`dc6a133`（修复）、`38e90ec`（前序汉化产出入库）

---

## 一、错误现场

链接 `bin/IQmol.exe` 阶段，`openbabel` 静态库已成功构建（`[100%] Built target openbabel`），
但 IQmol 主程序链接失败，缺失三类符号：

| 来源 .obj | 缺失符号 | 类别 |
|---|---|---|
| `asciiformat.cpp.obj` / `painterformat.cpp.obj` | `OpenBabel::ASCIIPainter::*`、`OpenBabel::CommandPainter::*` | 同库内被丢弃的成员 |
| `maeformat.cpp.obj` | `__imp__ZN11schrodinger3mae6Reader...`（Reader/Writer/Block） | **DLL 导入**（`__imp_` 前缀） |
| `wlnformat.cpp.obj` | `NMReadWLN` | 同库内被丢弃的成员 |

---

## 二、根因分析

### 2.1 `ASCIIPainter` / `CommandPainter` / `NMReadWLN` —— 静态库成员被丢弃

与早前的 UFF 力场注册丢失**同一类根因**：GNU ld 对静态库按"符号引用"提成员，
纯全局构造副作用或弱引用成员会被整体丢弃。`--whole-archive` 已用于包裹 `openbabel`，
但若链接命令（link.txt）是旧缓存、未重跑 configure，则 `--whole-archive` 未生效，
这些符号随之缺失。

### 2.2 `schrodinger::mae::*` —— maeparser 的 DLL 导入宏

`maeformat.cpp` 包含的是 `<maeparser/Reader.hpp>` 等头文件：`schrodinger::mae`
命名空间来自 OpenBabel **捆绑的独立 `maeparser` 库**（MAE 分子格式），不在
`openbabel` 自身源码里。

maeparser 用 CMake `GenerateExportHeader` 生成导出宏。在 Windows 静态构建下，
若该宏未被告知"静态使用"，默认按 `__declspec(dllimport)` 处理外部符号，
于是 `maeformat.cpp` 引用 `schrodinger::mae::Reader` 时带 `__imp_` 前缀，
而静态 `maeparser.a` 提供的是普通符号 → 不匹配 → `undefined reference to __imp_...`。

> 注：本仓离线子模块包**不含** maeparser（与用户机器上的完整子模块不同），
> 故本仓 Linux 构建无法复现；诊断基于错误信息与 OpenBabel 3.1.1 源码结构推演。

---

## 三、修复

1. **`CMakeLists.txt`**：在 `add_subdirectory(modules/openbabel)` **之前**、且
   静态构建（`NOT BUILD_SHARED_LIBS`）时，定义 `MAEPARSER_STATIC_DEFINE`，
   使 maeparser 导出宏退化为普通符号，与静态 `.a` 匹配；并让 maeparser 子目录继承该宏。
   若 `maeparser` 是独立 CMake 目标，一并用 `--whole-archive` 整体保留。

2. **`scripts/build_windows.sh`**：把 `MAEPARSER_STATIC_DEFINE` 纳入配置指纹
   （`BUILD_SHARED_SYNC` / `WHOLE_ARCHIVE` / `MAEPARSER_STATIC`）。否则用户本地
   `CMakeLists.txt` 已含 `--whole-archive` 时指纹不变、不会重配，`MAEPARSER_STATIC_DEFINE`
   不生效。

---

## 四、用户侧验证步骤（关键）

1. 更新本地 `CMakeLists.txt` 与 `scripts/build_windows.sh` 到最新（含 `dc6a133`）。
2. **清理并重新配置**（务必执行，否则沿用旧 link.txt）：
   - 删除构建目录，或至少 `build/CMakeCache.txt` 与 `build/Makefile`；
   - 重新运行 `scripts/build_windows.sh`。
3. 配置阶段日志应出现 `[IQmol] 已对 openbabel 启用 --whole-archive` 与
   （若 maeparser 为独立目标）`[IQmol] 已对 maeparser 启用 --whole-archive`。
4. 重新链接应不再出现上述 `undefined reference`。

---

## 五、若仍失败：回退方案

若 `MAEPARSER_STATIC_DEFINE` 未覆盖实际宏名（极少数 OpenBabel 分支用不同导出宏），
可改用 **OpenBabel 共享构建**：将 `BUILD_SHARED` 设为 `ON`，IQmol 链接
`openbabel` 导入库，运行时随 `openbabel-3.dll` / `maeparser.dll` 加载。
代价是需在 `deploy_windows.sh` 中正确部署 DLL、插件 `.obf` 文件与
`BABEL_LIBDIR` / `BABEL_DATADIR`（否则会回到早前的 "Unable to find OpenBabel plugins"）。
