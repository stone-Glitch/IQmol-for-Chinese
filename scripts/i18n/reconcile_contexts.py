#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把译文对齐到 lupdate 认定的权威 context。

背景
----
Qt 的 tr() 在运行时按「类名」查表。lupdate 扫描源码时，会把某个 tr()
字面量登记到它认为的 context 下（通常是 `IQmol::Lib::ClassName`，也可能
是 `InputDialog`、`UndoCommands` 这类短名，取决于源码里 namespace 的写法和
lupdate 能否解析）。

历史上我们的 ts 手工补过一批条目，context 名字和 lupdate 认定的不一致
（例如把 `Save As` 放进了 `IQmol::MainWindow`，而源码里它其实在
`InputDialog` 下）。这种「译文存在但 context 不对」会造成界面残留英文，
而且从 lrelease 的 unfinished 统计里看不出来 —— 因为那个 context 下
确实有这条翻译，只是运行时永远查不到。

本脚本做的事
------------
1. 用 lupdate 重新扫描源码，得到权威的 (context -> sources) 映射；
2. 读取我们现有的 ts，建立 source -> 译文 的全局索引（同一字符串在
   不同 context 下译文通常相同）；
3. 对每一个权威 context 里缺少译文的字符串，从全局索引里取译文补上；
4. 输出补充清单，供人工复核。

用法
----
    python3 scripts/i18n/reconcile_contexts.py            # 只报告，不写盘
    python3 scripts/i18n/reconcile_contexts.py --apply    # 实际写盘
"""

import argparse
import os
import re
import subprocess
import sys
import tempfile

TOPDIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
TS = os.path.join(TOPDIR, 'translations', 'zh_CN.ts')

CONTEXT_RE = re.compile(r'<context>\s*<name>([^<]+)</name>(.*?)</context>', re.S)
MESSAGE_RE = re.compile(
    r'<source>(.*?)</source>\s*<translation([^>]*)>(.*?)</translation>', re.S)

# ---------------------------------------------------------------------------
# 同形异义保护表
#
# 同一个英文串在不同界面里含义不同，跨 context 搬运译文会串味。例如
# "Alpha" 在颜色对话框里是「不透明度」，在轨道/激发态图里是「Alpha 自旋」。
# 这些串一律不自动搬运，必须人工按目标语境给译文。
#
# 格式： source -> {只允许来源的 context 集合} 或 None（禁止自动搬运）
# ---------------------------------------------------------------------------
AMBIGUOUS = {
    'Alpha': {
        'IQmol::Configurator::Orbitals': 'Alpha',
        'IQmol::Data::SurfaceType': 'Alpha',
        'IQmol::Configurator::ExcitedStates': 'Alpha',
    },
    'Beta': {
        'IQmol::Configurator::Orbitals': 'Beta',
        'IQmol::Data::SurfaceType': 'Beta',
        'IQmol::Configurator::ExcitedStates': 'Beta',
    },
    'Default': {
        'IQmol::ShaderDialog': '默认',
        'IQmol::Color::Dialog': '默认',
        'ShaderDialog': '默认',
        'ColorDialog': '默认',
    },
    # HTML 富文本（About 对话框、Info 面板的占位符等）：不搬运，
    # 由专门的 UI 翻译流程处理
}

# 明显不该进 ts 的 HTML 富文本 / 纯占位内容
SKIP_SOURCE_RE = re.compile(r'^\s*<!DOCTYPE|^\s*<html|^\s*<p style')


def parse_ts(path):
    """返回 {context: {source: (translation, attrs)}}"""
    text = open(path, encoding='utf-8').read()
    out = {}
    for cm in CONTEXT_RE.finditer(text):
        ctx, body = cm.group(1), cm.group(2)
        d = out.setdefault(ctx, {})
        for mm in MESSAGE_RE.finditer(body):
            d[mm.group(1)] = (mm.group(3), mm.group(2))
    return out


def run_lupdate():
    """跑 lupdate 到临时文件，返回解析结果。"""
    tmp = tempfile.NamedTemporaryFile(suffix='.ts', delete=False)
    # lupdate 会把已有 ts 读进来做「保留旧译文」的匹配，因此文件必须是
    # 合法 XML。空文件会报 "Premature end of document"，故先写个骨架。
    tmp.write(b'<?xml version="1.0" encoding="utf-8"?>\n'
              b'<!DOCTYPE TS>\n<TS version="2.1" language="zh_CN">\n</TS>\n')
    tmp.close()
    subprocess.run(
        ['lupdate', '-extensions', 'C,ui',
         os.path.join(TOPDIR, 'src') + '/', '-ts', tmp.name],
        check=True, capture_output=True)
    data = parse_ts(tmp.name)
    os.unlink(tmp.name)
    return data


def esc(s):
    return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true',
                    help='实际写入 ts（默认只报告）')
    args = ap.parse_args()

    print('==> lupdate 扫描源码，取得权威 context 表')
    fresh = run_lupdate()
    ours = parse_ts(TS)

    # 全局 source -> 译文（取第一个非空）
    global_tr = {}
    for _ctx, d in ours.items():
        for src, (tr, attrs) in d.items():
            if tr.strip() and src not in global_tr:
                global_tr[src] = tr

    # 找出需要补的 (context, source)
    plan = {}
    unresolved = []
    skipped = []
    for ctx, d in fresh.items():
        for src in d:
            cur = ours.get(ctx, {}).get(src, ('', ''))[0]
            if cur.strip():
                continue                       # 该 context 下已有译文
            if SKIP_SOURCE_RE.match(src):
                skipped.append((ctx, src))
                continue
            if src in AMBIGUOUS:
                # 同形异义：只在白名单里直接取，否则交人工
                tr = AMBIGUOUS[src].get(ctx)
                if tr:
                    plan.setdefault(ctx, {})[src] = tr
                else:
                    unresolved.append((ctx, src, '同形异义，需按语境人工翻译'))
                continue
            if src in global_tr:
                plan.setdefault(ctx, {})[src] = global_tr[src]
            else:
                unresolved.append((ctx, src, 'ts 中无此译文'))

    total = sum(len(v) for v in plan.values())
    print(f'\n需要补入的条目：{total} 条，涉及 {len(plan)} 个 context')
    for ctx in sorted(plan, key=lambda c: -len(plan[c])):
        print(f'  --- {ctx} ({len(plan[ctx])}) ---')
        for src, tr in sorted(plan[ctx].items()):
            print(f'      {src!r:<44} -> {tr!r}')

    if skipped:
        print(f'\n跳过（HTML 富文本，不走此流程）：{len(skipped)} 条')
        for ctx, src in skipped:
            print(f'      [{ctx}] {src[:60]!r}...')

    if unresolved:
        print(f'\n⚠ 需人工处理：{len(unresolved)} 条')
        for ctx, src, why in unresolved:
            label = src if len(src) < 70 else src[:67] + '...'
            print(f'      [{ctx}] {label!r}   ({why})')

    if not args.apply:
        print('\n（未写盘；加 --apply 生效）')
        return 0

    # ---- 写盘：往对应 context 块尾部插入 <message> ----
    text = open(TS, encoding='utf-8').read()
    inserted = 0
    created = 0
    for ctx, items in plan.items():
        anchor = f'<name>{ctx}</name>'
        i = text.find(anchor)
        ins = ''.join(
            f'        <message>\n'
            f'            <source>{esc(s)}</source>\n'
            f'            <translation>{esc(t)}</translation>\n'
            f'        </message>\n'
            for s, t in sorted(items.items()))
        if i < 0:
            # 我们的 ts 里还没有这个 context（lupdate 认定的名字和我们
            # 历史手工建的块不一致）。新建一个完整 <context> 块。
            block = (f'    <context>\n'
                     f'        <name>{ctx}</name>\n'
                     f'{ins}'
                     f'    </context>\n')
            k = text.rfind('</TS>')
            text = text[:k] + block + text[k:]
            created += 1
        else:
            j = text.find('</context>', i)
            text = text[:j] + ins + text[j:]
        inserted += len(items)

    open(TS, 'w', encoding='utf-8').write(text)
    print(f'\n已写入 {inserted} 条到 {TS}'
          f'（其中新建 context {created} 个）')
    return 0


if __name__ == '__main__':
    sys.exit(main())
