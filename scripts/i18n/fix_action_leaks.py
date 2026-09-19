#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""修复新发现的第 4 类 i18n 漏包：QAction 文本未包 tr()。

背景
----
IQmol 的右键菜单由 Layer::Base::newAction(QString const&) 和散落各处的
menu->addAction(QString) 动态创建。这些调用点直接传 C 字符串字面量，
既没有 tr() 也没有 QCoreApplication::translate()，因此 lupdate 提取不到，
界面上永远是英文。

本脚本把
    newAction("Configure")            ->  newAction(tr("Configure"))
    menu->addAction("Gasteiger")      ->  menu->addAction(tr("Gasteiger"))
统一包上 tr()。

安全性
------
所有受影响的类都继承 Layer::Base(: public QObject)，或自身是 QDialog 子类
（GridInfoDialog），因此 tr() 在编译期可用。脚本在改动前会逐文件断言
存在 QObject/QDialog 继承标记，否则跳过并报警。

用法
----
    python3 scripts/i18n/fix_action_leaks.py            # 预演（dry-run）
    python3 scripts/i18n/fix_action_leaks.py --apply    # 实际写入
"""

import argparse
import os
import re
import sys

TOPDIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 跳过这些路径：save/ 目录是历史弃用副本，不参与编译
SKIP_DIR_PARTS = ('/save/', '\\save\\')

# newAction("X")  /  addAction("X")
NEWACTION_RE = re.compile(r'\bnewAction\(\s*"((?:[^"\\]|\\.)*)"\s*\)')
ADDACTION_RE = re.compile(r'\baddAction\(\s*"((?:[^"\\]|\\.)*)"\s*(,|\))')

# 判断该 .C 文件对应的类是否有 tr() 依据：递归追溯继承链直到命中 QObject。
# 例：Group : Primitive : GLObject : Base : QObject   —— 有 tr()
#     GridInfoDialog : QDialog                        —— 有 tr()
# 追溯失败（找不到基类、链上有纯类）则判定为不安全，跳过不改。
QOBJECT_ROOTS = {'QDialog', 'QMainWindow', 'QWidget', 'QObject', 'QGraphicsItem'}

# 在所有 Layer/ 及常见头文件里抓 "class X : public Y" / "class X : public Y, public Z"
INHERIT_RE = re.compile(
    r'\bclass\s+([A-Za-z_]\w*)\s*:\s*([^{;]+)\{')


def build_inherit_map():
    """扫描 src/ 下所有 .h，建立 类名 -> [直接基类名] 映射。"""
    m = {}
    for root, _dirs, files in os.walk(os.path.join(TOPDIR, 'src')):
        for fn in files:
            if not fn.endswith('.h'):
                continue
            try:
                txt = open(os.path.join(root, fn), encoding='utf-8').read()
            except Exception:
                continue
            for mm in INHERIT_RE.finditer(txt):
                cls = mm.group(1)
                bases = []
                for part in mm.group(2).split(','):
                    # 去掉 public/protected/private/virtual 限定
                    b = re.sub(r'\b(public|protected|private|virtual)\b', '', part).strip()
                    # 只取裸类名（忽略命名空间与模板实参）
                    b = b.split('<')[0].strip()
                    b = b.split('::')[-1].strip()
                    if b:
                        bases.append(b)
                if cls not in m or len(bases) > len(m[cls]):
                    m[cls] = bases
    return m


_INHERIT = None


def has_tr_evidence(c_file):
    """递归追溯继承链，判断是否有 QObject/QDialog 祖先。"""
    global _INHERIT
    if _INHERIT is None:
        _INHERIT = build_inherit_map()

    h = c_file[:-2] + '.h'
    if not os.path.exists(h):
        return False
    txt = open(h, encoding='utf-8').read()

    # 取头文件里第一个非前向声明的类名作为入口
    names = [mm.group(1) for mm in INHERIT_RE.finditer(txt)]
    if not names:
        return False
    start = names[0]

    seen = set()
    stack = [start]
    while stack:
        cur = stack.pop()
        if cur in seen:
            continue
        seen.add(cur)
        if cur in QOBJECT_ROOTS:
            return True
        for b in _INHERIT.get(cur, []):
            if b not in seen:
                stack.append(b)
    return False


def find_targets():
    out = []
    for root, dirs, files in os.walk(os.path.join(TOPDIR, 'src')):
        # 路径含 save 目录（历史弃用副本）直接剪枝
        if os.path.basename(root) == 'save' or any(p in (root + '/') for p in SKIP_DIR_PARTS):
            dirs[:] = []
            continue
        for fn in files:
            if fn.endswith('.C'):
                out.append(os.path.join(root, fn))
    return sorted(out)


def process(path, apply_):
    src = open(path, encoding='utf-8').read()
    lines = src.split('\n')

    changed = []
    for i, ln in enumerate(lines):
        stripped = ln.lstrip()
        # 跳过整行注释
        if stripped.startswith('//'):
            continue
        new_ln = ln

        # --- newAction("...") ---
        def _na(m):
            return 'newAction(tr("%s"))' % m.group(1)
        t = NEWACTION_RE.sub(_na, new_ln)
        if t != new_ln:
            new_ln = t
            changed.append((i + 1, 'newAction'))

        # --- addAction("...") 注意第 2 参数（slot 形式）要保留 ---
        def _aa(m):
            tail = m.group(2)
            return 'addAction(tr("%s")%s' % (m.group(1), tail)
        t = ADDACTION_RE.sub(_aa, new_ln)
        if t != new_ln:
            new_ln = t
            if not any(c[0] == i + 1 for c in changed):
                changed.append((i + 1, 'addAction'))

        lines[i] = new_ln

    if not changed:
        return None

    # 安全检查：配套头文件里必须有 QObject/QDialog 继承痕迹
    if not has_tr_evidence(path):
        return ('UNSAFE', path, changed)

    if apply_:
        open(path, 'w', encoding='utf-8').write('\n'.join(lines))
    return (path, changed)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true', help='实际写入改动')
    args = ap.parse_args()

    total_files = 0
    total_edits = 0
    unsafe = []

    for path in find_targets():
        r = process(path, args.apply)
        if r is None:
            continue
        if r[0] == 'UNSAFE':
            unsafe.append(r[1])
            continue
        p, ch = r
        rel = os.path.relpath(p, TOPDIR)
        total_files += 1
        total_edits += len(ch)
        for lineno, kind in ch:
            print('  %-52s :%-5d %s' % (rel, lineno, kind))

    print()
    print('受影响文件 %d 个，改动 %d 处' % (total_files, total_edits))
    if unsafe:
        print('警告：以下文件未发现 QObject/QDialog 继承标记，已跳过：')
        for u in unsafe:
            print('  ', os.path.relpath(u, TOPDIR))
    if not args.apply:
        print('\n这是预演。加 --apply 才会写入。')


if __name__ == '__main__':
    main()
