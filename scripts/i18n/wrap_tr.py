#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IQmol3 MainWindow.C 汉化改造脚本（精确、行号驱动、注释安全）
将可见 UI 字符串用 tr() 包裹，跳过品牌名、力场名、注释块与内部标识符。
"""
import re
import sys

FILE = "/workspace/IQmol3/src/Main/MainWindow.C"

# 要包裹的行号 -> 该行的内容（作为校验，防止误改）
# 这些是 `name = "XXX";` 形式的菜单项标签（顶层菜单 6 个 + 菜单项）
NAME_LINES = {
    368: '"About"',
    372: '"New Molecule"',
    377: '"New Viewer"',
    381: '"Open"',
    386: '"Open Dir"',
    391: '"Open Recent"',
    397: '"Close Viewer"',
    402: '"Save"',
    407: '"Save As"',
    414: '"Save Picture"',
    425: '"Record Animation"',
    433: '"Show Message Log"',
    438: '"Quit"',
    447: '"Undo"',
    453: '"Redo"',
    461: '"Cut"',
    466: '"Copy"',
    471: '"Paste"',
    478: '"Select All"',
    483: '"Select None"',
    488: '"Invert Selection"',
    495: '"Reindex Atoms"',
    502: '"Preferences"',
    510: '"Full Screen"',
    518: '"Reset View"',
    523: '"Show Axes"',
    534: '"Camera"',
    538: '"Appearance"',
    544: '"Atom Labels"',
    547: '"Element"',
    555: '"Index"',
    563: '"Mass"',
    571: '"NMR"',
    579: '"Partial Charge"',
    587: '"Spin Densities"',
    595: '"Atom Label"',
    607: '"Insert Molecule by ID"',
    614: '"Fill Valencies With Hydrogens"',
    619: '"Reperceive Bonds"',
    623: '"Set Isotopes"',
    629: '"Set Geometric Constraint"',
    634: '"Freeze Selected Atoms"',
    638: '"Minimize Structure"',
    643: '"Select Force Field"',
    690: '"Translate To Center"',
    695: '"Symmetrize Molecule"',
    700: '"Set Symmetry Tolerance"',
    704: '"Auto-detect Symmetry"',
    715: '"Q-Chem Setup"',
    721: '"Job Monitor"',
    726: '"Edit Servers"',
    # Gromacs/Amber 条件编译块内的菜单项（同样翻译）
    736: '"Gromacs Setup"',
    741: '"Edit Gromacs Config"',
    745: '"Edit Gomacs Server"',
    757: '"Edit Amber Config"',
    761: '"Amber System Builder"',
    773: '"Show Help"',
}

# 顶层菜单标题：menu = menuBar()->addMenu("X");
MENU_LINES = {
    366: '"File"',
    445: '"Edit"',
    508: '"Display"',
    605: '"Build"',
    713: '"Calculation"',
    771: '"Help"',
}

# 其他需要包裹 tr() 的行（精确整行替换）
OTHER_REPLACEMENTS = {
    122: '   m_statusWidget.showMessage(tr("Welcome to IQmol"));',
    805: '      QMsgBox::information(this, "IQmol", tr("Network access available"));',
    835: '      m_statusWidget.showMessage(tr("Loading"), true);',
    846: '      m_statusWidget.showMessage(tr("Loading"), true);',
    857: '      m_statusWidget.showMessage(tr("Loading"), true);',
    879: '      QString msg(tr("Only one molecule can be visible when reindexing atoms."));',
    955: '      action = m_recentFilesMenu->addAction(tr("Clear List"));',
}

def wrap_string(s):
    """把 "X" 变成 tr("X")"""
    return "tr(" + s + ")"

def process():
    with open(FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()

    changes = 0
    # 1) 顶层菜单 addMenu
    for ln, expected in MENU_LINES.items():
        idx = ln - 1
        line = lines[idx]
        # 校验行内容
        assert expected in line, f"行 {ln} 内容不匹配: {line.strip()}"
        # 替换 addMenu("X") -> addMenu(tr("X"))
        new = re.sub(r'addMenu\("([^"]+)"\)', r'addMenu(tr("\1"))', line)
        lines[idx] = new
        changes += 1

    # 2) name = "X"; 菜单项
    for ln, expected in NAME_LINES.items():
        idx = ln - 1
        line = lines[idx]
        assert expected in line, f"行 {ln} 内容不匹配: {line.strip()}"
        # 替换 name = "X" -> name = tr("X")
        new = re.sub(r'name = "([^"]+)"', r'name = tr("\1")', line)
        lines[idx] = new
        changes += 1

    # 3) 其他整行替换
    for ln, new_line in OTHER_REPLACEMENTS.items():
        idx = ln - 1
        lines[idx] = new_line + "\n"
        changes += 1

    with open(FILE, "w", encoding="utf-8") as f:
        f.writelines(lines)

    print(f"改造完成：共修改 {changes} 处。")

if __name__ == "__main__":
    process()
