#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从既有 tr() 改动中【反向提取】规则表，供 wrap_tr.py 幂等重放。

设计意图
--------
我们相对上游的最主要改动是 `tr()` 包裹（36 个文件 / 178 处），
其形态是机械的：把可见 UI 字面量包进 `tr(...)`。
本脚本把这批改动提取成【内容驱动】的规则表，取代当初那种
【行号驱动】的硬编码（行号随上游改动立刻失效，内容规则可跨版本复用）。

两种改动形态
------------
1. 有函数前缀：   setText("Resolution")   ->  setText(tr("Resolution"))
2. 裸 tr()：      name = "About";         ->  name = tr("About");
                  labels << "Model View";  ->  labels << tr("Model View");
                  ? "A" : "B"              ->  ? tr("A") : tr("B")

形态 2 没有可供定位的函数名，因此规则表统一以【字面量】为键：
重放时在文件里查找该字面量的**裸出现**（未被 tr() 包裹的那次），就地包裹。
函数名仅作为附加信息记录，便于人工审阅。

用法
----
    # 提取规则并写入文件
    python3 scripts/i18n/extract_tr_rules.py --base af7ff60

    # 只校验覆盖率（应为 100%）
    python3 scripts/i18n/extract_tr_rules.py --base af7ff60 --verify

规则文件格式（TSV，`#` 开头为注释）
---------------------------------
    <相对路径>\t<字面量>\t<形态标记>\t<出现次数>

形态标记：`call:<函数名>` 或 `bare`。
"""
import argparse
import collections
import os
import re
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

SRC_EXT = ('.C', '.c', '.h', '.H', '.cpp', '.hpp', '.cc')

# 形态 1：<函数>(tr("<字面量>")  —— 不要求 tr(...) 之后紧跟 ")"，因为存在多参数调用
CALL_TR_RE = re.compile(r'([A-Za-z_][\w:.\->]*)\s*\(\s*tr\(\s*"((?:[^"\\]|\\.)*)"\s*\)')
# 形态 2：任何 tr("<字面量>")（含已经在上式匹配过的，用于去重兜底）
ANY_TR_RE = re.compile(r'tr\(\s*"((?:[^"\\]|\\.)*)"\s*\)')
# 形态 3：QCoreApplication::translate("<上下文>", "<字面量>")
#   非 QObject 的类（如 QUndoCommand 子类）没有 tr()，只能用静态翻译。
#   目前仅 UndoCommands.C 使用（9 处），但形态独立，单列以便重放精确定位。
QT_TRANSLATE_RE = re.compile(
    r'QCoreApplication\s*::\s*translate\(\s*"((?:[^"\\]|\\.)*)"\s*,\s*'
    r'"((?:[^"\\]|\\.)*)"\s*\)')


def git(*args):
    return subprocess.run(['git', '-C', REPO, *args],
                          capture_output=True, text=True, check=False).stdout


def changed_source_files(base):
    out = git('diff', '--name-only', base, 'HEAD')
    return [f for f in out.splitlines()
            if f.endswith(SRC_EXT) and os.path.isfile(os.path.join(REPO, f))]


def _added_lines(base, path):
    """产出该文件相对 base 的新增行（不含 +++ 头）。"""
    diff = git('diff', '--unified=0', base, 'HEAD', '--', path)
    for line in diff.splitlines():
        if line.startswith('+') and not line.startswith('+++'):
            yield line[1:]


def extract(base):
    """
    返回 {(path, literal, form): total_wrapped}。

    同一字面量在同一文件里可能有【多种形态】，例如 MainWindow.C 里的 Save：
        messageBox.addButton(tr("Save"), QMessageBox::AcceptRole)   ← call:messageBox.addButton
        name = tr("Save");                                          ← bare
    因此键里必须带形态，否则会漏掉其中一种（实际踩过）。

    count 采用【语义 B】：<该形态在该文件中最终被 tr() 包裹的总数>。
    为什么不数 diff 的 + 行（语义 A）：上游往往已经带了一部分 tr()，
    例如 ExcitedStatesConfigurator.C 里
        第 341 行  setLabel(tr("Rel. Strength"))   ← 上游自带
        第 345 行  setLabel("Rel. Strength")       ← 裸的，由我们包裹
    语义 A 会得到 count=1，重放到成果上时"还有 1 处未包"→ 再包一次 → 不幂等。
    """
    rules = {}
    per_file = collections.Counter()

    # 第一遍：收集 (文件, 字面量, 形态) 三元组
    for path in changed_source_files(base):
        for body in _added_lines(base, path):
            # 形态 3：QCoreApplication::translate("Ctx", "X")
            #   先扫，避免其中的 "X" 被下面的 ANY_TR_RE 误判成 bare
            translate_spans = []
            for m in QT_TRANSLATE_RE.finditer(body):
                ctx, lit = m.group(1), m.group(2)
                rules.setdefault((path, lit, f'translate:{ctx}'), 1)
                translate_spans.append(m.span())

            for m in CALL_TR_RE.finditer(body):
                rules.setdefault((path, m.group(2), f'call:{m.group(1)}'), 1)
            for m in ANY_TR_RE.finditer(body):
                # 落在 translate(...) 里的 "X" 已由形态 3 登记，跳过
                if any(s <= m.start() < e for s, e in translate_spans):
                    continue
                # bare 形态只在没有 call 前缀时登记
                start = m.start()
                prefix = body[:start].rstrip()
                if prefix.endswith('(') and re.search(r'[A-Za-z_][\w:.\->]*\s*$', prefix):
                    continue
                rules.setdefault((path, m.group(1), 'bare'), 1)

    # 第二遍：按"最终包裹总数"归一。同一字面量若同时有 call 与 bare，
    # 分别统计各自在成果文件中的出现次数较为复杂，这里采用保守策略：
    # 记录【该字面量在文件中被 tr() 包裹的总数】，并优先保留 call 形态
    # （call 定位更精确），bare 形态的 count = 总数 - call 的 count。
    grouped = {}
    for (path, literal, form) in list(rules):
        grouped.setdefault((path, literal), []).append(form)

    final = {}
    for (path, literal), forms in grouped.items():
        abspath = os.path.join(REPO, path)
        trans_forms = sorted(f for f in forms if f.startswith('translate:'))
        call_forms = sorted(f for f in forms if f.startswith('call:'))
        has_bare = 'bare' in forms

        tr_total = 1
        if os.path.isfile(abspath):
            with open(abspath, encoding='utf-8') as f:
                text = f.read()
            tr_total = len(re.findall(r'tr\(\s*"' + re.escape(literal) + r'"\s*\)', text))
            per_file[path] += tr_total

        # translate 形态自成一路：按 <上下文, 字面量> 在成果文件中的实际出现数计数，
        # 与 tr() 的计数互不干扰（同一个字面量可能两个形态都用，如 UndoCommands.C）。
        for tf in trans_forms:
            ctx = tf[len('translate:'):]
            n = 1
            if os.path.isfile(abspath):
                n = len(re.findall(
                    r'QCoreApplication\s*::\s*translate\(\s*' + re.escape('"' + ctx + '"')
                    + r'\s*,\s*"' + re.escape(literal) + r'"\s*\)', text))
                n = max(n, 1)
            final[(path, literal, tf)] = n

        # tr() 形态（call / bare）按"最终包裹总数"归一
        tr_forms = call_forms + (['bare'] if has_bare else [])
        if not tr_forms:
            continue
        tr_total = max(tr_total, 1)
        if call_forms and has_bare:
            # 两种形态并存：各记 total 次，重放时按需补足，天然幂等
            for cf in call_forms:
                final[(path, literal, cf)] = tr_total
            final[(path, literal, 'bare')] = tr_total
        elif call_forms:
            for cf in call_forms:
                final[(path, literal, cf)] = tr_total
        else:
            final[(path, literal, 'bare')] = tr_total

    return final, per_file


def write_rules(rules, out_path):
    lines = [
        "# IQmol3 汉化 tr() 包裹规则表（由 extract_tr_rules.py 自动生成，请勿手改）",
        "#",
        "# 格式: <相对路径>\\t<字面量>\\t<形态>\\t<出现次数>",
        "#   形态 = call:<函数名>      →  重放为 <函数名>(tr(\"字面量\"))",
        "#   形态 = bare               →  重放为 tr(\"字面量\")",
        "#   形态 = translate:<上下文>  →  重放为 QCoreApplication::translate(\"<上下文>\", \"字面量\")",
        "#                                 （非 QObject 类没有 tr()，只能用静态翻译）",
        "#   出现次数 = 该字面量在该文件中【最终应被包裹的总数】",
        "#              （注意：上游自带的 tr() 也计入其中）",
        "# 同一字面量可同时出现多行（形态不同），例如 MainWindow.C 的 Save：",
        "#     Save\\tcall:messageBox.addButton  ← messageBox.addButton(tr(\"Save\"), ...)",
        "#     Save\\tbare                      ← name = tr(\"Save\");",
        "# 重放由 replay_tr.py 执行，幂等：已包裹的不会被二次包裹。",
        "#",
        "# ---------------------------------------------------------------",
        "# 已知例外：以下 6 个文件的改动【超出机械包裹范围】，本规则表无法完整重放，",
        "# 上游升级后需人工核对（详见 docs/第三层-重放机制说明.md §4.1/§4.2）：",
        "#",
        "#   [拼接 → 占位符重构] 目的是让 Qt 翻译系统能处理变量插值",
        "#     src/Configurator/ConstraintConfigurator.C",
        "#     src/Configurator/MullikenDecompositionsDialog.C",
        "#     src/Configurator/SurfaceAnimatorDialog.C",
        "#     src/Layer/GeminalOrbitalsLayer.C",
        "#     src/Qui/GeometryConstraint.C        （跨行字符串拼接）",
        "#",
        "#   [常量 → 可翻译字面量替换]",
        "#     src/Layer/MoleculeLayer.C           （DefaultMoleculeName → \"Untitled\"）",
        "#",
        "# 注：src/Viewer/UndoCommands.C 曾属例外，现由 translate:<上下文> 形态覆盖，",
        "#     残余差异仅 1 行（同上『拼接 → 占位符重构』类）。",
        "# 其余 30 个文件可由本规则表 100% 精确重放。",
        "# ---------------------------------------------------------------",
        "#",
        "# 另注：以下 6 个文件相对上游有改动但【不含任何翻译包裹】，属功能性补丁，",
        "# 需用 patches/功能补丁-语言支持.patch 单独重放（upstream 干净应用已验证）：",
        "#     src/Main/IQmolApplication.C / .h    （loadTranslations 语言加载）",
        "#     src/Main/PreferencesBrowser.C       （语言下拉框绑定）",
        "#     src/Util/Preferences.C / .h         （Language 偏好存取）",
        "#     src/Layer/OctreeLayer.C             （#include <cstdint>，GCC15 兼容）",
        "# ---------------------------------------------------------------",
        "#",
    ]
    n = 0
    for (path, literal, form), count in sorted(rules.items()):
        if '\t' in literal or '\n' in literal or '"' in literal:
            continue      # TSV 安全 + 含转义引号的暂不支持
        lines.append(f"{path}\t{literal}\t{form}\t{count}")
        n += 1
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')
    return n


def verify(base, rules):
    ok = miss = 0
    missing = []
    covered = {(p, l) for (p, l, _f) in rules}
    for path in changed_source_files(base):
        for body in _added_lines(base, path):
            # 形态 3：QCoreApplication::translate("Ctx", "X")
            t_spans = []
            for m in QT_TRANSLATE_RE.finditer(body):
                t_spans.append(m.span())
                literal = m.group(2)
                if (path, literal) in covered:
                    ok += 1
                else:
                    miss += 1
                    missing.append(f'{path}: QCoreApplication::translate("{m.group(1)}", "{literal}")')
            # 形态 1/2：tr("X")
            for m in ANY_TR_RE.finditer(body):
                if any(s <= m.start() < e for s, e in t_spans):
                    continue
                literal = m.group(1)
                if (path, literal) in covered:
                    ok += 1
                else:
                    miss += 1
                    missing.append(f'{path}: tr("{literal}")')
    return ok, miss, missing


def main():
    ap = argparse.ArgumentParser(description='从 diff 反向提取 tr() 包裹规则')
    ap.add_argument('--base', default='af7ff60', help='对比基线提交（默认 af7ff60）')
    ap.add_argument('--out', default=os.path.join(REPO, 'scripts/i18n/wrap_tr.rules'))
    ap.add_argument('--verify', action='store_true', help='只校验覆盖率，不写文件')
    args = ap.parse_args()

    rules, per_file = extract(args.base)
    if not rules:
        print(f"未从 {args.base}..HEAD 提取到任何 tr() 包裹，请检查基线。")
        return 1

    if args.verify:
        ok, miss, missing = verify(args.base, rules)
        print(f"规则条数      : {len(rules)}")
        print(f"覆盖文件数    : {len(per_file)}")
        print(f"diff 中 tr()  : {ok + miss}")
        print(f"被规则覆盖    : {ok}")
        print(f"未覆盖        : {miss}")
        if missing:
            print("\n未覆盖明细（前 20 条）:")
            for m in missing[:20]:
                print("  " + m)
            return 1
        print("\n✅ 覆盖率 100%：规则表可完整重放现有 tr() 成果。")
        return 0

    n = write_rules(rules, args.out)
    print(f"已写入 {args.out}")
    print(f"  文件数: {len(per_file)}")
    print(f"  规则数: {n}")
    print("\nTop 8 文件:")
    for p, c in per_file.most_common(8):
        print(f"  {c:4d}  {p}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
