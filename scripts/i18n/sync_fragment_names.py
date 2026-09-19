#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 fragment_names.py 的片段名译文写入 translations/zh_CN.ts。

为什么单独一个脚本
------------------
FragmentTable.C 的片段名来自目录/文件名（运行时变量），lupdate 提取不到，
必须手工维护。本脚本把 fragment_names.py 里的人工译表同步进 ts，可重复运行。

行为
----
1. 读取 fragment_names.FRAGMENTS
2. 在 ts 中定位（或新建）<context><name>FragmentTable</name>
3. 逐条插入/更新 <message>，已存在且译文相同的跳过
4. 不触碰其他 context

用法
----
    python3 scripts/i18n/sync_fragment_names.py            # 预演
    python3 scripts/i18n/sync_fragment_names.py --apply    # 写入
"""

import argparse
import os
import re
import sys

TOPDIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fragment_names import FRAGMENTS  # noqa: E402

TS = os.path.join(TOPDIR, 'translations', 'zh_CN.ts')
CTX = 'FragmentTable'

CONTEXT_RE = re.compile(r'<context>\s*<name>([^<]+)</name>(.*?)</context>', re.S)
MESSAGE_RE = re.compile(r'<source>(.*?)</source>\s*<translation([^>]*)>(.*?)</translation>', re.S)


def esc(s):
    return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true')
    args = ap.parse_args()

    text = open(TS, encoding='utf-8').read()

    # 取出该 context 现有条目
    existing = {}
    m = None
    for mm in CONTEXT_RE.finditer(text):
        if mm.group(1) == CTX:
            m = mm
            for e in MESSAGE_RE.finditer(mm.group(2)):
                existing[e.group(1)] = e.group(3)
            break

    to_add = []      # 全新条目
    to_update = []   # 已有但译文不同
    for src, tr in sorted(FRAGMENTS.items()):
        cur = existing.get(src)
        if cur is None:
            to_add.append((src, tr))
        elif cur.strip() != tr:
            to_update.append((src, cur.strip(), tr))

    print('FragmentTable context 现有 %d 条' % len(existing))
    print('新增 %d 条，更新 %d 条' % (len(to_add), len(to_update)))
    for src, tr in to_add[:8]:
        print('   + %-30s -> %s' % (src, tr))
    if len(to_add) > 8:
        print('   ...（共 %d 条）' % len(to_add))
    for src, old, new in to_update[:8]:
        print('   ~ %-30s %r -> %r' % (src, old, new))

    if not args.apply:
        print('\n这是预演。加 --apply 才会写入。')
        return 0

    def entry(src, tr):
        return ('        <message>\n'
                '            <source>%s</source>\n'
                '            <translation>%s</translation>\n'
                '        </message>\n' % (esc(src), esc(tr)))

    if m is None:
        # 新建整个 context
        body = ''.join(entry(s, t) for s, t in sorted(FRAGMENTS.items()))
        block = ('    <context>\n'
                 '        <name>%s</name>\n'
                 '%s'
                 '    </context>\n' % (CTX, body))
        k = text.rfind('</TS>')
        text = text[:k] + block + text[k:]
        print('已新建 context %s' % CTX)
    else:
        body = m.group(2)
        # 更新已有
        for src, _old, tr in to_update:
            pat = re.compile(
                r'(<source>' + re.escape(esc(src)) + r'</source>\s*'
                r'<translation[^>]*>).*?(</translation>)', re.S)
            body = pat.sub(lambda mm: mm.group(1) + esc(tr) + mm.group(2), body)
        # 追加新增
        body = body.rstrip('\n ') + '\n' + ''.join(entry(s, t) for s, t in to_add)
        text = text[:m.start(2)] + body + text[m.end(2):]

    open(TS, 'w', encoding='utf-8').write(text)
    print('\n已写入 ts')
    return 0


if __name__ == '__main__':
    sys.exit(main())
