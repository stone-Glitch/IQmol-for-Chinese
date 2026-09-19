#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""为 QAction 漏包修复补齐 zh_CN.ts 译文。

背景
----
fix_tr_leaks.py / fix_action_leaks.py 给源码补了 tr()，lupdate 随之在 ts 里
产生了一批**新 context**（每个 Layer 子类一个，如 IQmol::Layer::Molecule）。
这些 context 在现有 ts 里不存在，需要把译文补进去，否则界面仍是英文。

策略
----
1. 跑 lupdate 得到权威 context 表（含新条目）。
2. 对照现有 ts，列出「lupdate 有、ts 无」的条目。
3. 跳过 HTML 富文本（lupdate 会从 .ui 的 QLabel 抓整段 HTML，不该翻译为普通串）。
4. 用内置词典补齐译文；词典未覆盖的报出来人工处理。

用法
----
    python3 scripts/i18n/fill_action_translations.py            # 预演
    python3 scripts/i18n/fill_action_translations.py --apply    # 写入
"""

import argparse
import os
import re
import subprocess
import sys
import tempfile

TOPDIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TS = os.path.join(TOPDIR, 'translations', 'zh_CN.ts')

CONTEXT_RE = re.compile(r'<context>\s*<name>([^<]+)</name>(.*?)</context>', re.S)
MESSAGE_RE = re.compile(r'<source>(.*?)</source>\s*<translation([^>]*)>(.*?)</translation>', re.S)

# lupdate 从 .ui 里抓到的整段 HTML（Designer 富文本），不该按普通串翻译
SKIP_SOURCE_RE = re.compile(r'^\s*(<!DOCTYPE|<html|<p style|<span style)', re.I)

# QAction / 界面文本词典。键为英文原文，值为中文译文。
DICT = {
    # --- 通用 ---
    'Configure': '配置',
    'Select All': '全选',
    'Reperceive Bonds': '重新识别键',
    'Add Hydrogens': '添加氢原子',
    'Duplicate Geometry': '复制几何结构',
    'Atomic Charges': '原子电荷',
    'Remove': '移除',
    'Save As': '另存为',
    'Edit Color': '编辑颜色',
    'Delete': '删除',
    'Surface Animator': '表面动画器',
    'Copy Geometry': '复制几何结构',
    'Show Grid Info': '显示网格信息',
    'Edit Bounding Box': '编辑包围盒',
    'Show Vertex Normals': '显示顶点法线',
    'Show Face Normals': '显示面法线',
    'Decimate': '抽稀',
    'Print Mesh Info': '打印网格信息',
    'Box System': '加框系统',
    'Export PDB': '导出 PDB',
    'Remove System': '移除系统',
    # --- 电荷方法（专有名词，保留英文并加注） ---
    'Gasteiger': 'Gasteiger',
    'Mulliken': 'Mulliken',
    'Multipole Derived': '多极展开',
    'CHELPG': 'CHELPG',
    'Hirshfeld': 'Hirshfeld',
    'Lowdin': 'Löwdin',
    'Natural': 'Natural',
    'Merz-Kollman ESP': 'Merz-Kollman ESP',
    'Merz-Kollman RESP': 'Merz-Kollman RESP',
    # --- 首选项 ---
    'English': 'English',
    '中文': '中文',
    '界面语言:': '界面语言：',
    '跟随系统': '跟随系统',
    # --- 关于对话框 ---
    'IQmol is a simple molecular builder and visualizer':
        'IQmol 是一款简洁的分子构建与可视化软件',
    # --- 树节点标签（初始化列表漏包，见 fix_inline_labels.py）---
    'Atoms': '原子',
    'Bonds': '键',
    'Charges': '电荷',
    'Files': '文件',
    'Constraints': '约束',
    'Isotopes': '同位素',
    'Scan Coordinates': '扫描坐标',
    'Groups': '基团',
    'Residues': '残基',
    'Bond': '键',
    'Charge': '电荷',
    'Cube Data': 'Cube 数据',
    'Dipole': '偶极',
    'EFP Fragments': 'EFP 片段',
    'Excited States': '激发态',
    'Frequencies': '频率',
    'Geminal Orbitals': '成对轨道',
    'NMR': '核磁共振（NMR）',
    'Octree Box': '八叉树盒',
    'Symmetry': '对称性',
    'Vibronic': '振动电子',
    'Surfaces': '表面',
    'Untitled': '未命名',
    # --- 表面类型下拉（MolecularSurfacesConfigurator / GeminalOrbitalsConfigurator）---
    'van der Waals': '范德华',
    'Promolecule': '原分子',
    'SID': 'SID',
    'Geminal': '成对',
    'Geminal Correlation': '成对相关',
}


def run_lupdate():
    """跑 lupdate 得到权威 context 表。"""
    tmp = tempfile.NamedTemporaryFile(suffix='.ts', delete=False)
    tmp.write(b'<?xml version="1.0" encoding="utf-8"?>\n'
              b'<!DOCTYPE TS>\n<TS version="2.1" language="zh_CN">\n</TS>\n')
    tmp.close()
    subprocess.run(['lupdate', '-extensions', 'C,ui',
                    os.path.join(TOPDIR, 'src') + '/', '-ts', tmp.name],
                   check=True, capture_output=True)
    r = parse_ts(tmp.name)
    os.unlink(tmp.name)
    return r


def parse_ts(path):
    t = open(path, encoding='utf-8').read()
    d = {}
    for m in CONTEXT_RE.finditer(t):
        ctx = m.group(1)
        for mm in MESSAGE_RE.finditer(m.group(2)):
            d.setdefault(ctx, {})[mm.group(1)] = (mm.group(3), mm.group(2))
    return d


def esc(s):
    return (s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;'))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true')
    args = ap.parse_args()

    authoritative = run_lupdate()
    current = parse_ts(TS)

    text = open(TS, encoding='utf-8').read()

    # 收集需要新增的 (context, source, translation)
    todo = []
    unknown = []
    for ctx, items in authoritative.items():
        for src, (tr, attrs) in items.items():
            if SKIP_SOURCE_RE.match(src):
                continue
            c = current.get(ctx, {}).get(src)
            if c is not None and c[0].strip() and 'unfinished' not in c[1]:
                continue  # 已有译文
            if src in DICT:
                todo.append((ctx, src, DICT[src]))
            else:
                unknown.append((ctx, src))

    print('=== 待补齐译文 %d 条 ===' % len(todo))
    last_ctx = None
    for ctx, src, tr in sorted(todo):
        if ctx != last_ctx:
            print('  [%s]' % ctx)
            last_ctx = ctx
        print('      %-28r -> %r' % (src, tr))

    if unknown:
        print()
        print('=== 词典未覆盖 %d 条（原文将保留英文，需人工处理） ===' % len(unknown))
        for ctx, src in sorted(unknown):
            print('  %-42s %r' % (ctx[:41], src[:60]))

    if not args.apply:
        print('\n这是预演。加 --apply 才会写入。')
        return 0

    # 写入：优先插到已有 context；context 不存在则在文件尾新建
    added_ctx = 0
    added_msg = 0
    for ctx, src, tr in todo:
        block_re = re.compile(
            r'(<context>\s*<name>' + re.escape(ctx) + r'</name>)(.*?)(</context>)', re.S)
        m = block_re.search(text)
        entry = ('        <message>\n'
                 '            <source>%s</source>\n'
                 '            <translation>%s</translation>\n'
                 '        </message>\n' % (esc(src), esc(tr)))
        if m:
            # 替换已有条目（unfinished）或追加
            body = m.group(2)
            msg_re = re.compile(
                r'(\s*<message>\s*<source>' + re.escape(esc(src)) +
                r'</source>.*?</message>)', re.S)
            if msg_re.search(body):
                new_body = msg_re.sub(
                    '\n        <message>\n'
                    '            <source>%s</source>\n'
                    '            <translation>%s</translation>\n'
                    '        </message>' % (esc(src), esc(tr)),
                    body)
            else:
                new_body = body + entry
            text = text[:m.start(2)] + new_body + text[m.end(2):]
        else:
            new_ctx = ('    <context>\n'
                       '        <name>%s</name>\n%s'
                       '    </context>\n' % (ctx, entry))
            k = text.rfind('</TS>')
            text = text[:k] + new_ctx + text[k:]
            added_ctx += 1
        added_msg += 1

    open(TS, 'w', encoding='utf-8').write(text)
    print('\n已写入：%d 条译文，新建 context %d 个' % (added_msg, added_ctx))
    return 0


if __name__ == '__main__':
    sys.exit(main())
