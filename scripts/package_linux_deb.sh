#!/usr/bin/env bash
# IQmol 中文版 Debian/Ubuntu 安装包制作脚本
#
# 流水线定位：
#   build/IQmol                    <- cmake + make 产物
#   scripts/package_linux.sh       <- 生成自包含 tar.gz（dist/IQmol-linux-x86_64/）
#   本脚本                          <- 把上面的 staging 重排成 FHS 布局，打成 .deb
#
# 用法：
#   bash scripts/package_linux_deb.sh                 # 输出 dist/iqmol_<ver>_amd64.deb
#   bash scripts/package_linux_deb.sh --out DIR       # 指定输出目录
#   bash scripts/package_linux_deb.sh --no-strip      # 不 strip
#
# 安装布局（符合 FHS，同时命中 IQmol 硬编码路径）：
#   /usr/bin/iqmol                                    <- 启动包装脚本
#   /usr/lib/iqmol/IQmol                              <- 可执行文件
#   /usr/lib/iqmol/lib/                               <- 随包 Qt/OpenBabel/OpenMesh 运行库
#   /usr/lib/iqmol/plugins/                           <- Qt 插件
#   /usr/lib/iqmol/translations/zh_CN.qm              <- applicationDirPath()/translations
#   /usr/lib/iqmol/openbabel/                         <- OpenBabel 运行期插件 (BABEL_LIBDIR)
#   /usr/share/iqmol/shaders|fragments|openbabel|...  <- Preferences.cpp 硬编码 /usr/share/iqmol
#   /usr/share/applications/iqmol.desktop             <- 应用菜单
#   /usr/share/icons/hicolor/512x512/apps/iqmol.png
#
# 为什么翻译要放 /usr/lib/iqmol/translations：
#   IQmolApplication::loadTranslations() 会探测
#     applicationDirPath()/translations
#     applicationDirPath()/../share/iqmol/translations
#   二进制位于 /usr/lib/iqmol，故前者 = /usr/lib/iqmol/translations；
#   后者会算成 /usr/lib/share/iqmol/translations（不存在），故必须放前者。
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
    --out)      OUT_DIR="${2:-}"; shift 2 ;;
    --build)    BUILD_DIR="${2:-}"; shift 2 ;;
    --no-strip) DO_STRIP=0; shift ;;
    *) shift ;;
  esac
done
[ -z "$OUT_DIR" ] && OUT_DIR="$SRC_DIR/dist"

PKG="iqmol"
EXE="$BUILD_DIR/IQmol"
TARBALL_DIR="$OUT_DIR/IQmol-linux-x86_64"

#--------------------------------------------------------------------
# 1. 前置检查
#--------------------------------------------------------------------
if [ ! -f "$EXE" ]; then
  echo "ERROR: 未找到 $EXE，请先构建（cmake -B build && cmake --build build）" >&2
  exit 1
fi
if [ ! -d "$TARBALL_DIR/lib" ]; then
  echo "==> 未找到已收集的运行库，先运行 package_linux.sh"
  bash "$SRC_DIR/scripts/package_linux.sh" --build "$BUILD_DIR" --out "$OUT_DIR" || exit 1
fi

VER="$(sed -n 's/.*project[[:space:]]*([^)]*VERSION[[:space:]]\+\([0-9][0-9.]*\).*/\1/p' "$SRC_DIR/CMakeLists.txt" | head -1)"
[ -z "$VER" ] && VER="0.0.0"
ARCH="$(dpkg --print-architecture 2>/dev/null || echo amd64)"

echo "==> 版本: $VER  架构: $ARCH"

STAGE="$OUT_DIR/deb/${PKG}_${VER}_${ARCH}"
rm -rf "$STAGE"
mkdir -p "$STAGE/DEBIAN" \
         "$STAGE/usr/bin" \
         "$STAGE/usr/lib/iqmol/lib" \
         "$STAGE/usr/lib/iqmol/plugins" \
         "$STAGE/usr/lib/iqmol/translations" \
         "$STAGE/usr/share/iqmol" \
         "$STAGE/usr/share/applications" \
         "$STAGE/usr/share/icons/hicolor/512x512/apps" \
         "$STAGE/usr/share/metainfo" \
         "$STAGE/usr/share/doc/$PKG"

#--------------------------------------------------------------------
# 2. 可执行文件与运行库
#--------------------------------------------------------------------
install -m 0755 "$EXE" "$STAGE/usr/lib/iqmol/IQmol"
if [ "$DO_STRIP" = "1" ] && command -v strip >/dev/null 2>&1; then
  strip --strip-unneeded "$STAGE/usr/lib/iqmol/IQmol" 2>/dev/null || true
fi
cp -a "$TARBALL_DIR/lib/." "$STAGE/usr/lib/iqmol/lib/"
if [ -d "$TARBALL_DIR/lib/plugins" ]; then
  cp -a "$TARBALL_DIR/lib/plugins/." "$STAGE/usr/lib/iqmol/plugins/"
fi
if [ -d "$TARBALL_DIR/lib/openbabel" ]; then
  cp -a "$TARBALL_DIR/lib/openbabel" "$STAGE/usr/lib/iqmol/openbabel"
fi
echo "==> 已放置二进制与 $(find "$STAGE/usr/lib/iqmol/lib" -type f | wc -l) 个运行库"

#--------------------------------------------------------------------
# 3. 翻译（应用 + Qt 基础）
#--------------------------------------------------------------------
cp -a "$TARBALL_DIR/translations/zh_CN.qm" "$STAGE/usr/lib/iqmol/translations/zh_CN.qm"
mkdir -p "$STAGE/usr/share/iqmol/translations"
cp -a "$TARBALL_DIR/translations/zh_CN.qm" "$STAGE/usr/share/iqmol/translations/zh_CN.qm"
# Qt 标准对话框（确定/取消/文件选择）中文
for q in qt_zh_CN.qm qtbase_zh_CN.qm; do
  for cand in "/usr/share/qt5/translations/$q" \
              "/usr/lib/x86_64-linux-gnu/qt5/translations/$q"; do
    if [ -f "$cand" ]; then
      cp -a "$cand" "$STAGE/usr/lib/iqmol/translations/$q"
      echo "     Qt 翻译 <- $cand"
      break
    fi
  done
done

#--------------------------------------------------------------------
# 4. share 资源（Preferences.cpp 硬编码 /usr/share/iqmol）
#--------------------------------------------------------------------
for d in shaders fragments openbabel; do
  if [ -d "$TARBALL_DIR/share/$d" ]; then
    cp -a "$TARBALL_DIR/share/$d" "$STAGE/usr/share/iqmol/"
    echo "     share/$d <- $(du -sh "$TARBALL_DIR/share/$d" | cut -f1)"
  fi
done
[ -f "$TARBALL_DIR/share/qchem_option.db" ] && \
  cp -a "$TARBALL_DIR/share/qchem_option.db" "$STAGE/usr/share/iqmol/"

# 示例文件（可选，放 doc 下避免污染 /usr/share/iqmol）
if [ -d "$TARBALL_DIR/samples" ]; then
  cp -a "$TARBALL_DIR/samples" "$STAGE/usr/share/doc/$PKG/samples"
fi

#--------------------------------------------------------------------
# 5. 启动包装脚本
#--------------------------------------------------------------------
cat > "$STAGE/usr/bin/iqmol" <<'LAUNCHER'
#!/bin/sh
# IQmol 启动器：把随包的 Qt / OpenBabel 路径指好再启动。
# 系统安装布局下由 dpkg 放置，勿手工修改。
IQMOL_ROOT=/usr/lib/iqmol

LD_LIBRARY_PATH="$IQMOL_ROOT/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
QT_PLUGIN_PATH="$IQMOL_ROOT/plugins"
QT_QPA_PLATFORM_PLUGIN_PATH="$IQMOL_ROOT/plugins/platforms"
BABEL_DATADIR="/usr/share/iqmol/openbabel"
export LD_LIBRARY_PATH QT_PLUGIN_PATH QT_QPA_PLATFORM_PLUGIN_PATH BABEL_DATADIR

if [ -d "$IQMOL_ROOT/openbabel" ]; then
  # OpenBabel 运行期插件按版本分子目录（如 3.1.1）
  for _d in "$IQMOL_ROOT"/openbabel/*/; do
    [ -d "$_d" ] && BABEL_LIBDIR="${_d%/}" && break
  done
  [ -n "${BABEL_LIBDIR:-}" ] && export BABEL_LIBDIR
fi

exec "$IQMOL_ROOT/IQmol" "$@"
LAUNCHER
chmod 0755 "$STAGE/usr/bin/iqmol"

#--------------------------------------------------------------------
# 6. 桌面集成
#--------------------------------------------------------------------
cat > "$STAGE/usr/share/applications/iqmol.desktop" <<'DESKTOP'
[Desktop Entry]
Type=Application
Name=IQmol
Name[zh_CN]=IQmol 分子编辑器
GenericName=Molecular Editor
GenericName[zh_CN]=分子编辑器
Comment=Build, visualise and animate molecules
Comment[zh_CN]=分子构建、可视化与动画演示
Exec=/usr/bin/iqmol %F
Icon=iqmol
Terminal=false
StartupNotify=true
StartupWMClass=IQmol
Categories=Education;Science;Chemistry;Physics;
Keywords=molecule;chemistry;quantum;qchem;visualisation;
DESKTOP
chmod 0644 "$STAGE/usr/share/applications/iqmol.desktop"

if [ -f "$SRC_DIR/resources/IQmol.png" ]; then
  install -m 0644 "$SRC_DIR/resources/IQmol.png" \
    "$STAGE/usr/share/icons/hicolor/512x512/apps/iqmol.png"
fi
if [ -f "$SRC_DIR/resources/IQmol.appdata.xml" ]; then
  install -m 0644 "$SRC_DIR/resources/IQmol.appdata.xml" \
    "$STAGE/usr/share/metainfo/IQmol.appdata.xml"
fi

#--------------------------------------------------------------------
# 7. 依赖计算
#    收集 ldd 中出现、但不在本包内的库，反查所属 dpkg 包
#--------------------------------------------------------------------
TMPD="$(mktemp -d)"
trap 'rm -rf "$TMPD"' EXIT

: > "$TMPD/inpkg"
while IFS= read -r f; do
  basename "$f" >> "$TMPD/inpkg"
  soname="$(readelf -d "$f" 2>/dev/null | sed -n 's/.*SONAME.*\[\(.*\)\].*/\1/p' | head -1)"
  [ -n "$soname" ] && echo "$soname" >> "$TMPD/inpkg"
done < <(find "$STAGE/usr/lib/iqmol" \( -type f -o -type l \) -name '*.so*')
sort -u -o "$TMPD/inpkg" "$TMPD/inpkg"

: > "$TMPD/ldd"
# 关键 1：ldd 必须带包内 lib 路径，否则 Qt 各库之间的相互依赖解析不出来。
# 关键 2：必须同时扫描 plugins/（如 platforms/libqxcb.so），Qt 的 X11/输入法
#         依赖（libxkbcommon-x11、libxcb-* 系列）只出现在插件里，不在 libQt5Gui。
while IFS= read -r -d '' t; do
  LD_LIBRARY_PATH="$STAGE/usr/lib/iqmol/lib:$STAGE/usr/lib/iqmol/plugins${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}" \
    ldd "$t" 2>/dev/null | awk '/=> \//{print $1"\t"$3}'
done < <(find "$STAGE/usr/lib/iqmol" \( -name '*.so*' -o -name 'IQmol' \) -print0) \
  | sort -u >> "$TMPD/ldd"

: > "$TMPD/pkgs"
while IFS="$(printf '\t')" read -r soname path; do
  [ -n "$soname" ] || continue
  if grep -qxF "$soname" "$TMPD/inpkg"; then
    continue           # 已随包提供
  fi
  pkg="$(dpkg -S "$path" 2>/dev/null | head -1 | cut -d: -f1)"
  if [ -z "$pkg" ]; then
    # usrmerge 下 /lib/... 与 /usr/lib/... 的 dpkg 记录不一致，用真实路径重试
    real="$(readlink -f "$path" 2>/dev/null)"
    [ -n "$real" ] && pkg="$(dpkg -S "$real" 2>/dev/null | head -1 | cut -d: -f1)"
  fi
  [ -n "$pkg" ] && echo "$pkg" >> "$TMPD/pkgs"
done < "$TMPD/ldd"

{
  sort -u "$TMPD/pkgs"
  # 基础运行依赖始终声明
  printf '%s\n' libc6 libstdc++6 libgl1
} | sed 's/^ *//; s/ *$//' | grep -v '^$' | sort -u > "$TMPD/deps"
DEPS="$(sed 's/$/,/' "$TMPD/deps" | tr -d '\n' | sed 's/,$//; s/,/, /g')"
[ -z "$DEPS" ] && DEPS="libc6, libstdc++6, libgl1"
echo "==> 依赖: $DEPS"

SIZE_KB="$(du -sk "$STAGE" | cut -f1)"

cat > "$STAGE/DEBIAN/control" <<EOF
Package: $PKG
Version: $VER
Section: science
Priority: optional
Architecture: $ARCH
Installed-Size: $SIZE_KB
Depends: $DEPS
Maintainer: IQmol Chinese localisation <noreply@localhost>
Homepage: https://github.com/stone-Glitch/IQmol-for-Chinese
Description: IQmol molecular builder and visualiser (Simplified Chinese)
 IQmol is a free open-source molecular editor and visualisation package.
 It provides a molecular builder, surface generation, molecular orbital
 display, vibrational mode animation and support for Q-Chem input/output.
 .
 This build ships a complete Simplified Chinese interface (zh_CN) together
 with its own Qt and OpenBabel runtime libraries, so it runs without
 installing a Qt development environment.
EOF

cat > "$STAGE/DEBIAN/postinst" <<'POSTINST'
#!/bin/sh
set -e
if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database -q /usr/share/applications || true
fi
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
  gtk-update-icon-cache -q -t -f /usr/share/icons/hicolor || true
fi
exit 0
POSTINST

cat > "$STAGE/DEBIAN/postrm" <<'POSTRM'
#!/bin/sh
set -e
if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database -q /usr/share/applications || true
fi
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
  gtk-update-icon-cache -q -t -f /usr/share/icons/hicolor || true
fi
exit 0
POSTRM
chmod 0755 "$STAGE/DEBIAN/postinst" "$STAGE/DEBIAN/postrm"
chmod 0644 "$STAGE/DEBIAN/control"

# 版权文件（Debian 政策对 doc 目录的要求）
cat > "$STAGE/usr/share/doc/$PKG/copyright" <<'COPY'
Format: https://www.debian.org/doc/packaging-manuals/copyright-format/1.0/
Upstream-Name: IQmol
Source: https://github.com/nutjunkie/IQmol

Files: *
License: GPL-3.0+
 IQmol is free software: you can redistribute it and/or modify it under
 the terms of the GNU General Public License as published by the Free
 Software Foundation, either version 3 of the License, or (at your option)
 any later version.
 .
 On Debian systems the full text of the GPL-3 is available in
 /usr/share/common-licenses/GPL-3.
COPY

#--------------------------------------------------------------------
# 8. 打包
#--------------------------------------------------------------------
DEB="$OUT_DIR/${PKG}_${VER}_${ARCH}.deb"
dpkg-deb --root-owner-group -Zxz --build "$STAGE" "$DEB" >/dev/null || exit 1

echo "==> 已生成: $DEB ($(du -h "$DEB" | cut -f1))"
echo
echo "包内容抽样:"
dpkg-deb -c "$DEB" | awk '{print $6}' | grep -E '^\./(usr/bin/iqmol|usr/lib/iqmol/IQmol|usr/lib/iqmol/translations/|usr/share/iqmol/shaders/|usr/share/applications/|usr/share/icons/)' | head -12 | sed 's/^/    /'
echo
echo "安装:  sudo apt install $DEB"
echo "卸载:  sudo apt remove $PKG"
