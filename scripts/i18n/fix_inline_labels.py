#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""修复第 5 类 i18n 漏包：构造函数初始化列表里的裸字符串标签。

背景
----
形如
    Molecule::Molecule(QObject* parent) : Component(tr("Untitled"), parent),
       m_atomList(this, "Atoms"),
       ...
的初始化列表，其中的 label 是裸字符串。初始化列表阶段 this 尚未构造完成
（tr() 是静态成员，严格来说可调用，但对 Non-QObject 基类会编译失败；
且 lupdate 对初始化列表里的 tr() 提取不稳定），因此这里采用统一方案：

    **保持初始化列表不变，在构造函数体开头追加 setText(tr("...")) 覆盖。**

这样：
  - 源码可编译（体内 this 已完整）
  - lupdate 能提取到 tr("...") 字面量
  - 译文通过 setText 生效到界面上

用法
----
    python3 scripts/i18n/fix_inline_labels.py            # 预演
    python3 scripts/i18n/fix_inline_labels.py --apply    # 写入
"""

import argparse
import os
import re
import sys

TOPDIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# (相对路径, 构造函数签名正则, [(成员/变量, 英文标签), ...])
# 成员名为 None 表示直接是基类构造，需用 setText 覆盖 this 自身
TARGETS = [
    ('src/Layer/MoleculeLayer.C', r'Molecule::Molecule\(QObject\* parent\)\s*:',
     [('m_atomList', 'Atoms'), ('m_bondList', 'Bonds'), ('m_chargesList', 'Charges'),
      ('m_fileList', 'Files'), ('m_constraintList', 'Constraints'),
      ('m_isotopesList', 'Isotopes'), ('m_scanList', 'Scan Coordinates'),
      ('m_groupList', 'Groups')]),
    # 注：Bond::Bond 的 label "Bond" 只是内部标识，其 setText 由 setIndex()
    # 动态重设为 "序号 元素-元素"，不需翻译；Charge::Charge 同理（label 不显示在树上）。
    ('src/Layer/CubeDataLayer.C', r'CubeData::CubeData\(Data::CubeData const& cube\)\s*:',
     [(None, 'Cube Data')]),
    ('src/Layer/DipoleLayer.C', r'Dipole::Dipole\(qglviewer::Vec const& dipoleMoment\)\s*:',
     [(None, 'Dipole')]),
    ('src/Layer/EfpFragmentListLayer.C', r'EfpFragmentList::EfpFragmentList\(Layer::Base\* parent\)\s*:',
     [(None, 'EFP Fragments')]),
    ('src/Layer/ExcitedStatesLayer.C', r'ExcitedStates::ExcitedStates\(Data::ExcitedStates const& states\)\s*:',
     [(None, 'Excited States')]),
    ('src/Layer/FrequenciesLayer.C', r'Frequencies::Frequencies\(Data::Frequencies const& frequencies\)\s*:',
     [(None, 'Frequencies')]),
    ('src/Layer/GeminalOrbitalsLayer.C', r'GeminalOrbitals::GeminalOrbitals\(Data::GeminalOrbitals& molecularOrbitals\)\s*:',
     [(None, 'Geminal Orbitals')]),
    ('src/Layer/NmrLayer.C', r'Nmr::Nmr\(Data::Nmr& data\)\s*:',
     [(None, 'NMR')]),
    ('src/Layer/OctreeLayer.C', r'Octree::Octree\(AtomList const& atoms\)\s*:',
     [(None, 'Octree Box')]),
    ('src/Layer/SymmetryLayer.C', r'Symmetry::Symmetry\(Data::PointGroup const& pointGroup\)\s*:',
     [(None, 'Symmetry')]),
    ('src/Layer/VibronicLayer.C', r'Vibronic::Vibronic\(Data::Vibronic const& vibronic\)\s*:',
     [(None, 'Vibronic')]),
    ('src/Layer/MacroMoleculeLayer.C', r'',
     [('__special_macro__', 'Residues')]),
]


def handle_macro(path):
    """MacroMoleculeLayer.C 里 Residues 是在函数体里 new Container(this, "Residues")，
    不在初始化列表，可直接包 tr()。"""
    src = open(path, encoding='utf-8').read()
    old = 'new Container(this, "Residues")'
    new = 'new Container(this, tr("Residues"))'
    if old not in src:
        return None
    if 'new Container(this, tr("Residues"))' in src:
        return None
    if not args_apply:
        print('  %-46s :%s  Container label Residues' % (
            os.path.relpath(path, TOPDIR),
            src[:src.index(old)].count('\n') + 1))
        return 1
    open(path, 'w', encoding='utf-8').write(src.replace(old, new))
    print('  %-46s 改为 tr("Residues")' % os.path.relpath(path, TOPDIR))
    return 1


args_apply = False


def main():
    global args_apply
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true')
    args = ap.parse_args()
    args_apply = args.apply

    total = 0
    for rel, ctor_re, pairs in TARGETS:
        path = os.path.join(TOPDIR, rel)

        if pairs and pairs[0][0] == '__special_macro__':
            r = handle_macro(path)
            if r:
                total += r
            continue

        src = open(path, encoding='utf-8').read()
        if '// [i18n]' in src and 'setText(tr("Atoms"))' in src:
            continue  # 已处理

        m = re.search(ctor_re, src)
        if not m:
            print('  !! 未定位构造函数: %s  (%s)' % (rel, ctor_re))
            continue

        # 找构造函数的第一个 '{'
        brace = src.index('{', m.end())
        body_indent = '   '

        lines = []
        lines.append('')
        lines.append(body_indent + '// [i18n] 初始化列表中的标签为裸字符串，此处覆盖为译文，')
        lines.append(body_indent + '// 使 lupdate 可提取、界面显示中文。')
        for member, label in pairs:
            if member is None:
                lines.append(body_indent + 'setText(tr("%s"));' % label)
            else:
                lines.append(body_indent + '%s.setText(tr("%s"));' % (member, label))
        insertion = '\n'.join(lines) + '\n'

        new_src = src[:brace + 1] + insertion + src[brace + 1:]
        print('  %-46s 插入 %d 条 setText(tr())' % (rel, len(pairs)))
        total += len(pairs)

        if args.apply:
            open(path, 'w', encoding='utf-8').write(new_src)

    print()
    print('合计 %d 处' % total)
    if not args.apply:
        print('\n这是预演。加 --apply 才会写入。')


if __name__ == '__main__':
    main()
