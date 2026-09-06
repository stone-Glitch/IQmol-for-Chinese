#!/usr/bin/env bash
# IQmol Windows 自动构建脚本（在 MINGW64 终端运行）
# 用法:
#   bash build_windows.sh            # 增量构建（默认，推荐）
#   bash build_windows.sh --clean    # 删掉 build/ 从零重来（慢，仅在换配置时用）
#   JOBS=8 bash build_windows.sh     # 手动指定并行度（默认自动取核数，上限 8）
#   CMAKE_BIN="D:/cmake-3.31/bin/cmake.exe" bash build_windows.sh   # 用已有 3.31
#
# 脚本请放在 IQmol-src/ 根目录，或 IQmol-src/scripts/ 下。
# 把交付的 modules_CMakeLists.txt 放在同一目录可离线补全缺失文件。
#
# 重要：默认【增量】。configure 成功后不要删 build/，重跑本脚本只会编译
# 改动过的部分；编译中断后直接重跑即可续上，不会从头开始。
set -u

# ===== 可调参数（可用环境变量覆盖）=====
CMAKE_BIN="${CMAKE_BIN:-cmake}"
# MINGW64 终端里 MinGW 根目录就是 /mingw64（MSYS2 装在哪个盘都一样），
# 不要写成 /c/msys64/mingw64 或 /d/msys64/mingw64 —— 那是错的，会让 CMake
# 找不到 Qt / Boost，Generate 阶段直接失败。
MINGW_PREFIX="${MINGW_PREFIX:-/mingw64}"
if [ ! -d "$MINGW_PREFIX" ]; then
  for _p in /mingw64 /c/msys64/mingw64 /d/msys64/mingw64 /c/msys2/mingw64; do
    if [ -d "$_p" ]; then MINGW_PREFIX="$_p"; break; fi
  done
fi
echo "==> MinGW 前缀: $MINGW_PREFIX"
# 并行度自动取 CPU 核数，但上限 8：OpenBabel / QGLViewer 部分编译单元峰值
# 内存可达 1~2GB，核数多的机器开满容易 OOM，反而更慢。
JOBS="${JOBS:-$(nproc 2>/dev/null || echo 4)}"
if [ "$JOBS" -gt 8 ] 2>/dev/null; then JOBS=8; fi

# 推导源码根：脚本在 scripts/ 下则取上一级，否则取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ "$(basename "$SCRIPT_DIR")" = "scripts" ]; then
  SRC_DIR="$(dirname "$SCRIPT_DIR")"
else
  SRC_DIR="$SCRIPT_DIR"
fi
MODULES_DIR="$SRC_DIR/modules"

echo "==> 源码根: $SRC_DIR"

# ===== 0. 通用下载函数：优先 ghfast.top 镜像，失败再直连 =====
# raw.githubusercontent.com / github.com 在墙内直连基本必挂（Connection reset），
# 所以任何联网下载都必须先走 ghfast.top 镜像。
fetch_from_github() {
  # 用法: fetch_from_github <输出路径> <原始URL>
  local OUT="$1"; local URL="$2"; local U
  for U in "https://ghfast.top/$URL" "$URL"; do
    echo "    尝试 $U"
    if command -v curl >/dev/null 2>&1; then
      curl -fsSL --connect-timeout 15 "$U" -o "$OUT" && return 0
    elif command -v wget >/dev/null 2>&1; then
      wget -qO "$OUT" "$U" && return 0
    fi
  done
  return 1
}

# ===== 1. 检查/补全 modules/CMakeLists.txt（构建 libQGLViewer 的聚合脚本）=====
if [ ! -f "$MODULES_DIR/CMakeLists.txt" ]; then
  echo "==> 缺失 modules/CMakeLists.txt，尝试恢复..."
  # 兼容脚本放源码根 / 放 scripts/ 两种位置
  LOCAL_FIX=""
  for CAND in "$SCRIPT_DIR/modules_CMakeLists.txt" "$SCRIPT_DIR/scripts/modules_CMakeLists.txt"; do
    [ -f "$CAND" ] && LOCAL_FIX="$CAND" && break
  done
  if [ -n "$LOCAL_FIX" ]; then
    cp "$LOCAL_FIX" "$MODULES_DIR/CMakeLists.txt"
    echo "    已从本地 $LOCAL_FIX 复制"
  else
    URL="https://raw.githubusercontent.com/stone-Glitch/IQmol-for-Chinese/main/modules/CMakeLists.txt"
    echo "    下载补全文件..."
    fetch_from_github "$MODULES_DIR/CMakeLists.txt" "$URL" || {
      echo "ERROR: 下载失败。请手动放置 modules_CMakeLists.txt 到 $SCRIPT_DIR/"
      exit 1
    }
  fi
  if [ ! -f "$MODULES_DIR/CMakeLists.txt" ]; then
    echo "ERROR: 仍无法获取 modules/CMakeLists.txt，请手动放置后重试"
    exit 1
  fi
  echo "    已补全 $MODULES_DIR/CMakeLists.txt"
fi

# ===== 自动获取 CMake 3.31（portable，Windows x86_64）=====
auto_get_cmake_3_31() {
  local VER="3.31.6"
  local DEST="$SRC_DIR/.tools/cmake-$VER"
  local BIN="$DEST/bin/cmake.exe"
  if [ -x "$BIN" ]; then CMAKE_BIN="$BIN"; return 0; fi
  echo "==> 自动下载 CMake $VER (portable)..."
  mkdir -p "$SRC_DIR/.tools"
  local ZIP="$SRC_DIR/.tools/cmake-$VER-windows-x86_64.zip"
  local BASE="https://github.com/Kitware/CMake/releases/download/v$VER/cmake-$VER-windows-x86_64.zip"
  local OK=0
  for U in "https://ghfast.top/$BASE" "$BASE"; do
    echo "    尝试 $U"
    if command -v curl >/dev/null 2>&1; then
      curl -fL "$U" -o "$ZIP" && OK=1 && break
    elif command -v wget >/dev/null 2>&1; then
      wget -O "$ZIP" "$U" && OK=1 && break
    fi
  done
  if [ "$OK" -ne 1 ]; then
    echo "ERROR: 自动下载失败（可能被墙）。请手动下载:"
    echo "       $BASE"
    echo "       解压后运行: CMAKE_BIN=\"解压目录/bin/cmake.exe\" bash build_windows.sh"
    return 1
  fi
  echo "    解压中..."
  ( cd "$SRC_DIR/.tools" && cmake -E tar xf "$ZIP" ) || { echo "ERROR: 解压失败"; return 1; }
  if [ -d "$SRC_DIR/.tools/cmake-$VER-windows-x86_64" ]; then
    mv "$SRC_DIR/.tools/cmake-$VER-windows-x86_64" "$DEST"
  fi
  if [ ! -x "$BIN" ]; then echo "ERROR: 解压后未找到 $BIN"; return 1; fi
  CMAKE_BIN="$BIN"
  return 0
}

# ===== 2. 检查 CMake 版本（IQmol 在 Windows 不兼容 CMake 4.x）=====
CMAKE_VER="$("$CMAKE_BIN" --version 2>/dev/null | head -1)"
echo "==> CMake: $CMAKE_VER"
if echo "$CMAKE_VER" | grep -qE " 4\.[0-9]"; then
  echo "    检测到 CMake 4.x，自动获取 3.31..."
  auto_get_cmake_3_31 || exit 1
  CMAKE_VER="$("$CMAKE_BIN" --version 2>/dev/null | head -1)"
  echo "==> 改用 $CMAKE_VER"
fi

# ===== 2b. 检查/修复 openbabel/CMakeLists.txt 的 uninstall 目标保护 =====
# yaml-cpp 先定义了 uninstall 目标，OpenBabel 774 行再定义就撞车（CMP0002），
# configure 报: ADD_CUSTOM_TARGET cannot create target "uninstall"。
# 修复版在 scripts/openbabel_CMakeLists.txt（与 fix 包内一致）。
# 注意：若解压过 submodules 完整包，此文件会被覆盖回未修版——本步骤自动修复。
OB_CML="$MODULES_DIR/openbabel/CMakeLists.txt"
if [ -f "$OB_CML" ] && ! grep -q "NOT TARGET uninstall" "$OB_CML"; then
  echo "==> 检测到 openbabel/CMakeLists.txt 缺 uninstall 保护，自动修复..."
  # 兼容脚本放源码根 / 放 scripts/ 两种位置
  FIX_CML=""
  for CAND in "$SCRIPT_DIR/openbabel_CMakeLists.txt" "$SCRIPT_DIR/scripts/openbabel_CMakeLists.txt"; do
    [ -f "$CAND" ] && FIX_CML="$CAND" && break
  done
  if [ -n "$FIX_CML" ]; then
    cp "$FIX_CML" "$OB_CML"
    echo "    已用 $FIX_CML 覆盖"
  else
    URL="https://raw.githubusercontent.com/stone-Glitch/IQmol-for-Chinese/main/scripts/openbabel_CMakeLists.txt"
    echo "    本地无修复文件，下载..."
    fetch_from_github "$OB_CML" "$URL" || true
  fi
  if grep -q "NOT TARGET uninstall" "$OB_CML" 2>/dev/null; then
    echo "    修复完成"
  else
    echo "ERROR: 修复失败。请手动从 IQmol-openbabel-fix.tar.gz 重新解压到 modules/openbabel/" >&2
    exit 1
  fi
fi

# ===== 3. 检查 OpenBabel external 依赖（缺了 configure 必崩，直接拦截）=====
# OpenBabel 缺这三个包时不会跳过，而是尝试联网从 GitHub 下载；
# 墙内下载失败 → FATAL_ERROR "Failed getting or unpacking Maeparser/coordgen"
# → 整个 configure 白跑。所以这里提前拦截，省得等几分钟才崩。
OB_EXT="$MODULES_DIR/openbabel/external"
MISSING=""
for d in maeparser-v1.2.3 coordgen-master rapidjson-1.1.0; do
  [ -d "$OB_EXT/$d" ] || MISSING="$MISSING $d"
done
if [ -n "$MISSING" ]; then
  echo "ERROR: OpenBabel external 依赖缺失:$MISSING" >&2
  echo "" >&2
  echo "  处理：把 IQmol-openbabel-deps.tar.gz 解压到 modules/openbabel/ 下，" >&2
  echo "        解压后会生成 external/ 目录。命令示例（MINGW64）：" >&2
  echo "        cd $MODULES_DIR/openbabel && tar -xzf /d/IQmol/IQmol-openbabel-deps.tar.gz" >&2
  echo "" >&2
  echo "  包的位置：GitHub submodules-package 分支 / 对话文件卡片均可下载。" >&2
  exit 1
fi
echo "==> OpenBabel external 依赖齐备"

# ===== 4. configure（增量：build/ 已配置过就跳过）=====
BUILD_DIR="$SRC_DIR/build"
CLEAN="${CLEAN:-0}"
case "${1:-}" in
  --clean|--reconfigure|-c) CLEAN=1 ;;
esac

if [ "$CLEAN" = "1" ] && [ -d "$BUILD_DIR" ]; then
  echo "==> 清理旧构建目录 --clean（会重新 configure，较慢）..."
  rm -rf "$BUILD_DIR"
fi
mkdir -p "$BUILD_DIR"
cd "$BUILD_DIR" || exit 1

# 判定"配置成功"必须同时有 CMakeCache.txt 和 Makefile：上次 configure 失败时
# 会留下 CMakeCache.txt 却没有 Makefile，只看前者会误判为已配好，
# 进而直接进 make 报 "No targets specified and no makefile found"。
if [ -f "$BUILD_DIR/CMakeCache.txt" ] && [ -f "$BUILD_DIR/Makefile" ]; then
  # 已配置过：直接沿用缓存编译。若 CMakeLists 有改动，make 会自动触发重配。
  echo "==> 检测到已有配置，跳过 configure（要重配请加 --clean）"
else
  if [ -f "$BUILD_DIR/CMakeCache.txt" ]; then
    echo "==> 上次 configure 未完成（有 CMakeCache.txt 但无 Makefile），重新配置"
  fi
  echo "==> 首次 configure...（约 1~5 分钟，Windows 下 CMake 需逐个编译检查程序）"
  "$CMAKE_BIN" .. \
    -G "MinGW Makefiles" \
    -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_PREFIX_PATH="$MINGW_PREFIX" \
    -DCMAKE_CXX_FLAGS="-fpermissive -std=gnu++17 -Wno-deprecated" \
    -DCMAKE_MAKE_PROGRAM="mingw32-make" \
    -DBOOST_ROOT="$MINGW_PREFIX" 2>&1 | tee "$BUILD_DIR/cmake_config.log"
  RC=${PIPESTATUS[0]}   # 取 cmake 的退出码而非 tee 的
  if [ $RC -ne 0 ]; then
    echo ""
    echo "ERROR: cmake configure 失败（真正的错误往往被刷出屏幕，以下自动提取）"
    echo "==================== CMake Error 上下文 ===================="
    awk '/CMake Error/{c=15} c>0{print; c--}' "$BUILD_DIR/cmake_config.log" | head -80
    echo "============================================================"
    echo "把上面这段完整贴给助手即可定位。"
    exit 1
  fi
fi

# ===== 5. 编译 =====
# 优先 mingw32-make，某些环境只装了 GNU make（不带前缀）
MAKE_BIN="mingw32-make"
command -v "$MAKE_BIN" >/dev/null 2>&1 || MAKE_BIN="make"

echo "==> 开始编译（并行 -j$JOBS，首次约 20~40 分钟）..."
"$MAKE_BIN" -j"$JOBS" 2>&1 | tee "$BUILD_DIR/cmake_make.log"
RC=${PIPESTATUS[0]}
if [ $RC -ne 0 ]; then
  echo ""
  echo "ERROR: 编译失败（以下自动提取第一条编译错误及其上下文）"
  echo "==================== 第一条 error 上下文 ===================="
  awk '/error:/{c=10; print; next} /Error [12]/{c=10} c>0{print; c--}' "$BUILD_DIR/cmake_make.log" | head -60
  echo "============================================================"
  echo "把上面这段完整贴给助手即可定位。提示：直接重跑本脚本可续编（已完成的 .o 不会重编）。"
  exit 1
fi

echo "==> 构建完成"
ls -la "$BUILD_DIR"/IQmol.exe 2>/dev/null || \
  find "$BUILD_DIR" -maxdepth 2 -name "IQmol*.exe" 2>/dev/null || \
  echo "    未找到 IQmol.exe，请检查 build/ 下产物"
