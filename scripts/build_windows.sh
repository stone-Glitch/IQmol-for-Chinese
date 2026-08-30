#!/usr/bin/env bash
# IQmol Windows 自动构建脚本（在 MINGW64 终端运行）
# 用法:
#   bash build_windows.sh                       # 自动下载 CMake 3.31 并构建
#   CMAKE_BIN="D:/cmake-3.31/bin/cmake.exe" bash build_windows.sh   # 用已有 3.31
#
# 脚本请放在 IQmol-src/ 根目录，或 IQmol-src/scripts/ 下。
# 把交付的 modules_CMakeLists.txt 放在同一目录可离线补全缺失文件。
set -u

# ===== 可调参数（可用环境变量覆盖）=====
CMAKE_BIN="${CMAKE_BIN:-cmake}"
MINGW_PREFIX="${MINGW_PREFIX:-/d/msys64/mingw64}"
JOBS="${JOBS:-4}"

# 推导源码根：脚本在 scripts/ 下则取上一级，否则取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ "$(basename "$SCRIPT_DIR")" = "scripts" ]; then
  SRC_DIR="$(dirname "$SCRIPT_DIR")"
else
  SRC_DIR="$SCRIPT_DIR"
fi
MODULES_DIR="$SRC_DIR/modules"

echo "==> 源码根: $SRC_DIR"

# ===== 1. 检查/补全 modules/CMakeLists.txt（构建 libQGLViewer 的聚合脚本）=====
if [ ! -f "$MODULES_DIR/CMakeLists.txt" ]; then
  echo "==> 缺失 modules/CMakeLists.txt，尝试恢复..."
  LOCAL_FIX="$SCRIPT_DIR/modules_CMakeLists.txt"
  if [ -f "$LOCAL_FIX" ]; then
    cp "$LOCAL_FIX" "$MODULES_DIR/CMakeLists.txt"
    echo "    已从本地 $LOCAL_FIX 复制"
  else
    URL="https://raw.githubusercontent.com/stone-Glitch/IQmol-for-Chinese/main/modules/CMakeLists.txt"
    echo "    从 $URL 下载..."
    if command -v curl >/dev/null 2>&1; then
      curl -fsSL "$URL" -o "$MODULES_DIR/CMakeLists.txt"
    elif command -v wget >/dev/null 2>&1; then
      wget -qO "$MODULES_DIR/CMakeLists.txt" "$URL"
    else
      echo "ERROR: 无 curl/wget，且同目录无 modules_CMakeLists.txt，请手动放置该文件到 $MODULES_DIR/CMakeLists.txt"
      exit 1
    fi
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

# ===== 3. 检查 OpenBabel external 依赖（墙内无法联网下载，需预置）=====
OB_EXT="$MODULES_DIR/openbabel/external"
for d in maeparser-v1.2.3 coordgen-master rapidjson-1.1.0; do
  if [ ! -d "$OB_EXT/$d" ]; then
    echo "WARN: 缺少 OpenBabel 依赖 $OB_EXT/$d"
    echo "      请将 IQmol-openbabel-deps.tar.gz 解压到 $MODULES_DIR/openbabel/ 后重试"
  fi
done

# ===== 4. configure =====
BUILD_DIR="$SRC_DIR/build"
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"
cd "$BUILD_DIR" || exit 1

"$CMAKE_BIN" .. \
  -G "MinGW Makefiles" \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_PREFIX_PATH="$MINGW_PREFIX" \
  -DCMAKE_CXX_FLAGS="-fpermissive -std=gnu++17 -Wno-deprecated" \
  -DCMAKE_MAKE_PROGRAM="mingw32-make" \
  -DBOOST_ROOT="$MINGW_PREFIX"
if [ $? -ne 0 ]; then
  echo "ERROR: cmake configure 失败，详见上方输出"
  exit 1
fi

# ===== 5. 编译 =====
mingw32-make -j"$JOBS"
if [ $? -ne 0 ]; then
  echo "ERROR: 编译失败，请把输出贴出以便排查（GCC 16.x 较新，可能需要额外补丁）"
  exit 1
fi

echo "==> 构建完成，产物: $BUILD_DIR/IQmol.exe"
