#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
按规则表重放 tr() 包裹（幂等）。第三层方案 A 项的核心工具。

用途
----
上游发布新版本后，本仓库的汉化成果里最脆弱的部分是散落在 36 个源文件里的
`tr()` 包裹。若上游改动了这些文件，`git merge` 会产生冲突；即便自动合并成功，
也可能把我们的包裹覆盖掉。

有了规则表（scripts/i18n/wrap_tr.rules），恢复包裹不再需要人工逐行核对：

    python3 scripts/i18n/replay_tr.py --check     # 只报告差异，不落盘
    python3 scripts/i18n/replay_tr.py             # 就地重放

幂等性
------
已包裹为 tr("X") 的字面量不会被二次包裹（会先检查前缀）。
因此对同一份代码重复执行，结果稳定不变 —— 这是"可重放"的前提。

与 wrap_tr.py 的关系
--------------------
`wrap_tr.py` 是【历史遗留】的行号驱动脚本，只服务 MainWindow.C，
行号随上游改动即失效，已由本脚本（内容驱动）取代。保留仅为归档。
"""
import argparse
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RULES = os.path.join(REPO, 'scripts/i18n/wrap_tr.rules')

# 永不包裹的字面量（力场名、格式标识等纯技术符号）。
# 注意：不要在这里放品牌名 IQmol —— 它在不同上下文里的处理并不一致：
#   setWindowTitle("IQmol")                      → 包裹（窗口标题参与翻译）
#   QMessageBox(..., "IQmol", tr("..."))         → 不包裹（消息框署名不翻）
# 规则表已用 `call:<函数名>` 精确区分这两种情况，重放时尊重函数上下文即可，
# 在此一概排除反而会漏掉该包的那一处。
NEVER_WRAP = {
    'UFF', 'MMFF94', 'MMFF94s', 'PM3', 'AM1', 'MNDO',
    'B3LYP', 'MP2', 'CCSD', 'CCSD(T)',
    'PDF', 'PNG', 'JPEG', 'SVG', 'POV-Ray', 'XYZ', 'MOL', 'PDB', 'CIF',
}


def load_rules(path):
    """读规则表 → [(relpath, literal, form, count), ...]"""
    out = []
    with open(path, encoding='utf-8') as f:
        for raw in f:
            line = raw.rstrip('\n')
            if not line or line.startswith('#'):
                continue
            parts = line.split('\t')
            if len(parts) != 4:
                continue
            relpath, literal, form, count = parts
            if literal in NEVER_WRAP:
                continue        # 品牌名等：永不包裹
            out.append((relpath, literal, form, count))
    return out


def _already_wrapped(text, literal):
    """统计已被 tr("literal") 包裹的次数。"""
    pat = re.compile(r'tr\(\s*"' + re.escape(literal) + r'"\s*\)')
    return len(pat.findall(text))


def _bare_occurrences(text, literal, func=None):
    """
    找出【尚未被包裹】的 "literal" 出现位置。
    返回 [(start, end)]，其中 start/end 是含双引号的区间。

    三种形态由调用方通过 locator 的取值区分：
      locator is None               → bare：找所有未被 tr()/translate() 包裹的出现
      locator = 'tr:<函数名>'        → 补足式：只认可「紧跟在 <函数名>( 之后」的
                                       —— 即上游已有部分 tr()，本次补足剩余
      locator = 'translate:<上下文>' → 构造式：上游是裸字面量，需要连
                                       QCoreApplication::translate("Ctx", ) 一起生成；
                                       只认可「尚未被任何 translate() 包裹」的出现

    locator 精确化这一步至关重要：同一个字面量可能在同一文件里出现在不同上下文中，
    而我们的汉化只包裹了其中一部分。例如 MainWindow.C 里
        setWindowTitle("IQmol")                        ← 已包裹
        QMessageBox(..., "IQmol", tr("Save Changes?")) ← 未包裹（品牌名不翻）
    若忽略函数名而全局替换，就会把不该包的也包上。
    """
    if func and func.startswith('translate:'):
        # 构造式：与 bare 的定位规则一致（找裸出现），外层包裹形式不同
        return _unwrapped_literal_spans(text, literal)

    if func:
        # 补足式：匹配 <func>( 之后紧跟的字面量
        pat = re.compile(re.escape(func) + r'\s*\(\s*"(' + re.escape(literal) + r')"')
        result = []
        for m in pat.finditer(text):
            end = m.end()
            start = end - len(literal) - 2      # 减去两侧引号
            if text[start:end] == '"' + literal + '"':
                result.append((start, end))
        return result

    return _unwrapped_literal_spans(text, literal)


def _ensure_include(text, include_line):
    """
    确保 text 含有指定的 #include。已存在则原样返回。
    插入位置：最后一个已存在的 #include <Qt...> 之后；若无，则放在
    文件开头注释块（IQmol 的 license 头）之后、第一个 #include 之前。
    """
    if re.search(r'^\s*#\s*include\s*<' + re.escape(include_line[10:-1]) + r'>',
                 text, re.M):
        return text

    lines = text.split('\n')
    last_inc = -1
    for i, ln in enumerate(lines):
        if re.match(r'\s*#\s*include\s*[<"]', ln):
            last_inc = i
    if last_inc >= 0:
        lines.insert(last_inc + 1, include_line)
        return '\n'.join(lines)

    # 没有 include：插到文件头注释块之后
    for i, ln in enumerate(lines):
        if not ln.strip() and i > 0:
            lines.insert(i + 1, include_line)
            return '\n'.join(lines)
    return include_line + '\n' + text


def _unwrapped_literal_spans(text, literal):
    pat = re.compile(r'"' + re.escape(literal) + r'"')
    wrapped_spans = []
    # 已被 tr() 包裹
    for m in re.finditer(r'tr\(\s*"' + re.escape(literal) + r'"\s*\)', text):
        inner = re.search(r'"' + re.escape(literal) + r'"', m.group(0))
        if inner:
            wrapped_spans.append((m.start() + inner.start(), m.start() + inner.end()))
    # 已被 QCoreApplication::translate("...", ) 包裹
    for m in re.finditer(
            r'QCoreApplication\s*::\s*translate\(\s*"(?:[^"\\]|\\.)*"\s*,\s*"'
            + re.escape(literal) + r'"\s*\)', text):
        inner = re.search(r'"' + re.escape(literal) + r'"\s*\)\s*$', m.group(0))
        if inner:
            wrapped_spans.append((m.start() + inner.start(),
                                  m.start() + inner.end() - 1))

    result = []
    for m in pat.finditer(text):
        span = (m.start(), m.end())
        if any(ws <= span[0] and span[1] <= we for ws, we in wrapped_spans):
            continue
        result.append(span)
    return result


def apply_rules(rules, dry_run=True):
    """
    返回 (changed_files, total_wraps, details)。
    details: [(relpath, literal, 包裹处数)]
    """
    by_file = {}
    for relpath, literal, form, count in rules:
        by_file.setdefault(relpath, []).append((literal, form, count))
    changed_files = []
    total = 0
    details = []

    for relpath, items in sorted(by_file.items()):
        abspath = os.path.join(REPO, relpath)
        if not os.path.isfile(abspath):
            details.append((relpath, '（文件不存在，跳过）', 0))
            continue

        with open(abspath, encoding='utf-8') as f:
            text = f.read()
        original = text
        file_wraps = 0
        # 本文件是否已注入过 QCoreApplication 头（translate 形态需要）
        has_qca_include = bool(re.search(r'^\s*#\s*include\s*<QCoreApplication>',
                                        text, re.M))

        for literal, form, count in items:
            # 形态 → _bare_occurrences 的定位参数 & 包裹模板
            if form.startswith('translate:'):
                ctx = form[len('translate:'):]
                locator = 'translate:' + ctx
                pre_tpl = 'QCoreApplication::translate("' + ctx + '", '
                post_tpl = ')'
                # 已包裹计数：按 <上下文, 字面量> 精确统计
                done_pat = (r'QCoreApplication\s*::\s*translate\(\s*"'
                            + re.escape(ctx) + r'"\s*,\s*"' + re.escape(literal) + r'"\s*\)')
                done = len(re.findall(done_pat, text))
            else:
                func = form[5:] if form.startswith('call:') else None
                locator = func
                pre_tpl, post_tpl = 'tr(', ')'
                done = len(re.findall(r'tr\(\s*"' + re.escape(literal) + r'"\s*\)', text))

            spans = _bare_occurrences(text, literal, locator)
            if not spans:
                continue
            # count 的语义 = 该字面量在该文件中【最终应被包裹的总数】
            # （由 extract_tr_rules.py 从成果文件统计）。因此本次只需补
            # (count - 已包裹数) 处：
            #   - 上游自带 tr() 的情形 → 已包裹数 > 0，不会重复包；
            #   - 已重放过的文件       → 已包裹数 == count，need<=0 直接跳过。
            # 这两点共同保证幂等。
            try:
                target = int(count)
            except (TypeError, ValueError):
                target = len(spans)
            need = target - done
            if need <= 0:
                continue
            spans = spans[:need]
            # 从后往前替换，避免偏移失效
            for start, end in reversed(spans):
                text = text[:start] + pre_tpl + text[start:end] + post_tpl + text[end:]
            file_wraps += len(spans)
            details.append((relpath, literal, len(spans)))
            # translate 形态需要 QCoreApplication 声明；原文件若没有则补一个 include
            if pre_tpl.startswith('QCoreApplication::') and not has_qca_include:
                text = _ensure_include(text, '#include <QCoreApplication>')
                has_qca_include = True

        if text != original:
            changed_files.append(relpath)
            total += file_wraps
            if not dry_run:
                with open(abspath, 'w', encoding='utf-8') as f:
                    f.write(text)

    return changed_files, total, details


def main():
    ap = argparse.ArgumentParser(
        description='按规则表幂等重放 tr() 包裹',
        epilog='安全默认：不加 --apply 时只报告、不写盘。')
    ap.add_argument('--rules', default=RULES, help=f'规则表路径（默认 {RULES}）')
    ap.add_argument('--apply', action='store_true',
                    help='实际写入文件。默认只报告（dry-run），这是安全护栏')
    ap.add_argument('--quiet', action='store_true', help='只输出汇总')
    args = ap.parse_args()

    if not os.path.isfile(args.rules):
        print(f"ERROR: 规则表不存在: {args.rules}", file=sys.stderr)
        print("       先运行: python3 scripts/i18n/extract_tr_rules.py", file=sys.stderr)
        return 1

    rules = load_rules(args.rules)
    changed, total, details = apply_rules(rules, dry_run=not args.apply)

    if not args.quiet:
        for relpath, literal, n in details:
            if n:
                print(f"  +{n}  {relpath}  ←  {literal[:60]}")

    print()
    print(f"规则条数    : {len(rules)}")
    print(f"涉及文件    : {len(set(r for r, _, _ in details))}")
    print(f"新增包裹处数: {total}")
    print(f"改动文件数  : {len(changed)}")
    if not args.apply:
        print("\n（dry-run 模式，未写盘。确认无误后加 --apply 执行）")
    else:
        print("\n✅ 重放完成。建议随后运行 git diff 复核。")
    return 0


if __name__ == '__main__':
    sys.exit(main())
