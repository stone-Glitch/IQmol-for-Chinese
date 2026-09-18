# 补丁"修了等于没修"：增量构建跳过 configure 的判定盲区

**日期**：2026-09-19
**类型**：问题诊断 + 修复
**现象**：第三个轮次的链接失败，报错符号与第二轮**完全相同**

---

## 一、现象

用户在 Windows（MinGW64）重跑 `scripts/build_windows.sh`，链接 `bin/IQmol.exe` 时报：

```
libopenbabel.a(asciiformat.cpp.obj): undefined reference to `OpenBabel::ASCIIPainter::ASCIIPainter(int, int, double)'
libopenbabel.a(painterformat.cpp.obj): undefined reference to `OpenBabel::CommandPainter::CommandPainter(std::ostream&)'
libopenbabel.a(maeformat.cpp.obj): undefined reference to `__imp__ZN11schrodinger3mae6ReaderC1ESt10shared_ptrISiEy'
libopenbabel.a(wlnformat.cpp.obj): undefined reference to `NMReadWLN(char const*, OpenBabel::OBMol*)'
```

**关键特征**：符号集合与
[`2026-09-18-OpenBabel静态链接additional_sources与maeparser宏诊断.md`](2026-09-18-OpenBabel静态链接additional_sources与maeparser宏诊断.md)
记录的**逐条一致**（ASCIIPainter / CommandPainter / NMReadWLN / `__imp_` schrodinger::mae）。

> 一个报错重复出现两次，通常不是"上次没修对"，而是"上次的修复没有进入构建"。

---

## 二、排查过程（先验证补丁本身，再查它是否生效）

### 2.1 补丁内容正确性 —— 先排除"补丁写错了"

取 openbabel 子模块锁定的真实提交（`ea4710f04120df713a6806ffb56baae29f16f58f`），
把上游文件与我们的修复版逐行对比：

```bash
# 取上游真实文件
git -C <openbabel-repo> show ea4710f:src/CMakeLists.txt

# 对比我们的修复版
diff <上游文件> scripts/openbabel_src_CMakeLists.txt
```

结果：**前 183 行完全一致**，差异仅在静态分支的 `foreach` 内插入 13 行。

上游原始代码（**这就是 bug 本身**）：

```cmake
else(BUILD_SHARED)
  include(formats/formats.cmake)
  foreach(format ${formats})
    set(openbabel_srcs ${openbabel_srcs} formats/${format}.cpp)
    # ← 只加 formats/xxxformat.cpp，从不读 xxxformat_additional_sources
  endforeach(format ${formats})
```

我们的修复：

```cmake
    set(openbabel_srcs ${openbabel_srcs} formats/${format}.cpp)
    if(NOT format STREQUAL "inchiformat")
      set(openbabel_srcs ${openbabel_srcs} ${${format}_additional_sources})
    endif()
```

**缺失符号的来源全部确认**（读上游真实 `src/formats/formats.cmake`）：

| format | `additional_sources` 定义 | 缺失的符号 |
|---|---|---|
| `asciiformat` | `../depict/asciipainter.cpp` | `OpenBabel::ASCIIPainter::*` |
| `painterformat` | `../depict/commandpainter.cpp` | `OpenBabel::CommandPainter::*` |
| `wlnformat` | `wln-nextmove.cpp` | `NMReadWLN()` |

→ **补丁逻辑正确，必须能解决问题。**

### 2.2 补丁是否真的进入了构建 —— 问题在这里

脚本在 configure **之前** 把修复版覆盖进源码树（步骤 2d，第 220 行），顺序正确。
真正的盲区在步骤 4 的 **"是否跳过 configure"** 判定：

```bash
# 判定条件一：构建目录健全性
if [ ! -f "$BUILD_DIR/CMakeCache.txt" ] || [ ! -f "$BUILD_DIR/Makefile" ]; then
  NEED_CONFIG=1
# 判定条件二：只有【顶层 CMakeLists.txt】比 CMakeCache.txt 新才重配
elif [ "$SRC_DIR/CMakeLists.txt" -nt "$BUILD_DIR/CMakeCache.txt" ]; then
  NEED_CONFIG=1
fi
```

`_cfg_fingerprint()` 字符串指纹同样只 `grep "$SRC_DIR/CMakeLists.txt"`。

**两者都只盯着顶层 `CMakeLists.txt`，而所有补丁步骤改的都是 `modules/` 下的文件。**

| 步骤 | 改动的文件 | 是否在判定范围内 |
|---|---|---|
| 1 | `modules/CMakeLists.txt` | ❌ |
| 2b | `modules/openbabel/CMakeLists.txt` | ❌ |
| 2c | `modules/openbabel/data/CMakeLists.txt` | ❌ |
| 2d | `modules/openbabel/src/CMakeLists.txt` | ❌ |

### 2.3 因果链

```
用户上次 configure 成功
  → build/CMakeCache.txt + Makefile 存在
  → 本次重跑：步骤 2d 覆盖了 modules/openbabel/src/CMakeLists.txt ✅（文件内容对了）
  → 但顶层 CMakeLists.txt 没变 → NEED_CONFIG=0 → 跳过 configure ❌
  → 指纹机制只读顶层 CMakeLists → 也没触发
  → make 沿用旧的 build/modules/openbabel/src/CMakeFiles/*.make
    （其中仍只有 formats/xxxformat.cpp，没有 additional_sources）
  → asciipainter.cpp / commandpainter.cpp / wln-nextmove.cpp 从未被编译
  → 链接期 undefined reference 原样复现
```

与用户日志完全吻合：

- 走到 `[100%]` 才失败 —— 旧构建产物完整，只是缺那 3 个 `.o`；
- `[100%] Linking CXX static library libMain.a` 成功 —— `Main` 不依赖这些符号。

---

## 三、修复

新增**补丁指纹**机制：记录补丁文件当前是否处于"已修状态"，与上次不一致即强制重新 configure。

```bash
_patch_fingerprint() {
  local _mods=0 _ob_root=0 _ob_data=0 _ob_src=0
  [ -f "$MODULES_DIR/CMakeLists.txt" ] && _mods=1
  grep -q 'NOT TARGET uninstall'             "$MODULES_DIR/openbabel/CMakeLists.txt"      && _ob_root=1
  grep -q 'pregen'                           "$MODULES_DIR/openbabel/data/CMakeLists.txt" && _ob_data=1
  grep -q 'format}_additional_sources'       "$MODULES_DIR/openbabel/src/CMakeLists.txt"  && _ob_src=1
  printf 'PATCH_STATE MODS=%s OB_ROOT=%s OB_DATA=%s OB_SRC=%s' \
         "$_mods" "$_ob_root" "$_ob_data" "$_ob_src"
}
```

**为什么用"语义标记"而不是"记录本次执行了哪些补丁"**（首版实现的弯路）：

- 动作记录型指纹在「执行补丁的那轮」与「不执行的那轮」之间来回抖动
  → 每轮都判定为变化 → 反复 re-configure，拖慢增量构建。
- 语义标记型：打补丁前 `0000`，打补丁后 `1111` → **恰好变化一次即触发**；
  之后每轮都是 `1111` → 稳定跳过。

---

## 四、验收（仿真实测，6 场景全过）

在仿真目录中用 **openbabel 上游真实文件**（`ea4710f`）复现：

| # | 场景 | 期望 | 实测 |
|---|---|---|---|
| 1 | 三个补丁均未应用 → 首轮构建 | 触发重配 | ✅ `★ 触发` `0000 → 1111` |
| 2 | 紧接着再跑（补丁已在） | 跳过 | ✅ `· 跳过` |
| 3 | 第三次跑 | 跳过（稳定） | ✅ `· 跳过` |
| 4 | submodules 包把 src 覆盖回未修版 | 触发重配 | ✅ `★ 触发` `OB_SRC=0` |
| 5 | 恢复补丁后再跑 | 触发重配一次 | ✅ `★ 触发` `OB_SRC=1` |
| 6 | 连续两次 | 跳过 | ✅ `· 跳过` `· 跳过` |

端到端（步骤 2b + 2c + 2d 全跑）：

```
[步骤2b]  已修复
[步骤2c]  已修复
[步骤2d]  已修复
[补丁指纹判定]
  ★ 触发重新 configure
    PATCH_STATE MODS=1 OB_ROOT=1 OB_DATA=1 OB_SRC=1
```

---

## 五、用户侧操作建议

本次修复解决的是"补丁不进构建"，因此：

```bash
# 直接重跑即可（脚本会因补丁指纹变化而自动重新 configure）
bash scripts/build_windows.sh
```

若希望一次性彻底重来（首次 configure 约 1~5 分钟，编译约 20~40 分钟）：

```bash
bash scripts/build_windows.sh --clean
```

**预期**：编译日志中应出现

- `==> 检测到子模块补丁状态变化（补丁已应用到源码树，但尚未反映到构建配置），自动重新 configure...`
- `asciipainter.cpp` / `commandpainter.cpp` / `wln-nextmove.cpp` 的编译行
- `[100%] Built target IQmol`

---

## 六、教训

1. **"打了补丁" ≠ "补丁生效"。** 构建系统的生成文件（`*.make`/`build.make`）是补丁与
   编译之间的一层缓存，改了源码树的输入却不重建它，等于没改。
2. **判定条件的覆盖面必须与改动面匹配。** 判定只看顶层 `CMakeLists.txt`，
   而补丁改的是子目录文件 —— 覆盖面不匹配，就会静默失效。
3. **同一报错重复出现时，优先怀疑"修复未进入构建"，而非"修复方向错"。**
   本次先花时间验证了补丁逻辑的正确性（读上游真实源码逐行对比），
   才把注意力转到构建流程上，这个顺序是对的。
