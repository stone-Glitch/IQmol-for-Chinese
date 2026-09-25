#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
qchem_db_translate.py —— Q-Chem 关键词数据库（share/qchem_option.db）提示文本汉化工具

背景（r397Su）
-------------
Q-Chem 输入文件编辑器的悬停提示（tooltip，如 SCF_ALGORITHM 的说明文字）
来自 SQLite 数据库 share/qchem_option.db 的 options.Description 字段，
**不是源码里的 tr() 字符串**，因此 lupdate/lrelease 流程完全覆盖不到。
本工具负责这条"第三条翻译通道"的工程链路：

    导出（export）→ 翻译 → 回写（import）→ 校验（verify）

关键难点：Description 存的是 **Qt RichText HTML**
------------------------------------------------
每条都是一整份 HTML 文档（DOCTYPE + <style> + <p style=...><span style=...>…），
直接让翻译模型整条改写极易破坏标签。因此本工具：

    · export：只抽出 `<body>` 之后的**可见文本节点**（剥离 DOCTYPE/style/标签属性），
                逐段编号后导出 —— 翻译者只看到纯文本；
    · import：按编号把译文**原位回填**到 HTML 文本节点，标签与样式一字不动；
    · 关键词名（Name）不译 —— 它是输入文件语法；
    · `{KEY}` 形式的交叉引用占位符必须守恒，否则拒绝写入（宁可不译，不断链）。

用法
----
    # 导出全部待译文本段
    python3 scripts/i18n/qchem_db_translate.py export --out /tmp/qchem_desc.json
    # 分批导出（第 1 批 / 共 6 批）
    python3 scripts/i18n/qchem_db_translate.py export --batch 1/6 --out /tmp/b1.json
    # 回写（自动备份原库）  输入 JSON 中每段补上 "zh" 字段即可
    python3 scripts/i18n/qchem_db_translate.py import --in /tmp/b1.json
    # 校验：条数 / 空描述 / HTML 结构完整性
    python3 scripts/i18n/qchem_db_translate.py verify
    # 生成 Markdown 对照表（给审校看）
    python3 scripts/i18n/qchem_db_translate.py table --out docs/汉化对照表/qchem关键词说明.md
"""
import argparse
import json
import os
import re
import shutil
import sqlite3
import sys
from datetime import datetime

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB = os.path.join(REPO, 'share/qchem_option.db')
TABLE = 'options'
COL = 'Description'

# 交叉引用占位符：{SCF_ALGORITHM} 这类，花括号内只允许关键词字符
PLACEHOLDER_RE = re.compile(r'\{[A-Za-z_][A-Za-z0-9_]{1,40}\}')
# HTML 文本节点（标签之间的可见文本）
TEXT_NODE_RE = re.compile(r'>([^<>]+)<')
BODY_RE = re.compile(r'(<body[^>]*>)', re.I)


# ------------------------------------------------------------------ HTML 拆分/回填
def split_html(html):
    """拆成 (前缀, body 部分, 文本段列表)

    文本段: {'id': 序号, 'text': 原文（已 strip）, 'start'/'end': 在 body 中的区间}
    只处理 <body> 之后的可见文本，DOCTYPE / <style> / 标签属性一律不动。
    """
    m = BODY_RE.search(html)
    if not m:
        return '', html, [{'id': 0, 'text': html, 'start': 0, 'end': len(html)}]
    prefix, body = html[:m.end()], html[m.end():]
    segs, i = [], 0
    for tm in TEXT_NODE_RE.finditer(body):
        raw = tm.group(1)
        if not raw.strip():
            continue
        lead = len(raw) - len(raw.lstrip())
        trail = len(raw) - len(raw.rstrip())
        segs.append({'id': i, 'text': raw.strip(),
                     'start': tm.start(1) + lead, 'end': tm.end(1) - trail})
        i += 1
    return prefix, body, segs


def rebuild_html(prefix, body, segs, zh_map):
    """按 id 把译文回填到 body 的文本节点（倒序替换，避免 offset 失效）"""
    out = body
    for seg in sorted(segs, key=lambda s: s['start'], reverse=True):
        zh = zh_map.get(seg['id'])
        if zh is None:
            continue
        out = out[:seg['start']] + zh + out[seg['end']:]
    return prefix + out


# ------------------------------------------------------------------ 数据库
def open_db(path=DB, write=False):
    if not os.path.isfile(path):
        sys.exit(f'ERROR: 数据库不存在: {path}')
    if write:
        bak = f'{path}.bak-{datetime.now():%Y%m%d-%H%M%S}'
        shutil.copy2(path, bak)
        print(f'  已备份原库 -> {os.path.basename(bak)}')
    con = sqlite3.connect(path)
    con.text_factory = str
    return con


def load_rows(con):
    return [(r[0], r[1] or '') for r in
            con.execute(f'SELECT Name, {COL} FROM {TABLE} ORDER BY Name')]


def slice_batch(rows, batch):
    if not batch:
        return rows
    m = re.match(r'^(\d+)\s*/\s*(\d+)$', batch)
    if not m:
        sys.exit(f'ERROR: --batch 格式应为 i/n，收到 {batch}')
    i, n = int(m.group(1)), int(m.group(2))
    if not (1 <= i <= n):
        sys.exit(f'ERROR: --batch 越界: {batch}')
    size = (len(rows) + n - 1) // n
    return rows[(i - 1) * size: i * size]


# ------------------------------------------------------------------ 子命令
def cmd_export(args):
    con = open_db()
    rows = slice_batch(load_rows(con), args.batch)
    items, total_seg = [], 0
    for name, html in rows:
        _p, _b, segs = split_html(html)
        items.append({'name': name,
                      'segments': [{'id': s['id'], 'en': s['text']} for s in segs]})
        total_seg += len(segs)
    payload = {'source': os.path.relpath(DB, REPO), 'batch': args.batch or 'all',
               'count': len(items), 'segments': total_seg, 'items': items}
    if args.out:
        with open(args.out, 'w', encoding='utf-8') as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        print(f'已导出 {len(items)} 条 / {total_seg} 个文本段 -> {args.out}')
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    con.close()
    return 0


def cmd_import(args):
    with open(args.input, encoding='utf-8') as f:
        obj = json.load(f)
    items = obj['items'] if isinstance(obj, dict) else obj
    if not items:
        sys.exit('ERROR: 译文文件为空')

    con = open_db(write=not args.no_backup)
    rows = dict(load_rows(con))
    applied = skipped_ph = skipped_missing = 0
    bad = []
    for it in items:
        name = it.get('name')
        if name not in rows:
            skipped_missing += 1
            continue
        zh_map, broken = {}, False
        for seg in it.get('segments', []):
            zh = (seg.get('zh') or '').strip()
            if not zh:
                continue
            en = seg.get('en', '')
            if sorted(PLACEHOLDER_RE.findall(en)) != sorted(PLACEHOLDER_RE.findall(zh)):
                broken = True
                break
            zh_map[seg['id']] = zh
        if broken:
            bad.append(name)
            skipped_ph += 1
            continue
        if not zh_map:
            continue
        prefix, body, segs = split_html(rows[name])
        new_html = rebuild_html(prefix, body, segs, zh_map)
        con.execute(f'UPDATE {TABLE} SET {COL} = ? WHERE Name = ?', (new_html, name))
        applied += 1
    con.commit()
    con.close()
    print(f'已回写 {applied} 条 -> {os.path.relpath(DB, REPO)}')
    if skipped_missing:
        print(f'  跳过（库中无此关键词）: {skipped_missing}')
    if skipped_ph:
        print(f'  跳过（占位符不守恒，需人工修）: {skipped_ph} -> {bad[:5]}')
    return 0 if not skipped_ph else 1


def cmd_verify(args):
    con = open_db()
    rows = load_rows(con)
    total = len(rows)
    zh = [n for n, d in rows if re.search(r'[一-鿿]', d)]
    broken_html, empty_text = [], []
    for n, d in rows:
        if not d.strip():
            empty_text.append(n)
        elif '<body' in d and '</html>' not in d:
            broken_html.append(n)
    con.close()

    print('=' * 66)
    print(' qchem_option.db 汉化校验')
    print('=' * 66)
    print(f'  关键词总数      : {total}')
    print(f'  已汉化（含汉字）: {len(zh)}  ({len(zh)/total:.1%})')
    print(f'  空描述          : {len(empty_text)}')
    print(f'  HTML 结构异常   : {len(broken_html)}')
    for b in broken_html[:5]:
        print(f'      - {b}')
    print('=' * 66)
    ok = not empty_text and not broken_html
    print('  ✅ 结构与占位符正常' if ok else '  ❌ 存在问题，见上')
    return 0 if ok else 1


def cmd_table(args):
    con = open_db()
    rows = load_rows(con)

    # 若给出英文原库，则生成「原文 / 译文」两列对照；否则只列当前（已汉化）文本
    orig = {}
    if args.orig:
        if not os.path.isfile(args.orig):
            sys.exit(f'ERROR: 原库不存在: {args.orig}')
        con2 = sqlite3.connect(args.orig)
        con2.text_factory = str
        for n, d in con2.execute(f'SELECT Name, {COL} FROM {TABLE}'):
            _p, _b, segs = split_html(d or '')
            orig[n] = ' / '.join(s['text'] for s in segs)
        con2.close()

    head = ['# Q-Chem 关键词说明（tooltip）汉化对照表', '',
            '> 来源：`share/qchem_option.db` → `options.Description`（Qt RichText HTML）',
            '> 规则：关键词名**不译**（输入文件语法）；只译 `<body>` 内的可见文本；'
            '`{KEY}` 交叉引用占位符原样保留。', '',
            f'共 {len(rows)} 条；表中多个文本段以「 / 」分隔（对应同一说明里的多段文字）。',
            '']
    if orig:
        head += ['| 关键词 | 原文 | 译文 |', '|---|---|---|']
    else:
        head += ['| 关键词 | 当前文本 |', '|---|--|']

    lines = list(head)
    for n, d in rows:
        _p, _b, segs = split_html(d)
        txt = ' / '.join(s['text'] for s in segs).replace('|', '\\|')
        if orig:
            en = orig.get(n, '').replace('|', '\\|')
            lines.append(f'| `{n}` | {en[:300]} | {txt[:300]} |')
        else:
            lines.append(f'| `{n}` | {txt[:300]} |')
    text = '\n'.join(lines) + '\n'
    if args.out:
        os.makedirs(os.path.dirname(args.out), exist_ok=True)
        with open(args.out, 'w', encoding='utf-8') as f:
            f.write(text)
        print(f'已生成对照表: {args.out}')
    else:
        print(text)
    con.close()
    return 0


def main():
    ap = argparse.ArgumentParser(description='Q-Chem 关键词数据库提示文本汉化工具')
    sub = ap.add_subparsers(dest='cmd', required=True)

    p = sub.add_parser('export', help='导出待译文本段（HTML 安全）')
    p.add_argument('--out', default='')
    p.add_argument('--batch', default='', help='分批，如 1/6')
    p.set_defaults(func=cmd_export)

    p = sub.add_parser('import', help='回填译文到数据库（自动备份）')
    p.add_argument('--in', dest='input', required=True)
    p.add_argument('--no-backup', action='store_true')
    p.set_defaults(func=cmd_import)

    p = sub.add_parser('verify', help='校验数据库与汉化覆盖率')
    p.set_defaults(func=cmd_verify)

    p = sub.add_parser('table', help='生成 Markdown 对照表')
    p.add_argument('--out', default='')
    p.add_argument('--orig', default='', help='英文原库路径，用于生成 原文/译文 两列对照')
    p.set_defaults(func=cmd_table)

    args = ap.parse_args()
    return args.func(args)


if __name__ == '__main__':
    sys.exit(main())
