#!/usr/bin/env bash
# IQmol Windows 运行期部署脚本（在 MINGW64 终端运行）
#
# 用途：编译成功后（build/bin/IQmol.exe 已生成），把运行时需要的
#       Qt 插件、MinGW 运行库、IQmol 资源（share/）复制到位，
#       使 bin/IQmol.exe 能直接双击运行。
#
# 用法：
#   bash deploy_windows.sh              # 部署到 build/ 下（默认，可直接运行）
#   bash deploy_windows.sh --stage DIR  # 额外把结果整理成可分发的 DIR/IQmol/
#
# 依据（来自 IQmol 源码的运行时查找规则）：
#   src/Main/IQmolApplication.C:101-155
#     - Windows 约定目录结构 IQmol/bin/IQmol.exe，
#       代码执行 dir.cdUp() 从 bin/ 上跳到 IQmol/，因此运行时根是应用目录的上一级。
#       本项目可执行文件在 build/bin/IQmol.exe -> 运行时根即 build/。
#     - QApplication::addLibraryPath(根/lib) 与 根/lib/plugins  -> Qt 插件放 lib/
#     - BABEL_LIBDIR  -> 根/lib/openbabel        （静态 OpenBabel 时不需要）
#     - BABEL_DATADIR -> 根/share/openbabel      （必需：元素/键参数等数据）
#   src/Util/Preferences.C:261-410,767-801
#     - 优先 应用目录/share/，回退 /usr/share/iqmol：
#         share/shaders      着色器（表面渲染等）
#         share/fragments    片段库
#         share/servers      服务器配置
#         share/qchem_option.db  等
#     - 应用目录/ffmpeg     可选：轨迹导出为视频
#
# 说明：脚本幂等，可重复运行；只复制、不删除用户已有文件。
set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ "$(basename "$SCRIPT_DIR")" = "scripts" ]; then
  SRC_DIR="$(dirname "$SCRIPT_DIR")"
else
  SRC_DIR="$SCRIPT_DIR"
fi

BUILD_DIR="$SRC_DIR/build"
BIN_DIR="$BUILD_DIR/bin"
MINGW_PREFIX="${MINGW_PREFIX:-/mingw64}"
if [ ! -d "$MINGW_PREFIX" ]; then
  for _p in /mingw64 /c/msys64/mingw64 /d/msys64/mingw64 /c/msys2/mingw64; do
    if [ -d "$_p" ]; then MINGW_PREFIX="$_p"; break; fi
  done
fi

STAGE_DIR=""
while [ $# -gt 0 ]; do
  case "$1" in
    --stage) STAGE_DIR="${2:-}"; shift 2 ;;
    *) shift ;;
  esac
done

echo "==> 源码根 : $SRC_DIR"
echo "==> 构建目录: $BUILD_DIR"
echo "==> MinGW : $MINGW_PREFIX"

#--------------------------------------------------------------------
# 0. 前置检查
#--------------------------------------------------------------------
EXE="$BIN_DIR/IQmol.exe"
if [ ! -f "$EXE" ]; then
  echo "ERROR: 未找到 $EXE" >&2
  echo "       请先运行 bash build_windows.sh 完成编译链接。" >&2
  exit 1
fi
echo "==> 找到可执行文件: $EXE"

copied=0
skip=0
copy_item() {
  # copy_item <源> <目标>
  if [ -e "$1" ]; then
    mkdir -p "$(dirname "$2")"
    cp -rf "$1" "$2" && copied=$((copied+1))
  else
    skip=$((skip+1))
  fi
}

#--------------------------------------------------------------------
# 1. Qt 运行时（DLL + 插件）
#    windeployqt 能自动分析 IQmol.exe 的 Qt 依赖并复制所需 DLL 与插件，
#    是首选。缺失时回退到手工复制常见 DLL（保证至少能启动）。
#--------------------------------------------------------------------
WINDEPLOYQT=""
for c in "$MINGW_PREFIX/bin/windeployqt.exe" \
         "$MINGW_PREFIX/bin/windeployqt6.exe" \
         "$(command -v windeployqt 2>/dev/null)" \
         "$(command -v windeployqt-qt5 2>/dev/null)"; do
  if [ -n "$c" ] && [ -x "$c" ]; then WINDEPLOYQT="$c"; break; fi
done

if [ -n "$WINDEPLOYQT" ]; then
  echo "==> 使用 windeployqt: $WINDEPLOYQT"
  # --no-translations: 不复制 Qt 自身翻译（IQmol 用自带 zh_CN.qm）
  # --no-opengl-sw   : 不复制软件 OpenGL 回退（体积大，且我们链接真实 opengl32）
  "$WINDEPLOYQT" --no-translations --no-opengl-sw --no-system-d3d-compiler \
      --dir "$BIN_DIR" "$EXE" 2>&1 | sed 's/^/    /' || \
    echo "    警告: windeployqt 返回非零，继续后续步骤"
else
  echo "==> 未找到 windeployqt，回退为手工复制 Qt DLL"
  echo "    （建议安装：pacman -S mingw-w64-x86_64-qt5-tools 以获得 windeployqt）"
  for dll in Qt5Core Qt5Gui Qt5Widgets Qt5Xml Qt5Network Qt5Sql \
             Qt5OpenGL Qt5PrintSupport; do
    # 优先从 MinGW 前缀复制对应的 .dll
    for cand in "$MINGW_PREFIX/bin/${dll}.dll" \
                "$MINGW_PREFIX/bin/lib${dll}.dll"; do
      [ -f "$cand" ] && copy_item "$cand" "$BIN_DIR/" && break
    done
  done
fi

#--------------------------------------------------------------------
# 1b. Qt 插件同步到 build/lib/ 与 build/lib/plugins/
#     源码 IQmolApplication.C:115-116 对 Windows 显式执行:
#        QApplication::addLibraryPath(path + "/lib")
#        QApplication::addLibraryPath(path + "/lib/plugins")
#     其中 path 为运行时根(=build/)。因此除 Qt 默认的 exe 同级目录外,
#     再把这些插件复制一份到 lib/ 下与源码逻辑对齐, 双保险。
#--------------------------------------------------------------------
echo "==> 同步 Qt 插件到 lib/ (与源码 addLibraryPath 对齐)"
mkdir -p "$BUILD_DIR/lib/plugins"
for sub in platforms styles imageformats iconengines platforminputcontexts; do
  for srcroot in "$BIN_DIR" "$MINGW_PREFIX/share/qt5/plugins" \
                 "$MINGW_PREFIX/lib/qt5/plugins"; do
    if [ -d "$srcroot/$sub" ]; then
      cp -rf "$srcroot/$sub" "$BUILD_DIR/lib/" 2>/dev/null && \
      cp -rf "$srcroot/$sub" "$BUILD_DIR/lib/plugins/" 2>/dev/null
    fi
  done
done

#--------------------------------------------------------------------
# 2. Qt 平台插件（必须；否则报 "could not find or load the Qt platform plugin windows"）
#    正常情况下 windeployqt 已复制，这里兜底确保存在。
#--------------------------------------------------------------------
if [ ! -d "$BIN_DIR/platforms" ]; then
  echo "==> 补装 Qt platforms 插件"
  mkdir -p "$BIN_DIR/platforms"
  for cand in "$MINGW_PREFIX/share/qt5/plugins/platforms/qwindows.dll" \
              "$MINGW_PREFIX/lib/qt5/plugins/platforms/qwindows.dll"; do
    [ -f "$cand" ] && copy_item "$cand" "$BIN_DIR/platforms/" && break
  done
fi
# 双保险：lib/ 下也要有
if [ ! -f "$BUILD_DIR/lib/platforms/qwindows.dll" ]; then
  for cand in "$BIN_DIR/platforms/qwindows.dll" \
              "$MINGW_PREFIX/share/qt5/plugins/platforms/qwindows.dll" \
              "$MINGW_PREFIX/lib/qt5/plugins/platforms/qwindows.dll"; do
    if [ -f "$cand" ]; then
      mkdir -p "$BUILD_DIR/lib/platforms"
      copy_item "$cand" "$BUILD_DIR/lib/platforms/"
      break
    fi
  done
fi

#--------------------------------------------------------------------
# 3. MinGW 运行库（动态链接 libstdc++/libgcc/libwinpthread 时必须，
#    否则在未装 MSYS2 的机器上双击会报缺少 DLL）
#--------------------------------------------------------------------
echo "==> 复制 MinGW 运行库"
for dll in libstdc++-6.dll libgcc_s_seh-1.dll libwinpthread-1.dll \
           libssp-0.dll; do
  if [ -f "$MINGW_PREFIX/bin/$dll" ]; then
    copy_item "$MINGW_PREFIX/bin/$dll" "$BIN_DIR/"
  fi
done

# 静态库内部可能引用的其他 DLL（存在则拷）
for dll in zlib1.dll libzstd.dll libssl-3-x64.dll libcrypto-3-x64.dll \
           libssh2-1.dll libarchive-13.dll libyaml-cpp.dll; do
  if [ -f "$MINGW_PREFIX/bin/$dll" ]; then
    copy_item "$MINGW_PREFIX/bin/$dll" "$BIN_DIR/"
  fi
done

#--------------------------------------------------------------------
# 4. IQmol 资源：share/
#    运行时根 = build/（可执行文件在 build/bin/IQmol.exe，源码 cdUp 一级）
#    Preferences.C 优先读 应用目录/share/
#--------------------------------------------------------------------
echo "==> 复制 IQmol 资源 share/"
if [ -d "$SRC_DIR/share" ]; then
  mkdir -p "$BUILD_DIR/share"
  cp -rf "$SRC_DIR/share/." "$BUILD_DIR/share/" && copied=$((copied+1))
else
  echo "    警告: 源树缺少 share/ 目录（$SRC_DIR/share），界面可能缺少着色器/片段库"
fi

# OpenBabel 数据 -> build/share/openbabel （BABEL_DATADIR）
OB_DATA="$SRC_DIR/modules/openbabel/data"
if [ -d "$OB_DATA" ]; then
  echo "==> 复制 OpenBabel 数据 -> share/openbabel"
  mkdir -p "$BUILD_DIR/share/openbabel"
  cp -rf "$OB_DATA/." "$BUILD_DIR/share/openbabel/" && copied=$((copied+1))
else
  echo "    警告: 未找到 modules/openbabel/data，OpenBabel 可能无法识别某些文件格式"
fi

#--------------------------------------------------------------------
# 5. 中文翻译（build_windows.sh 的 POST_BUILD 已生成 zh_CN.qm 到 bin/translations/）
#    这里兜底：若未生成且系统有 lrelease，则现场生成。
#--------------------------------------------------------------------
TS="$SRC_DIR/translations/zh_CN.ts"
QM_DIR="$BIN_DIR/translations"
if [ -f "$QM_DIR/zh_CN.qm" ]; then
  echo "==> 中文翻译已就位: $QM_DIR/zh_CN.qm"
elif [ -f "$TS" ]; then
  echo "==> 生成中文翻译 zh_CN.qm"
  LRELEASE=""
  for c in "$(command -v lrelease 2>/dev/null)" \
           "$(command -v lrelease-qt5 2>/dev/null)" \
           "$MINGW_PREFIX/bin/lrelease.exe"; do
    if [ -n "$c" ] && [ -x "$c" ]; then LRELEASE="$c"; break; fi
  done
  if [ -n "$LRELEASE" ]; then
    mkdir -p "$QM_DIR"
    "$LRELEASE" "$TS" -qm "$QM_DIR/zh_CN.qm" 2>&1 | sed 's/^/    /'
  else
    echo "    警告: 未找到 lrelease，界面将保持英文。"
    echo "          可安装后重跑，或手动执行：lrelease $TS -qm $QM_DIR/zh_CN.qm"
  fi
fi

#--------------------------------------------------------------------
# 6. OpenBabel 动态插件目录（静态 OpenBabel 时为占位；存在则复制）
#--------------------------------------------------------------------
if [ -d "$MINGW_PREFIX/lib/openbabel" ]; then
  echo "==> 复制 OpenBabel 插件（若为动态版）"
  mkdir -p "$BUILD_DIR/lib/openbabel"
  cp -rf "$MINGW_PREFIX/lib/openbabel/." "$BUILD_DIR/lib/openbabel/" 2>/dev/null || true
fi

#--------------------------------------------------------------------
# 7. 可选：--stage 整理为可分发的目录
#--------------------------------------------------------------------
if [ -n "$STAGE_DIR" ]; then
  echo "==> 整理分发包到 $STAGE_DIR/IQmol"
  mkdir -p "$STAGE_DIR/IQmol"
  cp -rf "$BIN_DIR" "$STAGE_DIR/IQmol/bin"
  [ -d "$BUILD_DIR/share" ] && cp -rf "$BUILD_DIR/share" "$STAGE_DIR/IQmol/share"
  [ -d "$BUILD_DIR/lib" ]   && cp -rf "$BUILD_DIR/lib"   "$STAGE_DIR/IQmol/lib"
  echo "    完成：$STAGE_DIR/IQmol/  （bin/ share/ lib/）"
fi

#--------------------------------------------------------------------
# 8. 汇总
#--------------------------------------------------------------------
echo ""
echo "==================== 部署完成 ===================="
echo "  可执行文件 : $EXE"
echo "  复制项     : $copied   跳过项: $skip"
[ -d "$BIN_DIR/platforms" ] && echo "  Qt 平台插件: $(ls "$BIN_DIR/platforms" 2>/dev/null | tr '\n' ' ')"
[ -d "$BUILD_DIR/share" ]   && echo "  资源目录   : $BUILD_DIR/share"
echo ""
echo "启动方式："
echo "  1) 命令行: cd \"$BIN_DIR\" && ./IQmol.exe"
echo "  2) 双击  : $EXE"
echo ""
echo "若启动仍报缺少某个 DLL，把完整报错贴出来即可定位。"
echo "=================================================="
