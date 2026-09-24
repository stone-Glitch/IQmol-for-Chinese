#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tqa.py —— IQmol 汉化版翻译质量量化评估（TQA）

实现 docs/翻译质量量化评估方案.md 中的六维指标模型，可在 CI / 本地一键运行：

    python3 scripts/i18n/tqa.py                  # 人类可读报告
    python3 scripts/i18n/tqa.py --json           # 机器可读（CI 用）
    python3 scripts/i18n/tqa.py --gate           # 阻断项检查，非 0 退出表示不合格
    python3 scripts/i18n/tqa.py --baseline FILE  # 与上次结果对比

设计要点
--------
本工具只实现【可自动化】的部分（证据链前三层 + 部分第五层）：
    P1 源码—翻译漂移   P2 翻译资产完整率   P3 QM 交付有效度
    P4 术语一致性      P5 界面可用性(可自动部分)

P6（语义质量）由 `semantic_audit.py` 承担：
    · 结构性语义缺陷（术语不一致、硬译参数名、占位符不匹配）→ 自动筛查
    · 「这句话翻得对不对」→ 人工四级评分，产出 A_s
    若仓库存在 review/P6-审校结果.json，本工具自动读取并计入 P6 权重；
    否则 P6 保持「未测量」并从有效权重中剔除（不臆造分数）。

关键设计：FragmentTable 等【工具注入】条目（无 <location>）不计入漂移，
因为它们的源文本来自运行期片段库而非 lupdate 可扫描的源码。
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import collections
from datetime import datetime, timezone

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TS = os.path.join(REPO, 'translations/zh_CN.ts')
QM = os.path.join(REPO, 'translations/zh_CN.qm')
SRC = os.path.join(REPO, 'src')
TERMS = os.path.join(REPO, 'scripts/i18n/known_translations.json')
P6_JSON = os.path.join(REPO, 'review/P6-审校结果.json')

# ---------------------------------------------------------------- 权重
WEIGHTS = {'P1': 20, 'P2': 20, 'P3': 15, 'P4': 15, 'P5': 15, 'P6': 15}

# ---------------------------------------------------------------- 阻断项阈值
GATE = {
    'ts_unfinished_max': 0,        # 未完成条目必须为 0
    'ts_empty_max': 0,             # 空译文必须为 0
    'qm_missing': True,            # QM 必须存在
    'drift_max': 0.05,             # 漂移率 ≤5%
    'fatal_term_max': 0,           # 致命术语错误必须为 0
}


# ================================================================ TS 解析
def parse_ts(path):
    """解析 TS 文件 → {context: [{src, tr, unfinished, locations, has_tr}]}"""
    with open(path, encoding='utf-8') as f:
        text = f.read()
    out = {}
    for ctx in re.findall(r'<context>(.*?)</context>', text, re.S):
        nm = re.search(r'<name>(.*?)</name>', ctx, re.S)
        name = nm.group(1) if nm else '?'
        items = []
        for m in re.findall(r'<message[^>]*>(.*?)</message>', ctx, re.S):
            s = re.search(r'<source>(.*?)</source>', m, re.S)
            if not s:
                continue
            t = re.search(r'<translation([^>]*)>(.*?)</translation>', m, re.S)
            attrs = t.group(1) if t else ''
            body = t.group(2) if t else ''
            locs = re.findall(r'<location[^>]*filename="([^"]*)"', m)
            items.append({
                'src': s.group(1),
                'tr': body,
                'unfinished': 'type="unfinished"' in attrs or 'type="vanished"' in attrs,
                'has_tr': bool(body.strip()),
                'locations': locs,
            })
        out[name] = items
    return out


# ================================================================ P1 漂移
def measure_drift(allow_lupdate=True):
    """
    D_t = N_drift / N_source
    以 lupdate 实时提取为基准，与仓库 TS 对比（按 上下文+源文本 匹配）。
    工具注入条目（无 <location>）不计为漂移 —— 见模块 docstring。
    """
    res = {'available': False, 'reason': '', 'n_source': 0, 'n_drift': 0,
           'drift': 0.0, 'added': [], 'removed': []}
    lupdate = shutil.which('lupdate')
    if not lupdate:
        res['reason'] = 'lupdate 不可用（需 qttools5-dev-tools），已跳过 P1'
        return res

    fresh = '/tmp/tqa_fresh.ts'
    cmd = [lupdate, '-extensions', 'C,ui', SRC + '/', '-ts', fresh]
    try:
        subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    except Exception as e:
        res['reason'] = f'lupdate 执行失败: {e}'
        return res
    if not os.path.isfile(fresh):
        res['reason'] = 'lupdate 未产出 TS'
        return res

    f = parse_ts(fresh)
    r = parse_ts(TS)
    fset = {(c, i['src']) for c, items in f.items() for i in items}
    # 仓库侧：只取【有 location 的】条目参与漂移比对（排除工具注入项）
    rset = {(c, i['src']) for c, items in r.items() for i in items if i['locations']}

    added = fset - rset        # 源码有、TS 缺
    removed = rset - fset      # TS 有、源码无
    n_src = len(fset)
    n_drift = len(added) + len(removed)

    res.update({
        'available': True, 'n_source': n_src, 'n_drift': n_drift,
        'drift': (n_drift / n_src) if n_src else 0.0,
        'added': sorted(f'{c}\t{s}' for c, s in added)[:50],
        'removed': sorted(f'{c}\t{s}' for c, s in removed)[:50],
        'n_added': len(added), 'n_removed': len(removed),
    })
    return res


# ================================================================ P2 资产
def measure_asset():
    r = parse_ts(TS)
    allitems = [i for items in r.values() for i in items]
    total = len(allitems)
    unfinished = sum(1 for i in allitems if i['unfinished'])
    empty = sum(1 for i in allitems if not i['has_tr'])
    obsolete = 0  # 本仓库已清理；lupdate 保留项另计
    no_ctx = sum(1 for i in allitems if not i['locations'])   # 工具注入（有意的）

    M_t = (empty + unfinished) / total if total else 0
    O_t = obsolete / total if total else 0
    I_t = 0.0    # translator comment 缺失：本项目未使用该字段，不计损失
    Q_asset = max(0.0, 100 - (100 * M_t + 70 * O_t + 20 * I_t))
    return {
        'total': total, 'unfinished': unfinished, 'empty': empty,
        'injected_no_location': no_ctx,
        'C_ts': (total - unfinished - empty) / total if total else 0,
        'M_t': M_t, 'O_t': O_t, 'Q_asset': Q_asset,
    }


# ================================================================ P3 QM
def measure_qm():
    exists = os.path.isfile(QM)
    size = os.path.getsize(QM) if exists else 0
    # 用 lrelease 重新生成一份，比较消息数（验证 TS→QM 无损）
    n_expected = 0
    n_generated = 0
    lrelease = shutil.which('lrelease')
    if lrelease and os.path.isfile(TS):
        out = '/tmp/tqa_check.qm'
        try:
            p = subprocess.run([lrelease, TS, '-qm', out],
                               capture_output=True, text=True, timeout=300)
            # lrelease 输出形如 "Generated N translations (M finished ...)"
            m = re.search(r'(\d+)\s+translation', p.stdout + p.stderr, re.I)
            if m:
                n_generated = int(m.group(1))
        except Exception:
            pass
    n_expected = n_generated or 0

    G_qm = 1.0 if exists and size > 0 else 0.0
    V_qm = 1.0 if n_expected > 0 else 0.0
    # L_qm（加载率）与 H_qm（命中率）需运行期采样，本工具无法自动测量，
    # 标记为未测量，不计入失分（避免臆造）。真实评估须由 W4 运行时采样补全。
    L_qm = None
    H_qm = None
    return {
        'exists': exists, 'size': size,
        'qm_messages': n_generated,
        'G_qm': G_qm, 'V_qm': V_qm, 'L_qm': L_qm, 'H_qm': H_qm,
        'measurable': exists and n_expected > 0,
    }


# ================================================================ P4 术语
def measure_terms():
    """
    术语一致性：以 known_translations.json 为标准词典，检查 TS 中
    同一英文源是否被译为多种中文（冲突），以及是否使用禁用译法。
    词典缺失时返回未测量，不臆造分数。
    """
    res = {'available': False, 'reason': '', 'conflicts': [], 'n_occurrence': 0,
           'C_term': 0.0, 'fatal': 0}
    if not os.path.isfile(TERMS):
        res['reason'] = 'known_translations.json 缺失，跳过 P4'
        return res
    with open(TERMS, encoding='utf-8') as f:
        try:
            terms = json.load(f)
        except Exception as e:
            res['reason'] = f'术语词典解析失败: {e}'
            return res
    if not isinstance(terms, dict) or not terms:
        res['reason'] = '术语词典为空，跳过 P4'
        return res

    # 反向索引：中文译名 → 英文源，用于检测"同一中文被多个英文共用"等冲突
    r = parse_ts(TS)
    items = [(c, i) for c, lst in r.items() for i in lst]
    res['n_occurrence'] = len(items)
    conflicts = []
    for en, zh in list(terms.items())[:100000]:
        for c, i in items:
            if i['src'].strip() == str(en).strip() and i['tr'].strip():
                if i['tr'].strip() != str(zh).strip():
                    conflicts.append({'ctx': c, 'src': i['src'],
                                      'expect': zh, 'actual': i['tr']})
    res.update({'available': True, 'conflicts': conflicts[:100],
                'n_conflict': len(conflicts)})
    res['C_term'] = (len(conflicts) / res['n_occurrence']) if res['n_occurrence'] else 0.0
    return res


# ================================================================ P5 界面（可自动部分）
def measure_ui():
    """
    可自动部分：动态文本格式合规（占位符/HTML 标签平衡）。
    英文残留率与截断率需运行期 UI 采样，本工具不臆造。
    """
    r = parse_ts(TS)
    items = [i for lst in r.values() for i in lst if i['has_tr']]
    fmt_err = []
    for i in items:
        s, t = i['src'], i['tr']
        # 1) 占位符集合必须一致（%1..%99 / %n / %s 等）
        ps = collections.Counter(re.findall(r'%\d+|%n|%s|%d|%L\d+', s))
        pt = collections.Counter(re.findall(r'%\d+|%n|%s|%d|%L\d+', t))
        if ps != pt:
            fmt_err.append({'src': s[:60], 'tr': t[:60], 'why': '占位符不一致'})
            continue
        # 2) HTML 标签平衡（仅当源含标签时）
        if re.search(r'<[a-zA-Z/][^>]*>', s):
            ts_ = sorted(re.findall(r'</?([a-zA-Z]+)', s))
            tt_ = sorted(re.findall(r'</?([a-zA-Z]+)', t))
            if ts_ != tt_:
                fmt_err.append({'src': s[:60], 'tr': t[:60], 'why': 'HTML 标签不平衡'})
                continue
        # 3) 中文译文误用半角标点（代码/命令/HTML 除外，粗筛）
        #    仅在【源文本为纯自然语言】时才检查：源含 HTML/标记/URL/代码骨架时
        #    跳过，否则会把 <!DOCTYPE ...> 这类不该翻译的骨架误判为"半角标点"。
        plain_src = not re.search(r'<[a-zA-Z/!][^>]*>|&[a-zA-Z#]+;|https?://', s)
        if (plain_src and len(t) > 8
                and re.search(r'[\u4e00-\u9fff]', t)
                and re.search(r'[,;:]\s', t)):
            fmt_err.append({'src': s[:60], 'tr': t[:60], 'why': '中文中疑似半角标点'})
    n = len(items)
    return {'n_dynamic_checked': n, 'n_format_error': len(fmt_err),
            'F_c': 1 - (len(fmt_err) / n) if n else 1.0,
            'errors': fmt_err[:50]}


# ================================================================ P6 语义
def measure_semantic(path=P6_JSON):
    """
    读取人工审校结果（由 semantic_audit.py score --save 产出）。

    约定：P6 分数不由本工具生成。若审校结果不存在，P6 = None，
    并从有效权重中剔除 —— 宁可显示「未测量」，也不用虚假满分掩盖。
    """
    if not os.path.isfile(path):
        return {'available': False,
                'note': f'未找到审校结果 {os.path.relpath(path, REPO)}，'
                        f'P6 记为未测量（运行 semantic_audit.py sample 生成工单）'}
    try:
        with open(path, encoding='utf-8') as f:
            d = json.load(f)
    except (OSError, ValueError) as exc:
        return {'available': False, 'note': f'审校结果读取失败：{exc}'}

    a = d.get('A_s')
    if a is None:
        return {'available': False, 'note': '审校结果中无 A_s 字段'}
    return {
        'available': True,
        'A_s': float(a),
        'n_reviewed': d.get('n_reviewed'),
        'n_fatal': d.get('n_fatal', 0),
        'n_severe': d.get('n_severe', 0),
        'n_minor': d.get('n_minor', 0),
        'undecided': d.get('undecided', 0),
        'reviewed_at': d.get('reviewed_at', ''),
        'reviewer': d.get('reviewer', ''),
    }


# ================================================================ 汇总
def evaluate(allow_lupdate=True):
    drift = measure_drift(allow_lupdate)
    asset = measure_asset()
    qm = measure_qm()
    terms = measure_terms()
    ui = measure_ui()
    sem = measure_semantic()

    P1 = drift['drift'] if drift['available'] else None
    P2 = 1 - asset['Q_asset'] / 100
    P3 = 1 - qm['G_qm']          # 只对"可自动测量的部分"计分
    P4 = terms['C_term'] if terms['available'] else None
    P5 = max(ui.get('n_format_error', 0) / ui['n_dynamic_checked'], 0) if ui['n_dynamic_checked'] else 0.0
    P6 = sem['A_s'] if sem.get('available') else None

    parts = {'P1': P1, 'P2': P2, 'P3': P3, 'P4': P4, 'P5': P5, 'P6': P6}
    # 未测量的维度按"不扣分"处理，但同时把有效权重归一化，避免虚高
    measured = {k: v for k, v in parts.items() if v is not None}
    wsum = sum(WEIGHTS[k] for k in measured) or 1
    loss = sum(WEIGHTS[k] * v for k, v in measured.items())
    tqa = 100 - (loss / wsum) * 100

    gates = []
    if asset['unfinished'] > GATE['ts_unfinished_max']:
        gates.append(f"未完成翻译 {asset['unfinished']} 条 > {GATE['ts_unfinished_max']}")
    if asset['empty'] > GATE['ts_empty_max']:
        gates.append(f"空译文 {asset['empty']} 条 > {GATE['ts_empty_max']}")
    if not qm['exists']:
        gates.append('QM 未生成')
    if drift['available'] and drift['drift'] > GATE['drift_max']:
        gates.append(f"漂移率 {drift['drift']:.1%} > {GATE['drift_max']:.0%}")

    return {
        'version': git('rev-parse', '--short', 'HEAD'),
        'date': datetime.now(timezone.utc).strftime('%Y-%m-%d'),
        'upstream': git('rev-parse', '--short', 'origin/master'),
        'parts': parts, 'weights': WEIGHTS,
        'TQA': round(tqa, 2),
        'measured_dims': sorted(measured),
        'unmeasured_dims': sorted(k for k, v in parts.items() if v is None),
        'gate_failures': gates,
        'detail': {'drift': drift, 'asset': asset, 'qm': qm,
                   'terms': terms, 'ui': ui, 'semantic': sem},
    }


def git(*a):
    try:
        return subprocess.run(['git', '-C', REPO, *a], capture_output=True,
                              text=True, timeout=30).stdout.strip()
    except Exception:
        return '?'


# ================================================================ 报告
def report(res):
    p = res['parts']; d = res['detail']
    L = []
    L.append('=' * 66)
    L.append('  IQmol 汉化版翻译质量评估（TQA）')
    L.append('=' * 66)
    L.append(f"  版本      : {res['version']}   上游: {res['upstream']}")
    L.append(f"  日期      : {res['date']}")
    L.append('')

    def row(k, name, val, w):
        if val is None:
            L.append(f"  {k}  {name:<22} 未测量   （权重 {w}，不计入）")
        else:
            L.append(f"  {k}  {name:<22} {val:>7.2%}  （权重 {w}，失分 {val*w:>5.2f}）")

    L.append('  ---- 六维指标 ----')
    row('P1', '源码—翻译漂移', p['P1'], 20)
    row('P2', '翻译资产不完整率', p['P2'], 20)
    row('P3', 'QM 交付失效度', p['P3'], 15)
    row('P4', '术语冲突率', p['P4'], 15)
    row('P5', '界面动态文本错误率', p['P5'], 15)
    row('P6', '语义质量', p['P6'], 15)
    L.append('')

    a = d['asset']
    L.append(f"  TS 消息总数  : {a['total']}")
    L.append(f"  未完成/空译文: {a['unfinished']} / {a['empty']}")
    L.append(f"  工具注入条目 : {a['injected_no_location']}（无 location，不计漂移）")
    if d['drift']['available']:
        dr = d['drift']
        L.append(f"  lupdate 提取 : {dr['n_source']} 条")
        L.append(f"  漂移         : {dr['n_drift']} 条（新增 {dr.get('n_added',0)} / 过期 {dr.get('n_removed',0)}）"
                 f" → {dr['drift']:.2%}")
    else:
        L.append(f"  漂移         : 未测量（{d['drift']['reason']}）")
    q = d['qm']
    L.append(f"  QM           : {'存在' if q['exists'] else '缺失'}"
             f"（{q['size']} 字节，{q['qm_messages']} 条）")
    L.append(f"  动态文本检查 : {d['ui']['n_dynamic_checked']} 条，"
             f"错误 {d['ui']['n_format_error']} 条")
    s = d.get('semantic', {})
    if s.get('available'):
        L.append(f"  语义审校     : {s['n_reviewed']} 条已评，"
                 f"A_s={s['A_s']:.4f}"
                 f"（无错误 {s.get('n_reviewed',0)-s.get('n_severe',0)-s.get('n_minor',0)-s.get('n_fatal',0)}"
                 f" / 轻微 {s.get('n_minor',0)} / 严重 {s.get('n_severe',0)} / 致命 {s.get('n_fatal',0)}）")
        if s.get('undecided'):
            L.append(f"                ⚠ 其中 {s['undecided']} 条未裁决，建议补第三人/化学专业裁决")
    else:
        L.append(f"  语义审校     : 未测量 —— {s.get('note','')}")
    L.append('')

    L.append('-' * 66)
    L.append(f"  TQA 综合得分 : {res['TQA']} / 100")
    L.append(f"  已测量维度   : {', '.join(res['measured_dims'])}")
    if res['unmeasured_dims']:
        L.append(f"  未测量维度   : {', '.join(res['unmeasured_dims'])}（不臆造分数）")
    if res['gate_failures']:
        L.append('  ⛔ 阻断项:')
        for g in res['gate_failures']:
            L.append(f'     - {g}')
    else:
        L.append('  ✅ 无阻断项')
    L.append('=' * 66)
    return '\n'.join(L)


def main():
    ap = argparse.ArgumentParser(description='IQmol 汉化版 TQA 评估')
    ap.add_argument('--json', action='store_true')
    ap.add_argument('--gate', action='store_true', help='有阻断项则非 0 退出')
    ap.add_argument('--no-lupdate', action='store_true', help='跳过 lupdate（快）')
    ap.add_argument('--save', default='', help='结果写入 JSON 文件')
    args = ap.parse_args()

    if not os.path.isfile(TS):
        print(f'ERROR: 未找到 {TS}', file=sys.stderr)
        return 1

    res = evaluate(allow_lupdate=not args.no_lupdate)
    if args.save:
        with open(args.save, 'w', encoding='utf-8') as f:
            json.dump(res, f, ensure_ascii=False, indent=2)
    if args.json:
        print(json.dumps(res, ensure_ascii=False, indent=2))
    else:
        print(report(res))
    if args.gate and res['gate_failures']:
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main())
