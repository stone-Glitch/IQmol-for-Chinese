#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""第二批：源码侧漏翻清零（P2-10 门禁收紧前置）。

把 check_tr_coverage.py 报出的 49 种（52 处）界面可见裸字符串收敛进 tr()/
QCoreApplication::translate()，使 zh_CN.ts 可覆盖这些文本。

两类编辑：
  A. BLOCKS  —— 多行重构（拼接消息改 %1 句式 / 相邻字面量合并），整块精确替换
  B. WRAPS   —— 单行包裹：literal 包成 tr("literal")，或
                QCoreApplication::translate("<ctx>", "literal")

安全约束（沿用 fix_tr_leaks.py 的设计）：
  - 只改列出的 (文件, 行号, 字面量)，绝不全局替换
  - 每处包裹前二次确认该字面量在这一行确实是裸的
  - BLOCKS 以整块原文唯一匹配后才替换
  - 默认 dry-run，--apply 才写盘
  - 同一文件多处的编辑自底向上应用，避免行号漂移

非 QObject 类的上下文（经类继承链核实）：
  - src/Network/Network.C        自由函数 TestNetworkConnection()  -> "IQmol::Network"
  - src/Parser/QChemOutputParser.C  IQmol::Parser::QChemOutput     -> "IQmol::Parser::QChemOutput"
  - src/Qui/OptionDatabase.C       Qui::OptionDatabase（非 QObject）-> "Qui::OptionDatabase"
  - src/Viewer/BuildHandler.C      Handler::Build（非 QObject）    -> "Handler::Build"
  其余各类均为 QObject 派生（Configurator::Base<-QDialog / Layer::Base<-QObject 等），
  用类内 tr()。
"""
import argparse
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ------------------------------------------------------------------ A. 块重构
# (相对路径, 原文块, 新块)
BLOCKS = [
    # BuildHandler: 相邻字面量合并为单行（非 QObject -> translate）
    ('src/Viewer/BuildHandler.C',
     '      QMsgBox::warning(0, "IQmol", "No molecule available.\\n"\n'
     '          "Please select one in the Model View");',
     '      QMsgBox::warning(0, "IQmol", QCoreApplication::translate("Handler::Build",\n'
     '         "No molecule available.\\nPlease select one in the Model View"));'),

    # InputDialog::saveInputFile 附近：msg 拼接改 %1 句式 + 标题 tr
    ('src/Qui/InputDialog.C',
     '      QString msg("Could not write to file \'");\n'
     '      msg += tmp.fileName() + "\'\\nInput file not saved\\n";\n'
     '      QMsgBox::warning(0, "File Not Saved", msg);',
     '      QString msg(tr("Could not write to file \'%1\'\\nInput file not saved\\n")\n'
     '         .arg(tmp.fileName()));\n'
     '      QMsgBox::warning(0, tr("File Not Saved"), msg);'),

    # InputDialog 删除节确认：msg 拼接改 %1 句式 + 标题 tr
    ('src/Qui/InputDialog.C',
     '   QString msg("Are you sure you want to delete the section ");\n'
     '   msg += m_ui.jobList->currentText() + "?";\n'
     '\n'
     '   if (QMsgBox::question(this, "Delete Section?", msg,',
     '   QString msg(tr("Are you sure you want to delete the section %1?")\n'
     '      .arg(m_ui.jobList->currentText()));\n'
     '\n'
     '   if (QMsgBox::question(this, tr("Delete Section?"), msg,'),

    # OptionDatabase::insert 覆盖确认：msg 改 %1 + 标题 translate（非 QObject）
    ('src/Qui/OptionDatabase.C',
     '         QString msg("Option name ");\n'
     '         msg += name;\n'
     '         msg += " already exists in database, overwrite?";\n'
     '         int ret = QMsgBox::question(0, "Option Exists",msg, ',
     '         QString msg(QCoreApplication::translate("Qui::OptionDatabase",\n'
     '            "Option name %1 already exists in database, overwrite?").arg(name));\n'
     '         int ret = QMsgBox::question(0, QCoreApplication::translate("Qui::OptionDatabase",\n'
     '            "Option Exists"), msg, '),

    # OptionDatabase::remove 删除确认：msg 改 %1 + 标题 translate
    ('src/Qui/OptionDatabase.C',
     '      QString msg("Permanently delete the ");\n'
     '      msg += optionName;\n'
     '      msg += " record from the option database?";\n'
     '\n'
     '      int ret = QMsgBox::question(0, "Delete Option?",msg, ',
     '      QString msg(QCoreApplication::translate("Qui::OptionDatabase",\n'
     '         "Permanently delete the %1 record from the option database?").arg(optionName));\n'
     '\n'
     '      int ret = QMsgBox::question(0, QCoreApplication::translate("Qui::OptionDatabase",\n'
     '         "Delete Option?"), msg, '),

    # OptionDatabase::get 重复记录提示：msg 改 %1 + 标题 translate
    ('src/Qui/OptionDatabase.C',
     '            QString msg("More than one record for ");\n'
     '            msg += optionName;\n'
     '            msg += " found in database.";\n'
     '            QMsgBox::information(0, "EGAD!", msg);',
     '            QString msg(QCoreApplication::translate("Qui::OptionDatabase",\n'
     '               "More than one record for %1 found in database.").arg(optionName));\n'
     '            QMsgBox::information(0, QCoreApplication::translate("Qui::OptionDatabase",\n'
     '               "EGAD!"), msg);'),

    # GeometryConstraint::Dialog::deleteConstraint 虚拟原子警告：msg 改 %1 + 标题 tr
    ('src/Qui/GeometryConstraint.C',
     '            msg = "Constraints that reference this dummy atom (";\n'
     '            msg += list[5]->text() + ") and any with a higher id will become invalid";\n'
     '            QMessageBox::warning(this, "Warning", msg);',
     '            msg = tr("Constraints that reference this dummy atom (%1) and any with a "\n'
     '               "higher id will become invalid").arg(list[5]->text());\n'
     '            QMessageBox::warning(this, tr("Warning"), msg);'),
]

# ------------------------------------------------------------------ B. 单行包裹
# (相对路径, 行号, 字面量, 上下文或 None)
#   None            -> tr("字面量")（QObject 派生类内）
#   "Ctx"           -> QCoreApplication::translate("Ctx", "字面量")
WRAPS = [
    # --- ConstraintConfigurator（IQmol::Configurator::VectorConstraint）---
    ('src/Configurator/ConstraintConfigurator.C', 56,  'Position ', None),
    ('src/Configurator/ConstraintConfigurator.C', 142, 'Distance ', None),
    ('src/Configurator/ConstraintConfigurator.C', 164, 'Angle ', None),
    ('src/Configurator/ConstraintConfigurator.C', 186, 'Torsion between atoms ', None),
    ('src/Configurator/ConstraintConfigurator.C', 187, 'Torsion ', None),
    # --- 坐标轴单位标签 ---
    ('src/Configurator/ExcitedStatesConfigurator.C', 112, 'Energy / Hartree', None),
    ('src/Configurator/GeminalOrbitalsConfigurator.C', 133, 'Energy/Hartree', None),
    ('src/Configurator/OrbitalsConfigurator.C', 322, 'Energy/Hartree', None),
    # --- Layer 各类 ---
    ('src/Layer/GeminalOrbitalsLayer.C', 275, 'Problem calculating grid data', None),
    ('src/Layer/GroupLayer.C', 169, 'Coordinate mismatch in Group alignment', None),
    ('src/Layer/GroupLayer.C', 183, 'Alignment failed in Group::align', None),
    ('src/Layer/MoleculeLayer.C', 957, 'Atom selection required', None),
    ('src/Layer/MoleculeLayer.C', 1043, 'Atom selection required', None),
    ('src/Layer/MoleculeLayer.C', 1428, 'Attempt to add unknown primitive type to molecule', None),
    ('src/Layer/MoleculeLayer.C', 1482, 'Atempt to remove unknown primitive type to molecule', None),
    ('src/Layer/MoleculeLayer.C', 1618, 'Unable to nest fragments', None),
    ('src/Layer/OrbitalsLayer.C', 250, 'Still processing previous grid data request', None),
    ('src/Layer/SurfaceLayer.C', 64, 'Configure Surface: ', None),
    ('src/Layer/SurfaceLayer.C', 576, 'Mesh simplification in progress', None),
    ('src/Layer/SystemLayer.C', 183, 'Failed to open PDB file for writing', None),
    # --- Network ---
    ('src/Network/AwsConnection.C', 230, 'Passwords do not match', None),
    ('src/Network/Network.C', 210, 'Invalid username or password', 'IQmol::Network'),
    # --- Parser（非 QObject）---
    ('src/Parser/QChemOutputParser.C', 1155, ' energy', 'IQmol::Parser::QChemOutput'),
    # --- Process ---
    ('src/Process/AwsConfigurationDialog.C', 70, 'Cognito Pool ID should start with the AWS region', None),
    ('src/Process/JobMonitor.C', 308, 'Invalid username or password', None),
    ('src/Process/JobMonitor.C', 313, 'Network timeout', None),
    ('src/Process/JobMonitor.C', 321, 'Error encountered', None),
    ('src/Process/JobMonitor.C', 447, 'Directory name cannot contain spaces', None),
    ('src/Process/JobMonitor.C', 845, 'Copy results from server?', None),
    ('src/Process/JobMonitor.C', 934, 'Output file no longer exists', None),
    ('src/Process/QueueResourcesDialog.C', 42, 'No queues found on server', None),
    ('src/Process/QueueResourcesDialog.C', 71, 'Wall time must be in the format h:mm:ss', None),
    ('src/Process/QueueResourcesDialog.C', 82, 'Validated wall time not in the format h:mm:ss', None),
    ('src/Process/QueueResourcesDialog.C', 95, 'Wall time exceeds queue maximum of ', None),
    ('src/Process/QueueResourcesDialog.C', 98, 'Memory exceeds queue limit of ', None),
    ('src/Process/QueueResourcesDialog.C', 102, 'Scratch exceeds queue limit of ', None),
    ('src/Process/QueueResourcesDialog.C', 106, 'Number of CPUs exceeds queue limit of ', None),
    ('src/Process/ServerConfigurationDialog.C', 69, 'Server name not set', None),
    ('src/Process/ServerConfigurationDialog.C', 88, 'Host address not set', None),
    ('src/Process/ServerConfigurationDialog.C', 98, 'User name must be set', None),
    ('src/Process/ServerConfigurationDialog.C', 526, 'Failed to export server configuration', None),
    # --- Viewer ---
    ('src/Viewer/Snapshot.C', 185, 'Movie making already in progress, please wait', None),
    ('src/Viewer/Snapshot.C', 192, 'ffmpeg executable not found', None),
    ('src/Viewer/Snapshot.C', 199, 'Could not remove existing file ', None),
    ('src/Viewer/ViewerModel.C', 233, 'Invalid string', None),
]

# 需要补 #include <QCoreApplication> 的文件（用了 translate 但未包含）
INCLUDE_FIXES = [
    'src/Network/Network.C',
    'src/Parser/QChemOutputParser.C',
]


def apply_wraps(lines, relpath, wraps, details):
    """自底向上包裹字面量。lines 为文件行列表（就地修改）。"""
    for lineno, literal, ctx in sorted(wraps, key=lambda w: -w[0]):
        idx = lineno - 1
        if idx >= len(lines):
            details.append((relpath, lineno, literal, '行号越界'))
            continue
        line = lines[idx]
        target = '"%s"' % literal
        if target not in line:
            details.append((relpath, lineno, literal, '该行无此字面量'))
            continue
        if re.search(r'tr\(\s*' + re.escape(target), line) or \
           re.search(r'translate\([^)]*,\s*' + re.escape(target), line):
            details.append((relpath, lineno, literal, '已包裹，跳过'))
            continue
        pos = line.find(target)
        prefix = line[:pos]
        if re.search(r'tr\(\s*$', prefix) or re.search(r'translate\([^,]*,\s*$', prefix):
            details.append((relpath, lineno, literal, '已包裹，跳过'))
            continue
        if ctx is None:
            repl = 'tr(%s)' % target
        else:
            repl = 'QCoreApplication::translate("%s", %s)' % (ctx, target)
        lines[idx] = prefix + repl + line[pos + len(target):]
        details.append((relpath, lineno, literal, '已包裹'))


def apply_blocks(text, relpath, blocks, details):
    for old, new in blocks:
        n = text.count(old)
        if n == 0:
            details.append((relpath, 0, old.split('\n')[0][:40], '块未找到'))
            continue
        if n > 1:
            details.append((relpath, 0, old.split('\n')[0][:40], '块不唯一(%d)' % n))
            continue
        text = text.replace(old, new)
        details.append((relpath, 0, old.split('\n')[0][:40], '块已替换'))
    return text


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true', help='实际写盘（默认 dry-run）')
    args = ap.parse_args()
    dry_run = not args.apply

    # 按文件归组
    wraps_by_file = {}
    for relpath, lineno, literal, ctx in WRAPS:
        wraps_by_file.setdefault(relpath, []).append((lineno, literal, ctx))
    blocks_by_file = {}
    for relpath, old, new in BLOCKS:
        blocks_by_file.setdefault(relpath, []).append((old, new))

    details = []
    for relpath in sorted(set(list(wraps_by_file) + list(blocks_by_file))):
        abspath = os.path.join(REPO, relpath)
        if not os.path.isfile(abspath):
            details.append((relpath, 0, '', '文件不存在'))
            continue
        with open(abspath, encoding='utf-8') as f:
            text = f.read()
        text = apply_blocks(text, relpath, blocks_by_file.get(relpath, []), details)
        lines = text.split('\n')
        apply_wraps(lines, relpath, wraps_by_file.get(relpath, []), details)
        if relpath in INCLUDE_FIXES and '#include <QCoreApplication>' not in text:
            # 在最后一个 #include <Q...> 行之后插入
            for i, ln in enumerate(lines):
                if ln.startswith('#include <Q'):
                    last = i
            lines.insert(last + 1, '#include <QCoreApplication>')
            details.append((relpath, 0, '#include <QCoreApplication>', '头文件已补'))
        if not dry_run:
            with open(abspath, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines))

    for relpath, lineno, literal, status in details:
        loc = '%s:%d' % (relpath, lineno) if lineno else relpath
        print('  %-10s %-58s %r' % (status, loc, literal))
    print()
    print('WRAPS 共 %d 处，BLOCKS 共 %d 块，涉及 %d 个文件'
          % (len(WRAPS), len(BLOCKS), len(set(list(wraps_by_file) + list(blocks_by_file)))))
    bad = [d for d in details if d[3] not in ('已包裹', '块已替换', '头文件已补')]
    if bad:
        print('!! 有 %d 处未按预期处理（见上）' % len(bad))
        return 1
    if dry_run:
        print('\n（dry-run，未写盘。确认后加 --apply）')
    return 0


if __name__ == '__main__':
    sys.exit(main())
