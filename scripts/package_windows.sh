#!/usr/bin/env bash
# IQmol 中文版 Windows 分发包制作脚本（在 MINGW64 终端运行）
#
# 流水线定位：
#   build_windows.sh   ->  编译链接生成 build/bin/IQmol.exe
#   deploy_windows.sh  ->  把 Qt 运行库/插件/share 资源复制到位
#   本脚本            ->  调用 deploy 整理出 IQmol/{bin,share,lib}，
#                          写中文 README，再用 7z 压成可分发压缩包。
#
# 用法：
#   bash package_windows.sh                # 默认打包为 dist/IQmol-win64-<ver>-zh_CN.7z
#   bash package_windows.sh --zip          # 同时用 PowerShell 出一份 .zip（给没有 7z 的人）
#   bash package_windows.sh --out DIR      # 指定输出目录（默认 <源码根>/dist）
#
# 产物结构（解压即用，要求解压到纯英文路径）：
#   IQmol/
#     bin/IQmol.exe   <- 双击运行
#     share/          <- 着色器/片段库/力场数据/选项库
#     lib/            <- Qt 插件 + MinGW 运行库
set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ "$(basename "$SCRIPT_DIR")" = "scripts" ]; then
  SRC_DIR="$(dirname "$SCRIPT_DIR")"
else
  SRC_DIR="$SCRIPT_DIR"
fi

BUILD_DIR="$SRC_DIR/build"
BIN_DIR="$BUILD_DIR/bin"
EXE="$BIN_DIR/IQmol.exe"

OUT_DIR=""
MAKE_ZIP=0
while [ $# -gt 0 ]; do
  case "$1" in
    --out) OUT_DIR="${2:-}"; shift 2 ;;
    --zip) MAKE_ZIP=1; shift ;;
    *) shift ;;
  esac
done
[ -z "$OUT_DIR" ] && OUT_DIR="$SRC_DIR/dist"

#--------------------------------------------------------------------
# 1. 前置检查
#--------------------------------------------------------------------
if [ ! -f "$EXE" ]; then
  echo "ERROR: 未找到 $EXE" >&2
  echo "       请先运行 bash build_windows.sh 完成编译链接。" >&2
  exit 1
fi
echo "==> 源码根 : $SRC_DIR"
echo "==> 构建产物: $EXE"

#--------------------------------------------------------------------
# 2. 版本号（取自 CMakeLists.txt 的 project(... VERSION x.y.z)）
#--------------------------------------------------------------------
VER=""
_CML="$SRC_DIR/CMakeLists.txt"
if [ -f "$_CML" ]; then
  VER="$(sed -n 's/^project([^)]*VERSION[[:space:]]*\([0-9][0-9.]*\).*/\1/p' "$_CML" | head -1)"
fi
[ -z "$VER" ] && VER="unknown"
echo "==> 版本号 : $VER"

#--------------------------------------------------------------------
# 3. 部署（--stage 整理出 OUT_DIR/IQmol/{bin,share,lib}）
#--------------------------------------------------------------------
echo "==> 调用 deploy_windows.sh 整理分发目录"
bash "$SCRIPT_DIR/deploy_windows.sh" --stage "$OUT_DIR" || {
  echo "ERROR: 部署失败，未生成分发目录" >&2
  exit 1
}

STAGE="$OUT_DIR/IQmol"
if [ ! -f "$STAGE/bin/IQmol.exe" ]; then
  echo "ERROR: 部署后仍未生成 $STAGE/bin/IQmol.exe" >&2
  exit 1
fi

#--------------------------------------------------------------------
# 3b. 发布前自检：分发包必须自包含，否则别人机器上无法“解压即用”
#--------------------------------------------------------------------
echo "==> 发布前自检：分发包自包含性"
_crit="libstdc++-6.dll libgcc_s_seh-1.dll libwinpthread-1.dll libgfortran-5.dll libquadmath-0.dll libgomp-1.dll"
_missing=""
for _d in $_crit; do
  [ -f "$STAGE/bin/$_d" ] || _missing="$_missing $_d"
done
if [ -n "$_missing" ]; then
  echo "ERROR: 分发包 bin/ 缺失关键运行库:$_missing" >&2
  echo "       deploy 的终检应已拦截，若仍出现请确认在 MSYS2 MINGW64 终端运行且对应包已安装:" >&2
  echo "         pacman -S mingw-w64-x86_64-gcc-libs mingw-w64-x86_64-gcc-fortran" >&2
  exit 1
fi
# 严禁随附 Windows 系统 DLL（每台机器自带，随附反而可能引发版本冲突）
_sys=$(ls "$STAGE/bin" 2>/dev/null | grep -E "api-ms-win|^KERNEL|^ntdll|^win32u|OPENGL32|GLU32|^USER32|^GDI32|System32" || true)
if [ -n "$_sys" ]; then
  echo "ERROR: 分发包 bin/ 误含 Windows 系统 DLL（下列文件不应随附）:" >&2
  echo "$_sys" >&2
  echo "       请更新 deploy_windows.sh（已修复 _find_dll 排除系统目录）后重跑。" >&2
  exit 1
fi
echo "    OK: 关键运行库齐全，且无系统 DLL 污染"
# 目录嵌套自检：share/share、bin/bin 任一存在即报错
for _n in share/share bin/bin lib/lib; do
  [ -e "$STAGE/$_n" ] && { echo "ERROR: 检测到目录嵌套 $STAGE/$_n，部署脚本需重跑清洗"; exit 1; }
done

#--------------------------------------------------------------------
# 4. 写中文 README（解压即用说明）
#--------------------------------------------------------------------
cat > "$STAGE/README_zh_CN.txt" <<TXT
IQmol ${VER} 中文版（Windows 64 位）
====================================

【运行】
  解压后直接双击  bin/IQmol.exe  即可。界面与内置帮助均为简体中文，
  首次运行自动使用中文。

【重要】请将本目录解压到“纯英文、不含空格”的路径下，例如：
        D:\IQmol\   或   C:\Apps\IQmol\
  避免放在“桌面”“下载”等含中文或空格的路径，以防部分组件查找资源失败。

【已包含】
  - Qt 运行库与平台插件（双击即可运行，无需安装 Qt）
  - OpenBabel 力场/元素数据（力场计算、文件格式转换可用）
  - 着色器 / 片段库 / Q-Chem 选项库
  - 简体中文翻译 zh_CN.qm（界面与帮助）

【可选】
  - 将轨迹导出为视频需要另行安装 ffmpeg 并加入系统 PATH。

【技术支持与反馈】
  项目仓库：https://github.com/stone-Glitch/IQmol-for-Chinese
TXT
echo "==> 已写入 README: $STAGE/README_zh_CN.txt"

#--------------------------------------------------------------------
# 5. 打包
#--------------------------------------------------------------------
PKG_NAME="IQmol-win64-${VER}-zh_CN"
cd "$OUT_DIR"

if command -v 7z >/dev/null 2>&1; then
  echo "==> 7z 打包: $PKG_NAME.7z"
  7z a -t7z -mx=9 -m0=LZMA2 "$PKG_NAME.7z" IQmol >/dev/null \
    && echo "    完成: $OUT_DIR/$PKG_NAME.7z  ($(du -h "$PKG_NAME.7z" | cut -f1))"
else
  echo "    未找到 7z，回退为 PowerShell 生成 .zip"
  MAKE_ZIP=1
fi

if [ "$MAKE_ZIP" -eq 1 ]; then
  echo "==> 生成 $PKG_NAME.zip (PowerShell Compress-Archive)"
  powershell -NoProfile -Command \
    "Compress-Archive -Path 'IQmol' -DestinationPath '$PKG_NAME.zip' -Force" \
    && echo "    完成: $OUT_DIR/$PKG_NAME.zip  ($(du -h "$PKG_NAME.zip" | cut -f1))"
fi

echo ""
echo "==================== 打包完成 ===================="
echo "  输出目录: $OUT_DIR"
ls -lh "$OUT_DIR"/$PKG_NAME.* 2>/dev/null
echo "=================================================="
