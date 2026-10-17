#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_tr_coverage.py — P2-10 源码侧 tr() 覆盖率门禁（防回退）

背景：
  lupdate 只能提取「已被 tr()/translate() 包裹」的字符串。若源码里把
  界面可见文本直接写死（裸字符串字面量出现在 UI 文本设置调用中而未包 tr()），
  lupdate 扫不到 → zh_CN.ts 缺失 → 界面显示英文。此类漏网项 TQA 的
  翻译文件侧指标管不到，故需这道「源码侧」门禁。

判定口径（复现 docs/汉化工程/界面英文残留清单.md 的扫描方法）：
  在 .C/.h 源码中，若「界面文本消费函数」(setText/setTitle/setWindowTitle/
  addAction/QAction 构造/QMessageBox::*/... ) 调用后紧跟一个「裸字符串字面量」
  （未被 tr()/translate() 包裹），即记为「疑似可见未翻译」候选。

白名单（scripts/i18n/source_tr_whitelist.json）：
  列出允许保留英文的 source 字面量（精确匹配），每条带 reason。
  类别：Q-Chem 关键字/基组名、单位符号、文件名/路径、URL、品牌/力场名、
  内部标识符、日志/调试串、HTML/CSS 片段、枚举/协议常量等。
  不在白名单的候选 = 未授权残留，计入门禁。

门禁：
  未授权残留数 > --limit（默认 5，即「容忍 5 条」）则非 0 退出。
  另以 --baseline 防恶化：残留数 > baseline 亦 fail（比基线多即回退）。

用法：
  python3 check_tr_coverage.py --report        # 打印候选明细 + 白名单匹配
  python3 check_tr_coverage.py --json          # 机器可读
  python3 check_tr_coverage.py --gate          # 门禁，非 0 即失败
  python3 check_tr_coverage.py --gate --limit 5 --baseline 0
"""
import argparse
import json
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(REPO, 'src')
WHITELIST = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         'source_tr_whitelist.json')

DEFAULT_LIMIT = 5

# 不参与构建的备份/存档目录（手动副本，避免误报）
EXCLUDE_DIRS = {'save', 'backup', '_archive', '__pycache__'}

# ---- 界面文本消费函数：其「字符串参数」视为可见文本候选 ----
UI_CONSUMERS = {
    'setText', 'setWindowTitle', 'setWindowIconText', 'setTitle', 'setLabel',
    'setToolTip', 'setStatusTip', 'setWhatsThis', 'setPlaceholderText',
    'setItemText', 'setTabText', 'setHeaderLabel', 'setFooterLabel',
    'setToolTip', 'setStatusTip', 'addAction', 'addMenu', 'addSection',
    'setMenuText', 'setPopupMenuText',
    # 构造 / 静态调用
    'QAction', 'QMessageBox',  # QMessageBox::information/warning/... 静态方法
    'information', 'warning', 'critical', 'question',  # QMessageBox 静态方法名
}

# 出现在这些「父调用」后、字符串字面量前的标识符 → 视为已翻译包装，排除
TRANSLATE_WRAPPERS = {'tr', 'translate', 'QCoreApplication', 'QObject',
                      'QT_TRANSLATE_NOOP', 'QT_TR_NOOP'}

# 行内字符串字面量（含转义）
STR_RE = re.compile(r'"((?:[^"\\]|\\.)*)"')
# 标识符
IDENT_RE = re.compile(r'[A-Za-z_][A-Za-z0-9_]*')


def load_whitelist():
    if not os.path.isfile(WHITELIST):
        return {}, []
    try:
        d = json.load(open(WHITELIST, encoding='utf-8'))
        items = d.get('whitelist', [])
        return {it['text']: it.get('reason', '') for it in items}, items
    except Exception as e:
        print(f'::warning::白名单读取失败: {e}', file=sys.stderr)
        return {}, []


def is_stream_or_log(before):
    """排除 qDebug() << "..."、 cerr << "..."、日志流输出等。"""
    return '<<' in before


def scan_file(path):
    """返回该文件命中的候选列表：[(lineno, text, consumer, wrapped)]"""
    hits = []
    try:
        lines = open(path, encoding='utf-8', errors='replace').read().splitlines()
    except Exception:
        return hits
    in_block_comment = False
    for ln, raw in enumerate(lines, 1):
        line = raw
        # 去除块注释（粗处理：同行 /* ... */）
        if in_block_comment:
            end = line.find('*/')
            if end == -1:
                continue
            line = line[end + 2:]
            in_block_comment = False
        # 去行注释
        cmt = line.find('//')
        if cmt != -1:
            line = line[:cmt]
        if '/*' in line:
            start = line.find('/*')
            rest = line[start + 2:]
            end = rest.find('*/')
            if end == -1:
                in_block_comment = True
                line = line[:start]
            else:
                line = line[:start] + rest[end + 2:]
        # 找所有字符串字面量
        for m in STR_RE.finditer(line):
            text = m.group(1)
            # 排除空串 / 纯空白占位（非可见文本，如 setText("") 清空、对齐空格）
            if text.strip() == '':
                continue
            before = line[:m.start()]
            # 取字面量「直接所属」的调用：最右侧的 '('
            idx = before.rfind('(')
            if idx == -1:
                continue
            pre = before[:idx]
            idents = IDENT_RE.findall(pre)
            call = idents[-1] if idents else ''
            # 处理 A::B 形式（如 QMessageBox::information）：取最后的 B
            if call and '::' in pre[pre.rfind(call):]:
                mm = re.findall(r'::\s*([A-Za-z_][A-Za-z0-9_]*)', pre)
                if mm:
                    call = mm[-1]
            # 排除已翻译包装：字面量直接属于 tr()/translate() 等
            if call in TRANSLATE_WRAPPERS:
                continue
            # 排除日志/流输出
            if is_stream_or_log(before):
                continue
            # 仅当落在 UI 消费函数上下文才算候选
            if call in UI_CONSUMERS:
                hits.append((ln, text, call, False))
    return hits


def main():
    ap = argparse.ArgumentParser(description='源码侧 tr() 覆盖率门禁 (P2-10)')
    ap.add_argument('--report', action='store_true', help='打印候选明细')
    ap.add_argument('--json', action='store_true')
    ap.add_argument('--gate', action='store_true', help='门禁，非 0 退出')
    ap.add_argument('--limit', type=int, default=DEFAULT_LIMIT,
                    help='目标上限（默认 5）。给定 --baseline 时仅作告警目标；未给 --baseline 时作硬门禁')
    ap.add_argument('--baseline', type=int, default=None,
                    help='防恶化硬门禁基线：残留数 > 基线即 fail（禁止回退）。与 --limit 配合实现"先卡恶化再清零"')
    args = ap.parse_args()

    wl_map, wl_items = load_whitelist()

    candidates = []  # (file, lineno, text, consumer)
    scanned = 0
    for root, dirs, files in os.walk(SRC):
        # 排除备份/存档目录（不参与构建，避免扫描手动副本产生误报）
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        for fn in files:
            if fn.endswith(('.C', '.h')):
                fp = os.path.join(root, fn)
                scanned += 1
                for ln, text, consumer, _ in scan_file(fp):
                    rel = os.path.relpath(fp, REPO)
                    candidates.append((rel, ln, text, consumer))

    # 分类：白名单命中 vs 未授权
    authorized = [c for c in candidates if c[2] in wl_map]
    unauthorized = [c for c in candidates if c[2] not in wl_map]

    # 去重（同一字面量可能多处出现，按 text 统计种类 vs 出现次数）
    unauth_texts = sorted({c[2] for c in unauthorized})
    n_unauth = len(unauth_texts)          # 按「不同字面量种类」计
    n_unauth_occ = len(unauthorized)      # 按「出现次数」计
    n_auth = len({c[2] for c in authorized})

    res = {
        'scanned_files': scanned,
        'candidates_total': len(candidates),
        'whitelist_size': len(wl_items),
        'authorized_distinct': n_auth,
        'unauthorized_distinct': n_unauth,
        'unauthorized_occurrences': n_unauth_occ,
        'limit': args.limit,
        'baseline': args.baseline,
        'unauthorized_samples': [
            {'file': c[0], 'line': c[1], 'text': c[2], 'consumer': c[3]}
            for c in sorted(unauthorized, key=lambda x: (x[0], x[1]))
        ],
    }

    failures = []
    warnings = []
    if args.baseline is not None:
        # 防恶化硬门禁：不得超过基线（回退即失败）
        if n_unauth > args.baseline:
            failures.append(
                f"源码侧未授权硬编码 {n_unauth} 种 > 防恶化基线 {args.baseline}"
                f"（疑似回退：禁止新增未 tr() 包裹的可见字符串）")
        # 目标上限：仅告警（待分批清零后，把 --baseline 收紧为 --limit 即转硬门禁）
        if n_unauth > args.limit:
            warnings.append(
                f"未授权硬编码 {n_unauth} 种仍 > 目标上限 {args.limit}"
                f"（在基线 {args.baseline} 内暂不阻断；清零后把 --baseline 改 {args.limit} 收紧）")
    else:
        # 未给基线：直接按目标上限硬门禁
        if n_unauth > args.limit:
            failures.append(
                f"源码侧未授权硬编码 {n_unauth} 种 > 上限 {args.limit}")

    if args.json:
        out = dict(res)
        out['gate_failures'] = failures
        out['warnings'] = warnings
        print(json.dumps(out, ensure_ascii=False, indent=2))
    elif args.report:
        print('=' * 66)
        print('  源码侧 tr() 覆盖率审计 (P2-10)')
        print('=' * 66)
        print(f"  扫描文件数        : {scanned}")
        print(f"  候选总数          : {len(candidates)}")
        print(f"  白名单条目        : {len(wl_items)}")
        print(f"  白名单命中(种类)  : {n_auth}")
        print(f"  未授权残留(种类)  : {n_unauth}")
        print(f"  未授权残留(次数)  : {n_unauth_occ}")
        print(f"  目标上限          : {args.limit}（容忍 {args.limit} 条，最终收紧目标）")
        if args.baseline is not None:
            print(f"  防恶化基线        : {args.baseline}")
        print('-' * 66)
        if unauthorized:
            print('  未授权残留明细（按 文件:行 文本 [consumer]）:')
            for c in sorted(unauthorized, key=lambda x: (x[0], x[1])):
                print(f"    {c[0]}:{c[1]}  {c[2]!r}  [{c[3]}]")
        else:
            print('  ✅ 无未授权硬编码残留')
        print('-' * 66)
        if warnings:
            print('  ⚠ 告警（目标未达，暂不阻断）:')
            for w in warnings:
                print(f'     - {w}')
        if failures:
            print('  ⛔ 阻断项:')
            for f in failures:
                print(f'     - {f}')
        else:
            print('  ✅ 通过门禁（未触发防恶化红线）')
        print('=' * 66)
    else:
        # 默认：静默门禁判定
        pass

    if args.gate and failures:
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main())
