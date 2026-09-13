# OpenBabel 插件加载失败 — 诊断与修复记录

| 项目 | 内容 |
| --- | --- |
| 日期 | 2026-09-13 |
| 平台 | Windows 10 / MSYS2 MinGW64（复现与修复验证） |
| 影响版本 | IQmol 3.2.3 静态构建（`BUILD_SHARED_LIBS OFF`） |
| 提交 | `e4f5857`（`BUILD_SHARED` 同步）、`45a09a0`（`--whole-archive`，含依赖修复） |
| 状态 | 已修复并通过最小工程验证 |

---

## 0. 两次报错的因果关系（先看结论）

Windows 端先后出现两条报错，它们是**同一根因的两个层次**：

| 顺序 | 报错 | 触发时机 | 实质 |
| --- | --- | --- | --- |
| ① | `Failed to load force field: UFF` | 执行能量计算 | 力场**找不到** |
| ② | `Unable to find OpenBabel plugins` | OpenBabel 初始化 | 插件**没被编进程序**，正在去磁盘找 |

**总根因**：OpenBabel 子模块使用的是它自己的私有开关 `BUILD_SHARED`（默认 `ON`），与 CMake 标准的 `BUILD_SHARED_LIBS` **完全无关**。顶层 `set(BUILD_SHARED_LIBS OFF)` 并没有让 OpenBabel 走静态构建，于是它按「动态插件」方式构建，插件既不内联、运行期又从磁盘找不到 → 同时产生上面两条报错。

修复步骤是**两层叠加**的，缺一不可：

| 提交 | 修复内容 | 解决什么 |
| --- | --- | --- |
| `e4f5857` | 同步 `BUILD_SHARED` = `BUILD_SHARED_LIBS` | 让插件**被编进**程序（解决 ②，根治） |
| `45a09a0` | `openbabel` 加 `--whole-archive` | 让已编入的插件注册对象**不被链接器丢弃**（解决 ①，防护） |

> 只做 `--whole-archive` 而不做 `BUILD_SHARED` 同步，插件根本没进静态库，无从链接；
> 只做 `BUILD_SHARED` 同步而不做 `--whole-archive`，插件进了库但仍会被 GNU ld 丢弃。
> 两者是「先有可链之物、再保证不被丢」，必须同时具备。

---

## 1. 问题现象

### 1.1 力场加载失败

Windows 下编译链接**完全成功**，程序启动后中文界面正常，但执行「计算 → 能量」时弹出错误对话框：

```
Failed to load force field: UFF
Unable to compute energy
BABEL_DATADIR environment variable may not be set correctly.
```

代码位置 `src/Layer/MoleculeLayer.C:2080-2095`，触发条件是：

```cpp
OBForceField* forceField = OBForceField::FindForceField(obff);
if (!forceField) {
   // 弹出上述提示
}
```

即 `FindForceField("UFF")` 返回 `NULL`。

### 1.2 插件目录找不到

程序启动（或首次调用 OpenBabel）时，控制台/日志出现：

```
*** Open Babel Error  in LoadAllPlugins
  Unable to find OpenBabel plugins. Try setting the BABEL_LIBDIR environment variable.
```

代码位置 `modules/openbabel/src/plugin.cpp:62`。

---

## 2. 排除项（先证明不是数据问题）

第 1.1 节的提示文案把矛头指向 `BABEL_DATADIR`，但实测数据文件是齐的：

| 检查项 | 结果 |
| --- | --- |
| `build/share/openbabel/` 文件数 | 63 |
| `modules/openbabel/data/` 文件数 | 63 |
| `build/share/openbabel/UFF.prm` | 存在，12573 字节 |
| 构建产物中 `.obf` 插件文件数 | 0 |

同时核对了 OpenBabel 的数据查找实现 `modules/openbabel/src/tokenst.cpp:192` `OpenDatafile()`，其查找顺序为：

1. 当前工作目录
2. `${BABEL_DATADIR}/<BABEL_VERSION>/<文件名>`
3. `${BABEL_DATADIR}/<文件名>`

第 3 条即扁平目录，**本身可用**。且 `IQmolApplication.C:198-207` 在 Windows 下已正确把 `BABEL_DATADIR` 设为 `build/share/openbabel`。

**结论：1.1 的报错文案具有误导性，问题不在数据文件，也不在路径配置。**

---

## 3. 根因分析

### 3.1 两个 `BUILD_SHARED` 变量互不相干

| 变量 | 定义位置 | 改动前的值 | 作用范围 |
| --- | --- | --- | --- |
| `BUILD_SHARED_LIBS` | IQmol 顶层 `CMakeLists.txt:17` | `OFF` | 决定 IQmol 各模块编成静态库 |
| `BUILD_SHARED` | `modules/openbabel/CMakeLists.txt:105` `option(... ON)` | **`ON`** | 决定 OpenBabel 是否动态构建 |

CMake 的 `option(BUILD_SHARED ... ON)` 与标准变量 `BUILD_SHARED_LIBS` 之间**没有任何自动关联**。顶层设置后者，对前者毫无影响。

### 3.2 `BUILD_SHARED=ON` 引发的连锁反应

`modules/openbabel/CMakeLists.txt:110-118`：

```cmake
if(BUILD_SHARED)
  set(BUILD_TYPE SHARED)
  set(PLUGIN_TYPE MODULE)
  add_definitions(-DUSING_DYNAMIC_LIBS)     # ← 关键
  ...
```

`USING_DYNAMIC_LIBS` 一旦定义，`src/plugin.cpp:46` 的 `LoadAllPlugins()` 就进入动态分支：

```cpp
void OBPlugin::LoadAllPlugins()
{
  int count = 0;
#if defined(USING_DYNAMIC_LIBS)
  string TargetDir;
  DLHandler::getConvDirectory(TargetDir);          // 取 BABEL_LIBDIR
  vector<string> files;
  if(!DLHandler::findFiles(files, DLHandler::getFormatFilePattern(), TargetDir)) {
    obErrorLog.ThrowError(__FUNCTION__,
      "Unable to find OpenBabel plugins. Try setting the BABEL_LIBDIR environment variable.",
      obError);                                     // ← 报错 ②
    return;
  }
  ...
#else
  count = 1;          // 静态构建：直接跳过，不会有任何报错
#endif
```

同时在 `src/CMakeLists.txt:288-304`，`BUILD_SHARED=ON` 时插件被编成**独立的 MODULE**（Windows 下后缀 `.obf`）而非并入主库：

```cmake
if(BUILD_SHARED)
  foreach(plugingroup descriptors fingerprints forcefields ops charges)
    add_library(plugin_${plugingroup} ${PLUGIN_TYPE} ${${plugingroup}} ...)
    set_target_properties(plugin_${plugingroup} PROPERTIES SUFFIX ${MODULE_EXTENSION})
  endforeach()
endif()
```

而这些 `.obf` **既没有被 IQmol 链接，也没有被 `install()`/部署到运行目录** —— 于是运行期在 `BABEL_LIBDIR` 下自然一个都找不到。

### 3.3 为什么 `find build -name "*.obf"` 返回 0

用户此前实测 `.obf` 数量为 0，这看似与 `BUILD_SHARED=ON` 矛盾。原因是 `add_subdirectory(modules/openbabel EXCLUDE_FROM_ALL)` 引入了 `EXCLUDE_FROM_ALL`：这些 `plugin_*` 目标**不属于默认构建目标**，`make`（不带具体目标）不会构建它们，所以磁盘上没有 `.obf` 产物 —— 但 `-DUSING_DYNAMIC_LIBS` 这个编译宏**已经生效**了。

> 这正是隐蔽之处：**编译宏生效了，产物却没生成**。运行期程序按「应该从磁盘加载插件」的逻辑去找，却什么也找不到。

### 3.4 为什么 Linux 上没暴露

Linux 构建中 CMake 的 `openbabel` 目标解析到了**系统动态库** `/usr/lib/x86_64-linux-gnu/libopenbabel.so.7.0.0`（系统包自带完整插件），根本不走嵌入构建分支，因此表现为正常。只有真正走 `modules/openbabel` 嵌入静态构建的 Windows 才会踩中。

---

## 4. 修复方案

### 4.1 根治：同步 `BUILD_SHARED`（提交 `e4f5857`）

在 `add_subdirectory(modules/openbabel)` **之前**插入同步逻辑（`CMakeLists.txt:140-165`）：

```cmake
if (NOT BUILD_SHARED_LIBS)
   set(BUILD_SHARED OFF CACHE BOOL "OpenBabel: build shared library + dynamic plugins" FORCE)
else()
   set(BUILD_SHARED ON CACHE BOOL "OpenBabel: build shared library + dynamic plugins" FORCE)
endif()

add_subdirectory(modules/openbabel  EXCLUDE_FROM_ALL)
```

要点：

- **必须在 `add_subdirectory` 之前**。`option()` 对已存在的 cache 变量不覆盖，若放在之后则子模块已经用默认的 `ON` 完成配置，改之无效。
- 用 `CACHE ... FORCE` 是为了覆盖用户上一次配置遗留的缓存值（否则改完仍可能沿用旧的 `ON`）。

静态构建下插件源码会在 `modules/openbabel/src/CMakeLists.txt:197-199` 被并入 `openbabel_srcs`：

```cmake
foreach(plugingroup descriptors fingerprints forcefields ops charges)
  set(openbabel_srcs ${openbabel_srcs} ${${plugingroup}})
endforeach()
```

即插件**静态内联**进主库，`USING_DYNAMIC_LIBS` 不再定义，运行期不再需要 `BABEL_LIBDIR`。

### 4.2 防护：`--whole-archive`（提交 `5111a63`）

插件内联进主库后带来新问题 —— 见下一节。

---

## 5. 第二层问题：静态插件注册对象被链接器丢弃

### 5.1 机制

OpenBabel 的力场、文件格式、描述符、指纹等采用**全局对象自注册**，不以显式函数调用注册。以 UFF 为例，`modules/openbabel/src/forcefields/forcefielduff.cpp:579`：

```cpp
//Make a global instance
OBForceFieldUFF theForceFieldUFF("UFF", true);
```

该全局对象的构造函数把实例写入 `OBForceField::Map()` 静态表（`include/openbabel/plugin.h` 的 `MAKE_PLUGIN` 宏）。

插件内联后，这些 `.cpp` 成为静态库 `openbabel.a` 的成员目标文件。GNU ld 提取静态库成员的唯一依据是**符号引用**：

> 只有当静态库中某个成员目标文件定义了当前未解析的符号时，该成员才会被链入。

`forcefielduff.o` 中**不存在被任何地方引用的符号** —— 它的全部作用是全局构造函数的副作用。于是该 `.o` 被整体丢弃，自注册从未执行，`OBForceField::Map()` 中根本没有 `"UFF"` 条目，`FindType("UFF")` 返回 `NULL`。

**这同样是静默失效：编译、链接、启动全程无任何报错。**

### 5.2 修复

用 `--whole-archive` 包裹 `openbabel`，强制链入其全部目标文件：

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
      target_link_libraries (${targetName}
         -Wl,--whole-archive
         openbabel
         -Wl,--no-whole-archive
      )
      add_dependencies(${targetName} openbabel)
   else()
      target_link_libraries (${targetName} openbabel)
   endif()
endif()
```

同时移除了原链接列表中裸写的 `openbabel`，避免重复链接。

### 5.3 踩坑记录：不要用 `$<TARGET_FILE:openbabel>`

`--whole-archive` 的首版写法用的是生成器表达式 `"$<TARGET_FILE:openbabel>"`（提交 `5111a63`），在 Windows 链接期报了：

```
mingw32-make[2]: *** No rule to make target
    'modules/openbabel/src/libopenbabel.a', needed by 'bin/IQmol.exe'.  Stop.
```

**原因**：`$<TARGET_FILE:...>` 会把库的**真实文件路径**直接写进 `link.txt`，从而**绕过 CMake 的目标依赖跟踪**。而 `openbabel` 是以 `EXCLUDE_FROM_ALL` 方式 `add_subdirectory` 进来的（不属于默认 `all` 目标），MinGW Makefile 后端因此找不到生成该文件的规则。

**正确做法**（提交 `45a09a0`）：用**目标名** `openbabel` 书写，由 CMake 自动建立依赖边并解析为相对构建目录的库路径，同时补 `add_dependencies()` 双保险。

实测 `link.txt` 生成结果，确认选项与库的相对顺序被保留、目标也被正确构建：

```
-Wl,--whole-archive sub/libsub.a -Wl,--no-whole-archive
```

> 经验：在 `target_link_libraries` 中混写选项与目标名时，CMake **保持书写顺序**输出到链接行；但**只要用了 `$<TARGET_FILE:...>`，就等于放弃了依赖管理** —— 对 `EXCLUDE_FROM_ALL` 引入的子模块尤其致命。

---

## 6. 验证方法

### 6.1 验证 `BUILD_SHARED` 同步（对应报告 ②）

用 CMake 最小工程模拟 IQmol 的 Windows 嵌入分支：

```cmake
# 顶层
set(BUILD_SHARED_LIBS OFF)
if (NOT BUILD_SHARED_LIBS)
   set(BUILD_SHARED OFF CACHE BOOL "ob" FORCE)
endif()
add_subdirectory(sub EXCLUDE_FROM_ALL)
```

```cmake
# sub/CMakeLists.txt (模拟 openbabel 子模块)
option(BUILD_SHARED "enable shared build support" ON)
if(BUILD_SHARED)
  add_definitions(-DUSING_DYNAMIC_LIBS)
  message(STATUS "BUILD_SHARED=ON  -> 定义 USING_DYNAMIC_LIBS (插件需外部加载)  << 故障态")
else()
  message(STATUS "BUILD_SHARED=OFF -> 插件静态内联 (USING_DYNAMIC_LIBS 未定义)  << 修复后")
endif()
```

实测输出：

```
-- 子模块: BUILD_SHARED=OFF -> 插件静态内联 (USING_DYNAMIC_LIBS 未定义)  << 修复后
```

修复前该行应为 `BUILD_SHARED=ON`（未同步时 `option` 的默认值）。

### 6.2 验证 `--whole-archive`（对应报告 ①）

构造最小可复现工程：把「注册对象」与「查找函数」拆到**不同**目标文件，还原被丢弃的条件。

`registry.cpp`（查找函数，被 main 引用）：
```cpp
std::map<std::string,int>& Reg() { static std::map<std::string,int> m; return m; }
```

`uff.cpp`（全局自注册，无任何外部引用）：
```cpp
std::map<std::string,int>& Reg();
struct AutoReg { AutoReg(const char* n){ Reg()[n]=1; } };
namespace { AutoReg theUFF("UFF"); }
```

`main.cpp`：
```cpp
int main(){ printf("UFF found: %s\n", Reg().count("UFF") ? "YES" : "NO"); }
```

链接方式对比：

| 链接方式 | 运行结果 |
| --- | --- |
| 普通链接 `-lplug` | `UFF found: NO` ← **精确复现用户现象** |
| `-Wl,--whole-archive ./libplug.a -Wl,--no-whole-archive` | `UFF found: YES` ← **修复生效** |

### 6.3 Linux 全量构建

`--whole-archive` 生效、链接通过、`Generated 1519 translation(s) (1519 finished and 0 unfinished)`。

---

## 7. 附带加固：`scripts/deploy_windows.sh`

| 加固项 | 说明 |
| --- | --- |
| 双布局数据目录 | 同时铺 `share/openbabel/`（扁平）与 `share/openbabel/<版本>/`（版本子目录）。版本号从 `modules/openbabel/CMakeLists.txt` 的 `BABEL_MAJ_VER` / `BABEL_MIN_VER` / `BABEL_PATCH_VER` 解析，当前得出 `3.1.1`，解析失败时回退为 `3.1.1` |
| 力场参数自检 | 检查 `UFF.prm` / `ghemical.prm` / `gaff.prm` / `mm2.prm` 是否存在，缺失即告警 |
| 自检名单修正 | **不**把 `MMFF94.prm` 列入自检 —— MMFF94 参数表编译进二进制，`data/` 目录下本就没有该文件，列入会导致每次部署误报 |
| 插件目录逻辑修正 | 静态内联构建下 `lib/openbabel/` 无插件属**正常**，不再误导；若确实发现 `.obf` 则说明构建被误配为动态模式，给出明确告警 |

---

## 8. Windows 端复现修复的步骤

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

预期：

| 阶段 | 应看到 |
| --- | --- |
| configure | `[IQmol] 已对 openbabel 启用 --whole-archive` |
| 编译 | 时间明显变长（所有格式插件改为内联编译，属预期） |
| 部署 | `力场参数已就位: UFF.prm / ghemical.prm / gaff.prm / mm2.prm` |
| 部署 | `OpenBabel 为静态内联构建（无 .obf），lib/openbabel/ 无需插件文件` |
| 运行 | 不再出现 `Unable to find OpenBabel plugins` |
| 运行 | 执行能量计算不再出现 `Failed to load force field: UFF` |

> **注意**：`BUILD_SHARED=OFF` 后 OpenBabel 会编译上百个格式插件源文件，**首次编译时间将显著增加**，这是预期行为。

---

## 9. 经验沉淀

### 9.1 子模块私有开关不会跟随 CMake 标准变量

> 第三方库若用 `option(BUILD_SHARED ...)` 之类的**私有开关**控制动态/静态构建，顶层设置标准的 `BUILD_SHARED_LIBS` 对它是**无效的**。嵌入构建前必须显式把这些私有开关同步过去，且必须放在 `add_subdirectory()` **之前**。

### 9.2 编译宏生效 ≠ 产物生成

> 本次最隐蔽的一点：`EXCLUDE_FROM_ALL` 让 `plugin_*` 目标不参与默认构建，磁盘上没有任何 `.obf`，但 `-DUSING_DYNAMIC_LIBS` 已经生效。程序按「应从磁盘加载插件」的逻辑运行，必然失败。排查时**不能只看产物有无，必须同时核对编译宏**。

### 9.3 静态库中「只有全局构造函数副作用」的目标文件会被静默丢弃

> 凡采用「全局对象自注册」模式的第三方库（OpenBabel 插件、Qt 静态插件、各类 factory 注册表），静态链接到可执行文件时都必须用 `--whole-archive` 包裹，或使用 `--undefined=<符号>` 强制拉入。这类问题**不会在编译链接期报错**，只会在运行期表现为「功能莫名其妙不存在」，且常被误导到配置/路径方向排查 —— 本次两条报错的文案（都在提示设置环境变量）恰好都是**误导性的**。

### 9.4 附带记录：OpenBabel 上游的一处笔误

`modules/openbabel/src/data.cpp:685` 在 `if` 内重新声明了同名变量：

```cpp
string fn_open = OpenDatafile(ifs, _filename, _envvar);
if (fn_open == "")
   string fn_open = OpenDatafile(ifs, _filename, _subdir);   // ← 重新声明，遮蔽外层
if (fn_open != "" && (ifs))   // ← 恒为假
```

内层 `string fn_open` 是**新的局部变量**，离开 `if` 作用域即销毁，外层 `fn_open` 始终为 `""`，导致随后的判断恒为假。这**不影响本次问题**（UFF 走的是 `forcefielduff.cpp:1616` 中独立的 `OpenDatafile` 调用，不经过 `OBGlobalDataBase::Init()`），但排查 OpenBabel 数据加载问题时需注意这一点，避免被带偏。
