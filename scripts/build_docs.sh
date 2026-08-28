#! /bin/bash
# ----------------------------------------------------------------------------
# 构建中文用户手册：IQmolUserGuide.tex -> IQmolUserGuide.pdf
#
# 用法:
#   ./scripts/build_docs.sh            # 编译 doc/IQmolUserGuide.pdf
#   ./scripts/build_docs.sh --clean    # 编译后清理 LaTeX 中间文件
#
# 依赖: texlive-xetex, texlive-lang-chinese (xelatex, bibtex)
# ----------------------------------------------------------------------------
set -e

TOPDIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )/.." &> /dev/null && pwd )
DOCDIR=$TOPDIR/doc
TEXFILE=IQmolUserGuide
CLEAN=0

[ "$1" = "--clean" ] && CLEAN=1

command -v xelatex >/dev/null 2>&1 || {
   echo "错误: 未找到 xelatex，请安装: sudo apt-get install texlive-xetex texlive-lang-chinese"
   exit 1
}

cd "$DOCDIR"

echo "==> xelatex (第 1 遍)"
xelatex -interaction=nonstopmode "$TEXFILE.tex" > /dev/null

echo "==> bibtex"
bibtex "$TEXFILE" > /dev/null 2>&1 || true

echo "==> xelatex (第 2 遍)"
xelatex -interaction=nonstopmode "$TEXFILE.tex" > /dev/null

echo "==> xelatex (第 3 遍, 解析交叉引用)"
xelatex -interaction=nonstopmode "$TEXFILE.tex" | tail -3

PAGES=$(pdfinfo "$TEXFILE.pdf" 2>/dev/null | awk '/^Pages/{print $2}')
echo "==> 生成完成: $DOCDIR/$TEXFILE.pdf (${PAGES:-?} 页)"

if [ "$CLEAN" = "1" ]; then
   echo "==> 清理中间文件"
   rm -f "$TEXFILE".{aux,bbl,blg,log,out,toc}
fi
