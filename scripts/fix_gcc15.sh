#!/usr/bin/env bash
# GCC 15+ 兼容补丁：给"用了 uint16_t/uint32_t 等类型但未显式 #include <cstdint>"
# 的 C++ 实现文件补上包含。GCC 15 起标准库头不再间接引入 <cstdint>，
# 老代码（yaml-cpp/openmesh/openbabel/IQmol）会批量报 "'uint16_t' was not declared"。
# 用法: bash fix_gcc15.sh [源码根]   （默认 /d/IQmol/IQmol-src）
set -u
SRC="${1:-/d/IQmol/IQmol-src}"
cd "$SRC" 2>/dev/null || { echo "ERROR: 源码根不存在: $SRC"; exit 1; }

# 白名单来自静态扫描(仅参与构建的 C++ 实现文件)
FILES="
modules/yaml-cpp/src/emitterutils.cpp
modules/openmesh/src/OpenMesh/Core/IO/reader/OFFReader.cc
modules/openmesh/src/OpenMesh/Core/IO/reader/PLYReader.cc
modules/openmesh/src/OpenMesh/Core/IO/writer/OFFWriter.cc
modules/openmesh/src/OpenMesh/Core/IO/writer/PLYWriter.cc
modules/openbabel/src/bitvec.cpp
modules/openbabel/src/formats/stlformat.cpp
src/Layer/OctreeLayer.C
"

n=0; p=0
for f in $FILES; do
  n=$((n+1))
  if [ ! -f "$f" ]; then echo "  [跳过] 不存在: $f"; continue; fi
  if grep -q "#include <cstdint>" "$f"; then echo "  [已修] $f"; p=$((p+1)); continue; fi
  # 在第一个 #include 前插入一行
  sed -i "0,/#include/s//#include <cstdint> \/* GCC15+ fix *\/\n#include/" "$f"
  if grep -q "#include <cstdint>" "$f"; then echo "  [补丁] $f"; p=$((p+1)); else echo "  [失败] $f"; fi
done
echo "结果: $p/$n 个文件就绪。可重新运行 build_windows.sh 续编(无需 --clean)。"
