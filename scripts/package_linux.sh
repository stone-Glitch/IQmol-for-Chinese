#!/usr/bin/env bash
# IQmol 中文版 Linux 分发包制作脚本
#
# 流水线定位：
#   configure + make         ->  build/IQmol（CMake POST_BUILD 已生成 translations/zh_CN.qm）
#   本脚本                    ->  收集 bin/lib/share/translations，
#                                写 README / run.sh，压成可分发 tar.gz
#
# 用法：
#   bash scripts/package_linux.sh                     # 输出 dist/IQmol-linux-x86_64.tar.gz
#   bash scripts/package_linux.sh --out DIR           # 指定输出目录
#   bash scripts/package_linux.sh --build DIR         # 指定构建目录（默认 <源码根>/build）
#   bash scripts/package_linux.sh --no-strip          # 不 strip 可执行文件（便于调试）
#
# 产物结构（解压即用）：
#   IQmol-linux-x86_64/
#     bin/IQmol                    <- 可执行文件
#     bin/translations/zh_CN.qm    <- 【关键】与 applicationDirPath() 对齐
#     translations/zh_CN.qm        <- 【关键】兼容包根布局（旧版 run.sh / 手工布局）
#     lib/                         <- Qt5/OpenBabel/OpenMesh 等运行库 + 插件
#     share/                       <- shaders / fragments / openbabel 数据
#     run.sh                       <- 一键启动
#
# 【为什么 zh_CN.qm 要放两份】
#   IQmolApplication::loadTranslations() 按 applicationDirPath()（= bin/）
#   推算翻译文件位置，而 Linux 包历来把 qm 放在包根的 translations/。
#   历史 bug（reA22A）：只放包根时，**只有恰好从包根目录启动才加载成功**
#   （偶然命中 cwd/translations），从桌面图标或 run.sh 之外的路径启动
#   都会静默回退英文。现同时放两处，并已在源码侧补上 ../translations
#   搜索路径，形成双保险。
set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ "$(basename "$SCRIPT_DIR")" = "scripts" ]; then
  SRC_DIR="$(dirname "$SCRIPT_DIR")"
else
  SRC_DIR="$SCRIPT_DIR"
fi

BUILD_DIR="$SRC_DIR/build"
OUT_DIR=""
DO_STRIP=1
while [ $# -gt 0 ]; do
  case "$1" in
    --out)       OUT_DIR="${2:-}"; shift 2 ;;
    --build)     BUILD_DIR="${2:-}"; shift 2 ;;
    --no-strip)  DO_STRIP=0; shift ;;
    *) shift ;;
  esac
done
[ -z "$OUT_DIR" ] && OUT_DIR="$SRC_DIR/dist"

PKG_NAME="IQmol-linux-x86_64"
STAGE="$OUT_DIR/$PKG_NAME"

#--------------------------------------------------------------------
# 1. 前置检查
#--------------------------------------------------------------------
EXE="$BUILD_DIR/IQmol"
if [ ! -f "$EXE" ]; then
  echo "ERROR: 未找到 $EXE" >&2
  echo "       请先完成构建（cmake + make）。" >&2
  exit 1
fi

TS="$SRC_DIR/translations/zh_CN.ts"
if [ ! -f "$TS" ]; then
  echo "ERROR: 未找到 $TS" >&2
  exit 1
fi

echo "==> 源码根  : $SRC_DIR"
echo "==> 构建目录: $BUILD_DIR"
echo "==> 输出目录: $OUT_DIR"

#--------------------------------------------------------------------
# 2. 版本号
#--------------------------------------------------------------------
VER=""
if [ -f "$SRC_DIR/CMakeLists.txt" ]; then
  VER="$(sed -n 's/.*project[[:space:]]*([^)]*VERSION[[:space:]]\+\([0-9][0-9.]*\).*/\1/p' \
        "$SRC_DIR/CMakeLists.txt" | head -1)"
fi
[ -z "$VER" ] && VER="0.0.0"
echo "==> 版本号  : $VER"

#--------------------------------------------------------------------
# 3. 准备 staging 目录
#--------------------------------------------------------------------
rm -rf "$STAGE"
mkdir -p "$STAGE/bin" "$STAGE/lib" "$STAGE/share" "$STAGE/translations"

#--------------------------------------------------------------------
# 4. 可执行文件
#--------------------------------------------------------------------
cp "$EXE" "$STAGE/bin/IQmol"
chmod +x "$STAGE/bin/IQmol"
if [ "$DO_STRIP" = "1" ] && command -v strip >/dev/null 2>&1; then
  strip --strip-unneeded "$STAGE/bin/IQmol" 2>/dev/null || true
fi
echo "==> 已复制可执行文件"

#--------------------------------------------------------------------
# 5. 【关键】翻译文件 —— 放两处
#--------------------------------------------------------------------
LRELEASE="$(command -v lrelease 2>/dev/null || true)"
if [ -z "$LRELEASE" ] && [ -x /usr/lib/qt5/bin/lrelease ]; then
  LRELEASE=/usr/lib/qt5/bin/lrelease
fi
if [ -z "$LRELEASE" ]; then
  echo "ERROR: 未找到 lrelease，无法生成 zh_CN.qm" >&2
  echo "       安装：sudo apt install qttools5-dev-tools" >&2
  exit 1
fi

"$LRELEASE" "$TS" -qm "$STAGE/translations/zh_CN.qm" >/dev/null 2>&1 || {
  echo "ERROR: lrelease 生成 zh_CN.qm 失败" >&2
  exit 1
}
# 位置 1：包根 translations/（历史布局）
# 位置 2：bin/translations/ （与 applicationDirPath() 对齐）
mkdir -p "$STAGE/bin/translations"
cp "$STAGE/translations/zh_CN.qm" "$STAGE/bin/translations/zh_CN.qm"
echo "==> 已放置翻译文件（包根 + bin/translations 双份）"
echo "     包根: $(stat -c%s "$STAGE/translations/zh_CN.qm") 字节"
echo "     bin : $(stat -c%s "$STAGE/bin/translations/zh_CN.qm") 字节"

#--------------------------------------------------------------------
# 6. 运行库 + 插件（用 ldd 递归收集）
#--------------------------------------------------------------------
collect_libs() {
  local bin="$1" out="$2"
  mkdir -p "$out"
  local seen="/tmp/.iqmol_pkg_libs.$$"
  : > "$seen"
  local queue="$bin"
  while [ -n "$queue" ]; do
    local cur="${queue%% *}"
    if [ "$cur" = "$queue" ]; then queue=""; else queue="${queue#* }"; fi
    [ -z "$cur" ] && continue
    ldd "$cur" 2>/dev/null | awk '/=> \//{print $3}' | while read -r lib; do
      [ -z "$lib" ] && continue
      # 跳过系统基础库：glibc / 动态链接器 / 内核接口库
      case "$(basename "$lib")" in
        libc.so.*|libm.so.*|libdl.so.*|libpthread.so.*|librt.so.*|\
        libgcc_s.so.*|libstdc++.so.*|ld-linux*|libresolv.so.*|libutil.so.*|\
        libnsl.so.*|libcrypt.so.*|libz.so.*|libexpat.so.*|libuuid.so.*|\
        libselinux.so.*|libpcre*.so.*|libffi.so.*|libbz2.so.*|liblzma.so.*|\
        libzstd.so.*|libcom_err.so.*|libkeyutils.so.*|libgssapi_krb5.so.*|\
        libkrb5*.so.*|libk5crypto.so.*|libkrb5support.so.*|libnettle.so.*|\
        libhogweed.so.*|libgmp.so.*|libidn2.so.*|libunistring.so.*|\
        libtasn1.so.*|libp11-kit.so.*|libcap.so.*|libgcrypt.so.*|libsystemd.so.*)
          continue ;;
      esac
      if ! grep -qx "$lib" "$seen" 2>/dev/null; then
        echo "$lib" >> "$seen"
        cp -L "$lib" "$out/" 2>/dev/null || true
      fi
    done
  done
  rm -f "$seen"
}

echo "==> 正在收集运行库（可能需要一分钟）..."
collect_libs "$STAGE/bin/IQmol" "$STAGE/lib"

# Qt 插件
# 构建目录通常没有插件（Qt 插件来自 Qt 安装目录），故回退到系统 Qt 插件路径。
QT_PLUGIN_CANDIDATES=(
  "$BUILD_DIR/lib/plugins"
  "$BUILD_DIR/plugins"
  "$(qtpaths --plugin-dir 2>/dev/null)"
  "$(qmake -query QT_INSTALL_PLUGINS 2>/dev/null)"
  /usr/lib/x86_64-linux-gnu/qt5/plugins
  /usr/lib/qt5/plugins
)
_plugins_done=0
for _pdir in "${QT_PLUGIN_CANDIDATES[@]}"; do
  [ -z "$_pdir" ] && continue
  if [ -d "$_pdir/platforms" ]; then
    mkdir -p "$STAGE/lib/plugins"
    # 只收运行必需的几类插件，避免包体膨胀
    for _sub in platforms platformthemes imageformats iconengines \
                platforminputcontexts xcbglintegrations sqldrivers \
                printsupport styles; do
      [ -d "$_pdir/$_sub" ] && cp -rL "$_pdir/$_sub" "$STAGE/lib/plugins/" 2>/dev/null
    done
    echo "     插件 <- $_pdir"
    _plugins_done=1
    break
  fi
done
[ "$_plugins_done" = "0" ] && \
  echo "     ⚠ 未找到 Qt 插件目录（缺少 platforms/ 会导致无法启动 GUI）" >&2

# share 资源
# 优先构建目录（部分构建会把资源拷进去），回退源码树。
# 各资源的实际归属不同，故逐个处理：
#   shaders / fragments / qchem_option.db  -> <源码根>/share/
#   openbabel 数据                          -> modules/openbabel/data 或 <源码根>/share/openbabel
copy_dir_first() {
  # copy_dir_first <目标名> <候选源...>
  local name="$1"; shift
  for _cand in "$@"; do
    if [ -d "$_cand" ]; then
      mkdir -p "$STAGE/share/$name"
      cp -rL "$_cand"/. "$STAGE/share/$name/" 2>/dev/null || true
      echo "     share/$name <- $_cand"
      return 0
    fi
  done
  echo "     ⚠ share/$name 未找到（候选：$*）" >&2
  return 1
}

echo "==> 收集 share 资源..."
copy_dir_first shaders \
  "$BUILD_DIR/share/shaders" "$SRC_DIR/share/shaders" || true
copy_dir_first fragments \
  "$BUILD_DIR/share/fragments" "$SRC_DIR/share/fragments" || true
copy_dir_first openbabel \
  "$BUILD_DIR/share/openbabel" "$SRC_DIR/share/openbabel" \
  "$SRC_DIR/modules/openbabel/data" "/usr/share/openbabel" || {
  echo "     提示：openbabel 数据来自子模块或系统安装。若 modules/ 为空且" >&2
  echo "       系统未装 openbabel，先解包：tar xzf submodules-package/IQmol-submodules.tar.gz -C modules/" >&2
}

# [reA22A] OpenBabel 运行期插件（格式/力场 .so），便携包自带以免依赖系统安装
OB_LIB_CANDIDATES=(
  "/usr/lib/openbabel"
  "/usr/lib/x86_64-linux-gnu/openbabel"
)
for _ob in "${OB_LIB_CANDIDATES[@]}"; do
  if [ -d "$_ob" ] && ls "$_ob"/*/  >/dev/null 2>&1; then
    mkdir -p "$STAGE/lib/openbabel"
    cp -rL "$_ob"/. "$STAGE/lib/openbabel/" 2>/dev/null || true
    echo "     lib/openbabel <- $_ob ($(du -sh "$STAGE/lib/openbabel" | cut -f1))"
    break
  fi
done

# qchem 选项库（单文件）
for _cand in "$BUILD_DIR/share/qchem_option.db" \
             "$SRC_DIR/share/qchem_option.db"; do
  if [ -f "$_cand" ]; then
    cp "$_cand" "$STAGE/share/"
    echo "     share/qchem_option.db <- $_cand"
    break
  fi
done

echo "==> 运行库: $(ls "$STAGE/lib" 2>/dev/null | wc -l) 个"
echo "==> 插件目录: $(ls "$STAGE/lib/plugins" 2>/dev/null | wc -l) 个"

#--------------------------------------------------------------------
# 7. run.sh
#--------------------------------------------------------------------
cat > "$STAGE/run.sh" <<'RUNSH'
#!/usr/bin/env bash
# IQmol 中文版 一键启动脚本（Linux x86_64）
#
# 作用：不安装、不污染系统，直接以本目录为根运行 IQmol。
#      自动设置 LD_LIBRARY_PATH / QT_PLUGIN_PATH / BABEL_DATADIR，
#      并把资源路径写入 IQmol 偏好（IQmol 在 Linux 下硬编码
#      /usr/share/iqmol，无法用环境变量覆盖）。
#
# 用法：
#   ./run.sh                 # 启动
#   ./run.sh 分子文件.xyz     # 启动并打开指定文件
set -u

SOURCE="${BASH_SOURCE[0]}"
while [ -L "$SOURCE" ]; do
  DIR="$(cd -P "$(dirname "$SOURCE")" && pwd)"
  SOURCE="$(readlink "$SOURCE")"
  [[ $SOURCE != /* ]] && SOURCE="$DIR/$SOURCE"
done
ROOT="$(cd -P "$(dirname "$SOURCE")" && pwd)"

BIN="$ROOT/bin/IQmol"
[ -x "$BIN" ] || { echo "ERROR: 未找到可执行文件 $BIN" >&2; exit 1; }

# ---- 运行时环境 ----
export LD_LIBRARY_PATH="$ROOT/lib:${LD_LIBRARY_PATH:-}"
export QT_PLUGIN_PATH="$ROOT/lib/plugins"
export QT_QPA_PLATFORM_PLUGIN_PATH="$ROOT/lib/plugins/platforms"
export BABEL_DATADIR="$ROOT/share/openbabel"
# [reA22A] OpenBabel 运行期插件也指向包内，解压即用、不依赖系统安装
if [ -d "$ROOT/lib/openbabel" ]; then
  OB_SUB="$(find "$ROOT/lib/openbabel" -mindepth 1 -maxdepth 1 -type d | head -1)"
  export BABEL_LIBDIR="${OB_SUB:-$ROOT/lib/openbabel}"
fi

# ---- [reA22A] 切到包根目录再启动 ----
# 源码侧已补 ../translations 搜索路径，这里再明确 cd 一次形成双保险；
# 否则用户从其它目录调用本脚本时，翻译文件可能因 cwd 不同而找不到。
cd "$ROOT" || exit 1

# ---- 资源路径注入 ----
CONF_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/iqmol.org"
CONF="$CONF_DIR/IQmol.conf"
mkdir -p "$CONF_DIR"

needs_write=0
if [ ! -f "$CONF" ]; then
  needs_write=1
else
  if ! grep -q "^ShaderDirectory=$ROOT/share/shaders" "$CONF" 2>/dev/null; then
    needs_write=1
  fi
fi

if [ "$needs_write" = "1" ]; then
  if [ -f "$CONF" ]; then
    grep -v -E "^(ShaderDirectory|FragmentDirectory|QChemDatabaseFilePath|ServerConfigurationDirectory|FavouriteDirectory)=" \
       "$CONF" > "$CONF.tmp" 2>/dev/null && mv "$CONF.tmp" "$CONF"
  fi
  if ! grep -q "^\[General\]" "$CONF" 2>/dev/null; then
    printf '[General]\n' >> "$CONF"
  fi
  {
    echo "ShaderDirectory=$ROOT/share/shaders"
    echo "FragmentDirectory=$ROOT/share/fragments"
    echo "QChemDatabaseFilePath=$ROOT/share/qchem_option.db"
  } >> "$CONF"
  echo "[run.sh] 已写入资源路径到 $CONF"
fi

# ---- 启动 ----
exec "$BIN" "$@"
RUNSH
chmod +x "$STAGE/run.sh"

#--------------------------------------------------------------------
# 8. 自检：翻译文件必须两处都在
#--------------------------------------------------------------------
_missing=0
for _q in "$STAGE/translations/zh_CN.qm" "$STAGE/bin/translations/zh_CN.qm"; do
  if [ ! -f "$_q" ]; then
    echo "ERROR: 分发包缺少翻译文件 $_q" >&2
    _missing=1
  fi
done
if [ "$_missing" = "1" ]; then
  echo "       提示：QQm 必须同时存在于包根 translations/ 与 bin/translations/。" >&2
  echo "       原因见脚本头部注释（reA22A）。" >&2
  exit 1
fi
echo "==> 翻译文件自检通过（两处均在）"

#--------------------------------------------------------------------
# 9. 打包
#--------------------------------------------------------------------
TARBALL="$OUT_DIR/$PKG_NAME.tar.gz"
( cd "$OUT_DIR" && tar czf "$TARBALL" "$PKG_NAME" )
echo "==> 已生成: $TARBALL ($(du -h "$TARBALL" | cut -f1))"
echo
echo "结构预览:"
tar tzf "$TARBALL" | grep -E "bin/IQmol$|\.qm$|run\.sh$" | sed 's/^/    /'
