#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""对已核实的"漏包"位置补 tr() 包裹。

设计：
  - 只改指定 (文件, 行号, 字面量) 三元组，绝不全局替换
  - 每处包裹前二次确认该字面量在这一行确实是裸的
  - 默认 dry-run，--apply 才写盘
"""
import argparse, os, re, sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# (相对路径, 行号, 字面量) —— 由人工核实的安全 UI 显示项
FIXES = [
    # --- ExcitedStatesConfigurator: 坐标轴标签 ---
    ('src/Configurator/ExcitedStatesConfigurator.C', 116, 'Alpha'),
    ('src/Configurator/ExcitedStatesConfigurator.C', 337, 'Strength'),
    ('src/Configurator/ExcitedStatesConfigurator.C', 345, 'Rel. Strength'),
    # --- FrequenciesConfigurator: 坐标轴标签 ---
    ('src/Configurator/FrequenciesConfigurator.C', 94, 'Intensity'),
    ('src/Configurator/FrequenciesConfigurator.C', 225, 'Intensity'),
    ('src/Configurator/FrequenciesConfigurator.C', 233, 'Rel. Intensity'),
    # --- GeometryListConfigurator ---
    ('src/Configurator/GeometryListConfigurator.C', 72, 'Energy'),
    ('src/Configurator/GeometryListConfigurator.C', 135, 'Geometry'),
    # --- NmrConfigurator / OrbitalsConfigurator / VibronicConfigurator ---
    ('src/Configurator/NmrConfigurator.C', 83, 'Shieldings'),
    ('src/Configurator/OrbitalsConfigurator.C', 68, 'Orbital'),
    ('src/Configurator/OrbitalsConfigurator.C', 174, 'Alpha'),
    ('src/Configurator/VibronicConfigurator.C', 88, 'Intensity'),
    ('src/Configurator/VibronicConfigurator.C', 221, 'Electronic Transition'),
    # --- Data ---
    ('src/Data/SurfaceType.C', 95, 'Alpha'),
    ('src/Data/SurfaceType.C', 98, 'Spin Density'),
    ('src/Data/SurfaceType.C', 116, 'Orbital'),
    # --- Layer ---
    ('src/Layer/AtomLayer.C', 99, 'Atom'),
    ('src/Layer/MoleculeLayer.C', 233, 'Info'),
    ('src/Layer/SystemLayer.C', 123, 'Info'),
    # --- Parser（OpenBabel 轴标签等） ---
    ('src/Parser/OpenBabelParser.C', 355, 'Energy'),
    # --- GeometryConstraint 类型名 ---
    ('src/Qui/GeometryConstraint.C', 30, 'Stretch'),
    ('src/Qui/GeometryConstraint.C', 31, 'Bend'),
    ('src/Qui/GeometryConstraint.C', 33, 'Dihedral'),
    ('src/Qui/GeometryConstraint.C', 35, 'Perpendicular'),
    # --- InputDialog 菜单栏 ---
    ('src/Qui/InputDialog.C', 373, 'Save As'),
    ('src/Qui/InputDialog.C', 379, 'Close'),
    ('src/Qui/InputDialog.C', 389, 'Copy'),
    ('src/Qui/InputDialog.C', 396, 'Paste'),
    ('src/Qui/InputDialog.C', 402, 'Cut'),
    ('src/Qui/InputDialog.C', 426, 'Submit'),
    # --- InputDialogLogic: 状态标签 ---
    ('src/Qui/InputDialogLogic.C', 776, 'Singlets'),
    ('src/Qui/InputDialogLogic.C', 777, 'Triplets'),
    ('src/Qui/InputDialogLogic.C', 814, 'Singlets'),
    ('src/Qui/InputDialogLogic.C', 815, 'Triplets'),
    ('src/Qui/InputDialogLogic.C', 869, 'Alpha'),
    ('src/Qui/InputDialogLogic.C', 886, 'Alpha'),
    ('src/Qui/InputDialogLogic.C', 922, 'Singlets'),
    ('src/Qui/InputDialogLogic.C', 922, 'Triplets'),
    # --- ColorDialog: 调色板名 ---
    ('src/Util/ColorDialog.C', 160, 'Custom'),
    ('src/Util/ColorDialog.C', 161, 'Default'),
    ('src/Util/ColorDialog.C', 162, 'Spectrum'),
    # --- UndoCommands: 撤销栈文本 ---
    ('src/Viewer/UndoCommands.C', 386, 'New molecule'),
    ('src/Viewer/UndoCommands.C', 388, 'New system'),
    ('src/Viewer/UndoCommands.C', 436, 'Remove molecule'),
    ('src/Viewer/UndoCommands.C', 438, 'Remove system'),
    # --- ViewerModelView: 右键菜单（已手工修） ---
    # ('src/Viewer/ViewerModelView.C', 102, 'New Molecule From Selection'),
]


def apply_fixes(dry_run=True):
    changed = []
    details = []
    for relpath, lineno, literal in FIXES:
        abspath = os.path.join(REPO, relpath)
        if not os.path.isfile(abspath):
            details.append((relpath, lineno, literal, '文件不存在'))
            continue
        with open(abspath, encoding='utf-8') as f:
            text = f.read()
        lines = text.split('\n')
        if lineno - 1 >= len(lines):
            details.append((relpath, lineno, literal, '行号越界'))
            continue
        line = lines[lineno - 1]
        target = f'"{literal}"'
        if target not in line:
            details.append((relpath, lineno, literal, '该行无此字面量'))
            continue
        # 已经是 tr("...") 或 translate("...", "...")
        if re.search(r'tr\(\s*' + re.escape(target), line) or \
           re.search(r'translate\([^)]*,\s*' + re.escape(target), line):
            details.append((relpath, lineno, literal, '已包裹，跳过'))
            continue
        # 定位第一个裸出现
        idx = line.find(target)
        # 检查前面不是 tr( 或 translate(..., 
        prefix = line[:idx]
        if re.search(r'tr\(\s*$', prefix):
            details.append((relpath, lineno, literal, '已包裹，跳过'))
            continue
        newline = prefix + 'tr(' + target + ')' + line[idx + len(target):]
        lines[lineno - 1] = newline
        if not dry_run:
            with open(abspath, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines))
        changed.append(relpath)
        details.append((relpath, lineno, literal, '已包裹'))
    return changed, details


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true', help='实际写盘（默认 dry-run）')
    args = ap.parse_args()

    changed, details = apply_fixes(dry_run=not args.apply)
    for relpath, lineno, literal, status in details:
        print(f'  {status:12} {relpath}:{lineno}  "{literal}"')
    print()
    print(f'改动文件: {len(set(changed))}  改动处数: {len(changed)}')
    if not args.apply:
        print('\n（dry-run，未写盘。确认后加 --apply）')


if __name__ == '__main__':
    sys.exit(main())
