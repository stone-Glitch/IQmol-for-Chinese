#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
context_reach.py —— Qt 翻译上下文可达性检查（lupdate 基准 + 运行时探针）

要解决的问题
------------
Qt 运行时按 context 查译文：

    tr("File")  ->  用「类名」作 context 去 .qm 里找

如果 .ts 里的 context 与运行时不一致，译文**存在但永远查不到**，
界面保持英文。而所有常规检查都看不出来：

  - lupdate 提取：正常（它提取到了）
  - TQA P1 漂移  ：0（源码没变）
  - TQA P2 完整率：0（条目都有译文）
  - TQA P3 QM    ：正常（.qm 里确实有这条）

本项目实际遇到过这个坑（见 2026-09-24 排查记录）：截图里
Q-Chem Input File Editor 的菜单栏显示 File/Edit/Job/Font 英文，
而同一窗口的 .ui 控件却是中文。

排查方法（本工具）
------------------
第一版曾用「读源码推断 context」的静态方法，**产生了大量误报**：
它给出 `Gmx::MainWindow`、`Layer::Molecule` 这类运行时根本不存在的
context，而实测发现 `IQmol::MainWindow` 是好的。

根因是 C++ 文件里 namespace 块的位置、前向声明、注释里的 namespace
字样都会干扰静态推断。**静态推断不可靠，必须用 lupdate 的输出作基准。**

正确方法：
  1. 跑 lupdate 生成基准 .ts —— 它写进去的 context 就是运行时会用的
     （已用 ctxprobe.C 实测验证）
  2. 把仓库 .ts 与基准 .ts 逐 context/逐条目比对，找缺失与空译文
  3. 需要验证某个 context 在 .qm 里到底能不能命中，用 ctxprobe 实测

用法
----
    # 1) 基准比对（默认，跑 lupdate）
    python3 scripts/i18n/context_reach.py

    # 2) 复用已有基准，避免重复跑 lupdate
    python3 scripts/i18n/context_reach.py --baseline /tmp/tqa_fresh.ts

    # 3) 只做 .qm 运行时探针（需先编译 ctxprobe，见 build_ctxprobe.sh）
    python3 scripts/i18n/context_reach.py --probe translations/zh_CN.qm

退出码：0 全部覆盖；1 存在缺失
"""
import argparse
import collections
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TS = os.path.join(REPO, 'translations', 'zh_CN.ts')
SRC = os.path.join(REPO, 'src')
PROBE_SRC = os.path.join(REPO, 'scripts', 'i18n', 'ctxprobe.C')


# ------------------------------------------------------------------ 解析
def load_ts(path):
    """
    → {context: {source: translation 或 None}}
    translation 为 None 表示该条目没有 <translation> 元素。
    """
    out = collections.defaultdict(dict)
    txt = open(path, encoding='utf-8', errors='ignore').read()
    for cm in re.finditer(r'<context>(.*?)</context>', txt, re.S):
        blk = cm.group(1)
        nm = re.search(r'<name>(.*?)</name>', blk)
        if not nm:
            continue
        ctx = nm.group(1)
        for mm in re.finditer(r'<message[^>]*>(.*?)</message>', blk, re.S):
            b = mm.group(1)
            sm = re.search(r'<source>(.*?)</source>', b, re.S)
            if not sm:
                continue
            tm = re.search(r'<translation([^>]*)>(.*?)</translation>', b, re.S)
            out[ctx][sm.group(1)] = (tm.group(2) if tm else None)
    return out


def run_lupdate(out_path):
    """
    用 lupdate 生成基准 .ts。
    以 src/ 下的源文件与 .ui 为输入 —— lupdate 写出的 context
    即运行时 QTranslator 查询时使用的 context（已实测验证）。
    """
    exe = shutil.which('lupdate') or '/usr/lib/qt5/bin/lupdate'
    if not os.path.isfile(exe) and not shutil.which('lupdate'):
        return None, 'lupdate 不可用'
    # 收集源文件（.C/.h/.ui）
    files = []
    for root, dirs, fs in os.walk(SRC):
        for f in fs:
            if f.endswith(('.C', '.h', '.ui')):
                files.append(os.path.join(root, f))
    if not files:
        return None, 'src/ 下没有可扫描的源文件'
    cmd = [exe, '-no-obsolete', '-silent'] + files + ['-ts', out_path]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    except Exception as e:                       # noqa: BLE001
        return None, f'lupdate 执行失败: {e}'
    if not os.path.isfile(out_path):
        return None, f'lupdate 未产出文件（rc={r.returncode}）'
    return out_path, None


# ------------------------------------------------------------------ 比对
def compare(base_path, repo_path):
    """→ (summary, per_context, samples)"""
    B = load_ts(base_path)
    R = load_ts(repo_path)

    need = 0
    missing_ctx = collections.Counter()
    empty_ctx = collections.Counter()
    samples = collections.defaultdict(list)
    extra_ctx = [c for c in R if c not in B]

    for ctx, items in B.items():
        have = R.get(ctx, {})
        for src in items:
            need += 1
            if src not in have:
                missing_ctx[ctx] += 1
                if len(samples[ctx]) < 8:
                    samples[ctx].append(src)
            elif not have[src]:
                empty_ctx[ctx] += 1
                if len(samples[ctx]) < 8:
                    samples[ctx].append(f'{src}（译文为空）')

    summary = {
        'baseline_contexts': len(B),
        'baseline_entries': need,
        'repo_contexts': len(R),
        'repo_entries': sum(len(v) for v in R.values()),
        'missing': sum(missing_ctx.values()),
        'empty': sum(empty_ctx.values()),
        'contexts_with_gap': len(set(missing_ctx) | set(empty_ctx)),
        'extra_contexts_in_repo': len(extra_ctx),
    }
    per_ctx = {}
    for c in sorted(set(missing_ctx) | set(empty_ctx)):
        per_ctx[c] = {'missing': missing_ctx.get(c, 0),
                      'empty': empty_ctx.get(c, 0)}
    return summary, per_ctx, samples, extra_ctx


# ------------------------------------------------------------------ 探针
def build_probe(workdir):
    """编译 ctxprobe。→ (可执行路径, 错误信息)"""
    exe = os.path.join(workdir, 'ctxprobe')
    if os.path.isfile(exe):
        return exe, None
    if not os.path.isfile(PROBE_SRC):
        return None, f'缺少 {os.path.relpath(PROBE_SRC, REPO)}'
    try:
        flags = subprocess.run(
            ['pkg-config', '--cflags', '--libs', 'Qt5Core'],
            capture_output=True, text=True, timeout=30)
        extra = flags.stdout.split() if flags.returncode == 0 else []
        cmd = ['g++', '-o', exe, PROBE_SRC, '-fPIC'] + extra
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    except Exception as e:                       # noqa: BLE001
        return None, f'编译失败: {e}'
    if not os.path.isfile(exe):
        return None, f'编译失败:\n{r.stderr[:800]}'
    return exe, None


def run_probe(qm_path, probes):
    """用真实 QTranslator 查询 (context, source) → [(ctx, src, 译文或None)]"""
    workdir = tempfile.mkdtemp(prefix='ctxprobe_')
    exe, err = build_probe(workdir)
    if not exe:
        return None, err
    args = [exe, qm_path] + [f'{c}\t{s}' for c, s in probes]
    try:
        r = subprocess.run(args, capture_output=True, text=True, timeout=120)
    except Exception as e:                       # noqa: BLE001
        return None, f'探针执行失败: {e}'
    out = []
    for line in r.stdout.splitlines():
        # 格式: context<空白>source<两空格以上>结果
        m = re.match(r'^(\S+)\s+(.+?)\s{2,}(✅.*|❌.*)$', line)
        if m:
            out.append((m.group(1), m.group(2).strip(), m.group(3)))
    if not out:
        return None, f'探针无输出:\n{r.stdout[:500]}\n{r.stderr[:500]}'
    return out, None


# ------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--baseline', metavar='TS',
                    help='复用已有 lupdate 基准 .ts（默认现场生成）')
    ap.add_argument('--probe', metavar='QM',
                    help='对 .qm 做运行时 context 探针实测')
    ap.add_argument('--json', metavar='OUT')
    ap.add_argument('--show', type=int, default=15,
                    help='最多显示多少个有缺口的 context')
    args = ap.parse_args()

    rc = 0

    if args.probe:
        qm = args.probe
        if not os.path.isfile(qm):
            print(f'找不到 {qm}', file=sys.stderr)
            return 2
        # 取每个 context 的第一条做探针
        R = load_ts(TS)
        probes = []
        for ctx, items in list(R.items())[:40]:
            for src in list(items)[:1]:
                probes.append((ctx, src))
        res, err = run_probe(qm, probes)
        print('=' * 72)
        print('  .qm 运行时 context 探针（真实 QTranslator 查询）')
        print('=' * 72)
        print(f'  被测 .qm: {qm}')
        if err:
            print(f'  ❌ {err}')
            return 2
        bad = [t for t in res if not t[2].startswith('✅')]
        print(f'  探测 {len(res)} 个 context，未命中 {len(bad)} 个')
        print()
        for ctx, src, hit in res:
            if hit.startswith('✅'):
                continue
            print(f'    ❌ {ctx:42} {src[:28]!r}  {hit}')
        if not bad:
            print('  ✅ 全部命中')
        return 0

    # ---- 基准比对
    baseline = args.baseline
    tmp = None
    if not baseline:
        tmp = tempfile.mktemp(suffix='.ts')
        baseline, err = run_lupdate(tmp)
        if err:
            print(f'lupdate 不可用（{err}）。', file=sys.stderr)
            print('可加 --baseline <已有.ts> 复用基准。', file=sys.stderr)
            return 2

    summary, per_ctx, samples, extra = compare(baseline, TS)

    print('=' * 72)
    print('  Qt 翻译上下文可达性检查（基准 = lupdate 输出）')
    print('=' * 72)
    print(f'  基准 .ts      : {baseline}')
    print(f'  基准 context  : {summary["baseline_contexts"]}'
          f'   条目 {summary["baseline_entries"]}')
    print(f'  仓库 context  : {summary["repo_contexts"]}'
          f'   条目 {summary["repo_entries"]}')
    print(f'  仓库独有 context: {summary["extra_contexts_in_repo"]}'
          f'（工具注入条目，属正常）')
    print()
    print(f'  ❌ 完全缺失条目: {summary["missing"]}')
    print(f'  ❌ 译文为空条目: {summary["empty"]}')
    print(f'  ❌ 存在缺口的 context: {summary["contexts_with_gap"]}')
    print()

    if summary['contexts_with_gap']:
        rc = 1
        print('-' * 72)
        print('  ⚠️  以下 context 存在缺失（运行时将回退英文）')
        print('-' * 72)
        for ctx in list(per_ctx)[:args.show]:
            d = per_ctx[ctx]
            print(f'\n  {ctx}')
            print(f'      缺失 {d["missing"]}   空译文 {d["empty"]}')
            for s in samples.get(ctx, [])[:5]:
                print(f'        - {s[:66]!r}')
    else:
        print('  ✅ lupdate 需要的全部条目均已覆盖且非空')

    if tmp and os.path.isfile(tmp):
        os.remove(tmp)

    if args.json:
        with open(args.json, 'w', encoding='utf-8') as f:
            json.dump({'summary': summary, 'per_context': per_ctx},
                      f, ensure_ascii=False, indent=2)
        print(f'\n  → 已落盘 {args.json}')

    return rc


if __name__ == '__main__':
    raise SystemExit(main())
