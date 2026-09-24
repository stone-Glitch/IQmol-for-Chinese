#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
semantic_audit.py —— P6 语义质量审校工具链

设计立场
--------
P6（语义质量）在 TQA 模型里被标注为「需人工」。这个判断**只对了一半**：

  · 真正的「这句话翻得对不对」——需要人判断，脚本无权代劳；
  · 但相当一部分语义缺陷是**可自动检测的结构性问题**——术语不一致、
    参数名硬译、占位符不匹配、中英夹杂不当。把这些交给脚本，
    人工审校就能聚焦在真正需要判断的地方。

因此本工具做三件事：

  1. **自动筛查（scan）**：找出结构性语义缺陷，产出待审清单
  2. **分层抽样（sample）**：按风险维度分层，产出人工审校工单
  3. **评分汇总（score）**：消费人工审校记录，算 A_s 并回填 tqa.py 的 P6 槽位

四级错误评分（与 TQA 模型一致）
------------------------------
  0   无错误   准确、清晰、符合上下文
  1   轻微     表达不自然，不影响操作
  10  严重     含义明显偏差，可能造成理解困难
  100 致命     可能造成错误参数选择或操作风险

A_s 计算
--------
  A_s = Σ(score_i) / Σ(weight_i × 100)     —— 归一化到 [0,1] 的语义损失率
  其中 weight_i 为该条目的风险权重（高风险条目权重更高）
  致命级（score=100）单独统计，>0 即阻断发布

用法
----
    # 自动筛查结构性语义缺陷
    python3 scripts/i18n/semantic_audit.py scan

    # 分层抽样，生成人工审校工单（CSV + Markdown）
    python3 scripts/i18n/semantic_audit.py sample --size 240

    # 消费已填写的审校记录，算 A_s
    python3 scripts/i18n/semantic_audit.py score review/审校记录.csv
"""
import argparse
import csv
import json
import os
import random
import re
import sys
from collections import defaultdict

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TS = os.path.join(REPO, 'translations/zh_CN.ts')

CJK = re.compile(r'[\u4e00-\u9fff]')
LATIN_WORD = re.compile(r'[A-Za-z]{3,}')


# ================================================================ TS 解析
def load_ts(path=TS):
    """→ [{ctx, src, tr, has_location, index}]"""
    with open(path, encoding='utf-8') as f:
        text = f.read()
    out = []
    for cm in re.finditer(r'<context>(.*?)</context>', text, re.S):
        ctx = re.search(r'<name>(.*?)</name>', cm.group(1), re.S)
        cname = ctx.group(1) if ctx else '?'
        for m in re.findall(r'<message[^>]*>(.*?)</message>', cm.group(1), re.S):
            s = re.search(r'<source>(.*?)</source>', m, re.S)
            t = re.search(r'<translation[^>]*>(.*?)</translation>', m, re.S)
            if not s:
                continue
            out.append({
                'ctx': cname,
                'src': s.group(1),
                'tr': t.group(1) if t else '',
                'has_location': '<location' in m,
            })
    for i, e in enumerate(out):
        e['index'] = i
    return out


# ================================================================ 风险分层
# 术语规范：同一英文术语必须统一译法
# key = 英文正则；value = (规范译法, 风险等级, 说明)
#
# ⚠️ 精度要点：正则必须**足够精确**，否则会把不同术语误判为不一致。
#    例：`\bbasis\b` 会同时命中 "Basis"（基组）和 "Basis Function"（基函数），
#    这两者本就该用不同译法。故此处用「优先匹配长形式」的写法，
#    并在下方 EXCLUDE 中排除掉不该归入本术语的条目。
TERM_CANON = [
    # (英文正则, 规范译法, 严重度, 说明, 排除正则或 None)
    (r'\bjobs?\b', '任务', 3,
     'Q-Chem 语境下 job 统一为「任务」（「作业」易与 homework 混淆）', None),
    (r'spin[- ]only', '纯自旋', 3,
     'spin-only density = 纯自旋密度；「仅自旋」是直译错误', None),
    (r'\bguess\b', '初始猜测', 2,
     'SCF guess = 初始猜测（单用「猜测」在中文界面里不成词）', None),
    (r'\bbasis sets?\b', '基组', 3, 'basis set = 基组', None),
    (r'\bbasis functions?\b', '基函数', 3, 'basis function = 基函数（与基组 basis set 区分）', None),
    (r'\bfunctionals?\b(?!\s+groups?\b)', '泛函', 3,
     'density functional = 密度泛函（否定预查排除 functional group）', None),
    (r'\bmultiplicity\b', '多重度', 3, 'multiplicity = 多重度（非「重数」）', None),
    (r'\bconvergence\b', '收敛', 3, 'convergence = 收敛', None),
    (r'\bgeometry optimization\b', '几何优化', 3, 'geometry optimization = 几何优化', None),
    (r'\btransition states?\b', '过渡态', 3, 'transition state = 过渡态', None),
    (r'\bvirtual orbitals?\b', '虚轨道', 3, 'virtual orbital = 虚轨道', None),
    (r'\boccupied orbitals?\b', '占据轨道', 3, 'occupied orbital = 占据轨道', None),
    (r'\bpartial charge', '部分电荷', 3, 'partial charge = 部分电荷（原子电荷）', None),
    (r'\bcharge\b', '电荷', 3, 'charge = 电荷', r'(partial|point|formal)'),
    # geminal = 双电子函数（GVB/APG/APSG/AP1roG/pCCD 语境）。
    # 本项目定稿为「成对」系列：成对 / 成对相关 / 成对轨道 / 成对 Alpha %1。
    # 历史误译「孪位/孪生/双生」已由 FORBIDDEN 拦截。
    (r'\bgeminals?\b', '成对', 3,
     'geminal 统一为「成对」系列（勿用孪位/孪生/双生）', None),
]

# 禁止译法：出现即为确定性缺陷
FORBIDDEN = [
    (r'仅自旋', 'spin-only 应为「纯自旋」', 10),
    (r'(?<![一二三四五六七八九十])重数', 'multiplicity 应为「多重度」', 10),
    (r'猜测打印', 'Print 为 Q-Chem 参数名，硬译不可读（建议保留 Print 或译「输出」）', 1),
    (r'^设定$', 'Set 在坐标语境下宜作「设定值」或保留', 1),
    (r'(?<![一二三四五六七八九十])自旋度', 'spin 相关术语应统一为「自旋」', 10),
    # geminal 的历史误译：曾出现 4 种译法并存，属严重级术语不一致
    (r'孪位|孪生|双生轨道', 'geminal 应为「成对」系列，勿用「孪位/孪生/双生」', 10),
]

# 高风险上下文：这些 context 里的译文直接决定计算参数是否正确
HIGH_RISK_CTX = re.compile(
    r'(MainWindow|Configurator|Tab$|Section|OptionDatabase|Parametrize|'
    r'GeometryConstraint|RemSection|MoleculeSection|LJParameters|'
    r'JobMonitor|QueueOptions|ServerConfiguration|SystemBuilder|'
    r'Orbitals|Surface|Constraint)', re.I)

# 高风险内容特征：影响计算参数或操作后果
HIGH_RISK_TEXT = re.compile(
    r'\b(charge|spin|multiplicity|basis|functional|method|SCF|MP2|CCSD|'
    r'B3LYP|HF|DFT|convergence|threshold|tolerance|optimize|optimization|'
    r'constraint|freeze|fixed|delete|remove|overwrite|reset|clear|purge|'
    r'error|failed|invalid|cannot|unable|warning|required|must|'
    r'Angstrom|kcal|Hartree|eV|Debye|Bohr)\b', re.I)


def risk_weight(e):
    """条目风险权重：1（低）~ 3（高）。权重进入 A_s 分母。"""
    if HIGH_RISK_CTX.search(e['ctx']) and HIGH_RISK_TEXT.search(e['src']):
        return 3
    if HIGH_RISK_CTX.search(e['ctx']) or HIGH_RISK_TEXT.search(e['src']):
        return 2
    return 1


def risk_layer(e):
    """分层标签，用于抽样保证覆盖。

    ⚠️ 精度要点：`spin` 在化学语境是「自旋」，在 Qt 语境是控件名 `QSpinBox`。
    早期实现让 "Spin box" → "微调框" 落进「A-化学参数」层，
    白白占用了高价值审校名额。故这里先排除控件名。
    """
    s, c = e['src'], e['ctx']
    QT_WIDGET = re.compile(
        r'\b(spin box|double spin box|combobox|combo box|check box|checkbox|'
        r'group box|list box|radio button|push button|line edit|tab widget|'
        r'scroll bar|progress bar|tool button|label|slider|table view)\b', re.I)
    if QT_WIDGET.search(s):
        return 'H-常规界面'
    if HIGH_RISK_TEXT.search(s) and re.search(
            r'(charge|spin|multiplicity|basis|functional|method)', s, re.I):
        return 'A-化学参数'
    if re.search(r'\b(error|failed|invalid|cannot|unable|warning|abort)\b', s, re.I):
        return 'B-错误信息'
    if HIGH_RISK_TEXT.search(s):
        return 'C-高后果操作'
    if re.search(r'\b(file|format|export|import|save|load|directory|path)\b', s, re.I):
        return 'D-文件与格式'
    if HIGH_RISK_CTX.search(c):
        return 'E-对话框主体'
    if re.search(r'\b(\d+|%\d)\b', s):
        return 'F-含数值/占位符'
    if len(s) > 60:
        return 'G-长文本'
    return 'H-常规界面'


# ================================================================ scan
def scan(entries):
    """自动筛查结构性语义缺陷。"""
    findings = defaultdict(list)

    # 1) 禁止译法
    for e in entries:
        for pat, why, sev in FORBIDDEN:
            if re.search(pat, e['tr']):
                findings['禁止译法'].append({**e, 'why': why, 'sev': sev,
                                             'rule': pat})

    # 2) 术语不一致：同一英文术语出现多种中文译法
    #
    # 提取方式很关键。早期实现取「译文里第一个中文词」作术语对应片段，
    # 对长句必然取错（"Computing basis functions on grid %1" 会取到"正在计算网格"）。
    # 正确做法：**只在译文里找该术语的中文候选**——把译文切成中文词，
    # 取与规范译法「编辑距离最近」的那个词作为实际译法。
    def zh_terms(s):
        return re.findall(r'[\u4e00-\u9fff]{2,}', s)

    def nearest_zh(tr, canon):
        words = zh_terms(tr)
        if not words:
            return None
        # 规范译法是子串 → 直接用规范译法
        for w in words:
            if canon in w or w in canon:
                return w
        # 否则取与规范译法最长公共子串最大的词（最可能是术语的对位）
        def lcs(a, b):
            best = 0
            for i in range(len(a)):
                for j in range(i + 1, len(a) + 1):
                    if a[i:j] in b:
                        best = max(best, j - i)
            return best
        scored = sorted(words, key=lambda w: -lcs(w, canon))
        return scored[0] if scored else None

    for pat, canon, sev, why, excl in TERM_CANON:
        variants = defaultdict(list)
        for e in entries:
            if excl and re.search(excl, e['src'], re.I):
                continue
            if not re.search(pat, e['src'], re.I):
                continue
            if not e['tr'] or not CJK.search(e['tr']):
                continue
            w = nearest_zh(e['tr'], canon)
            if w:
                variants[w].append(e)
        # 判据：存在「与规范译法共字率过低」的变体
        if variants:
            total = sum(len(v) for v in variants.values())
            bad = {}
            for k, v in variants.items():
                if canon in k or k in canon:
                    continue
                if len(k) >= 2 and (len(v) >= total * 0.2 or len(v) >= 3):
                    bad[k] = v
            for k, v in bad.items():
                for e in v:
                    findings['术语不一致'].append({
                        **e, 'why': f'{pat} 应统一为「{canon}」，当前「{k}」。{why}',
                        'sev': sev, 'rule': pat})

    # 3) 中英夹杂不当：译文里保留的可译英文（排除专名）
    #
    # ⚠️ 人名术语（Hartree-Fock / Kohn-Sham / Lennard-Jones）、
    #    程序名（Q-Chem / CHARMM / Amber / qchem）、
    #    格式名（POV-Ray）按规范**就该保留英文**，不算缺陷。
    KEEP = re.compile(
        r'\b(SCF|MP2|CCSD|CCSD\(T\)|B3LYP|HF|DFT|RI-?[JK]|DIIS|MOM|PAO|HFPT|AO|MO|'
        r'IQmol|Q-?Chem|qchem|GROMACS|OpenBabel|Qt|PBS|SGE|SSH|SFTP|FTP|'
        r'HTTP|HTTPS|URL|URI|API|GUI|ID|OK|'
        r'XYZ|PDB|CIF|MOL2|NBO|ESP|NMR|IR|UV|AIMD|EOM|ADC|CIS|CI|EFP|QMMM|'
        r'kB|MB|GB|TB|GHz|MHz|eV|amu|keV|meV|'
        r'Hartree|Fock|Kohn|Sham|Lennard|Jones|Mulliken|Hirshfeld|Lowdin|'
        r'Gasteiger|Merz|Kollman|RESP|Slater|Gaussian|Boys|'
        r'CHARMM|Amber|Ghemical|Gaff|MMFF9\d?s?|POV|Ray|Blender|'
        r'Aug|cc-|pV|TZ|QZ|VXZ|ANO|Roos|'
        r'CSV|XML|JSON|PDF|PNG|SVG|JPEG|Zip|Tar|'
        r'DOCTYPE|HTML|PUBLIC|quot|amp|nbsp|href|www|W3C|DTD|EN|CSS|'
        r'Linux|Windows|Mac|OS|X11|Wayland|OpenGL|GLSL|GL|'
        r'Maestro|Jaguar|Turbomole|Molpro|NWChem|ORCA|GAMESS|Psi4)')
    for e in entries:
        if not CJK.search(e['tr']):
            continue
        # 源/译文是 HTML 富文本骨架、shell 路径模板、或致谢段落中的 URL → 跳过
        if re.search(r'(DOCTYPE|&lt;html|&lt;head|&lt;style|&lt;p style)', e['tr']):
            continue
        if re.search(r'\$\{?\w+\}?/|\$\w+|\.ssh/|~/', e['tr']):
            continue
        if re.search(r'https?://|href=', e['tr']):
            continue
        # 译文里剩下的拉丁词，去掉专名后仍有普通英文词
        words = [w for w in re.findall(r'\b[A-Za-z]{4,}\b', e['tr'])
                 if not KEEP.match(w)]
        # 连续两个以上普通英文词才算缺陷（单个可能是漏网专名）
        if len(words) >= 2:
            findings['中英夹杂'].append({
                **e, 'why': f'译文中残留可译英文词：{", ".join(words[:4])}',
                'sev': 1, 'rule': 'mixed'})

    # 4) 占位符完整性
    for e in entries:
        sp = set(re.findall(r'%\d|%L\d|\{[^}]*\}', e['src']))
        tp = set(re.findall(r'%\d|%L\d|\{[^}]*\}', e['tr']))
        if sp != tp:
            findings['占位符不匹配'].append({
                **e, 'why': f'源占位符 {sorted(sp)} ≠ 译文 {sorted(tp)}',
                'sev': 10, 'rule': 'placeholder'})

    # 5) 长文本疑似漏译（中文占比过低）
    #    排除：样式表 / HTML 骨架 / 富文本 / 致谢段落。
    #    致谢段落（AboutDialog）里的库名、URL、人名**按规范保留英文**，
    #    中文占比低是正常的，不能算漏译。
    NOTRANSLATE = re.compile(
        r'^\s*[\w.#\-\[\]:>,\s]*\{|^\s*&lt;|^\s*<|^\s*p,\s*li\s*\{|'
        r'font-|color:|margin|padding|border|background|'
        r'^\s*[\w\-]+\s*:\s*[^;]*;|'
        r'^\s*(QTool|QPush|QLabel|QText|QLine|QCombo|QTab|QCheck|QGroup|'
        r'QSpin|QDialog|QMenu|QScroll|QProgress|QTree|QTable|QHeader)|'
        r'libQGLViewer|libqglviewer|openbabel\.org|boost\.org|'
        r'ccp14\.ac\.uk|paulbourke\.net|Marching cubes', re.I)
    for e in entries:
        if len(e['src']) <= 60 or NOTRANSLATE.search(e['src']):
            continue
        # 源文本身是英文自然语言才算「该翻译」
        if not re.search(r'[a-z]{3,}\s+[a-z]{3,}\s+[a-z]{3,}', e['src']):
            continue
        # 译文若已把自然语言部分译出，只是保留了库名/URL 等专名 → 不算漏译。
        # 判据：译文里的中文覆盖了源文**非链接部分**的大意。
        # 简化判据：源文去掉 &lt;li&gt;&lt;a href… 等链接片段后，仍是英文句子；
        # 而译文对应位置有中文，则视为已翻译。
        src_nolink = re.sub(r'&lt;/?[a-z]+[^&]*&gt;', ' ', e['src'], flags=re.I)
        src_nolink = re.sub(r'https?://\S+', ' ', src_nolink)
        if not re.search(r'[a-z]{3,}\s+[a-z]{3,}\s+[a-z]{3,}', src_nolink):
            continue
        cjk_n = len(CJK.findall(e['tr']))
        if cjk_n < len(e['tr']) * 0.15:
            findings['长文本疑似漏译'].append({
                **e, 'why': f'源 {len(e["src"])} 字符，译文仅 {cjk_n} 个中文字',
                'sev': 10, 'rule': 'longtext'})

    return findings


# ================================================================ sample
def sample(entries, size, seed=20260924):
    """分层抽样：高风险层 100% 覆盖，其余层按比例抽。"""
    random.seed(seed)
    layers = defaultdict(list)
    for e in entries:
        e['layer'] = risk_layer(e)
        e['weight'] = risk_weight(e)
        layers[e['layer']].append(e)

    picked, notes = [], []
    # 高风险两层全取
    FULL = ('A-化学参数', 'B-错误信息')
    for k in FULL:
        picked += layers.get(k, [])
        notes.append(f'{k}: 全取 {len(layers.get(k, []))} 条')

    # 其余按比例配额
    rest = [e for e in entries if e['layer'] not in FULL]
    remain = max(0, size - len(picked))
    if rest and remain:
        random.shuffle(rest)
        picked += rest[:remain]
        notes.append(f'其余层: 随机抽 {min(remain, len(rest))} 条')
    return picked, notes, layers


# ================================================================ score
def compute_A_s(rows):
    """
    rows: [{score, weight, fatal}]  —— score ∈ {0,1,10,100}
    A_s = Σ(score × weight) / Σ(100 × weight)
    """
    if not rows:
        return None, {}
    num = sum(float(r['score']) * float(r['weight']) for r in rows)
    den = sum(100.0 * float(r['weight']) for r in rows)
    stats = defaultdict(int)
    for r in rows:
        stats[int(r['score'])] += 1
    return (num / den if den else None), dict(stats)


def read_review(path):
    """
    读回人工填写的审校记录 CSV → [{score, weight, fatal, ...}]

    评分取值优先级（与工单列名对应）：
      裁决评分  >  审校者A评分  >  评分
    双人独立评分出现分歧时，以「裁决评分」为准；未填裁决时先取 A，
    并在报告中标注「未裁决条目数」，提醒补裁决。
    """
    LEVEL = {'无错误': 0, '轻微': 1, '严重': 10, '致命': 100,
             '无': 0, '0': 0, '1': 1, '10': 10, '100': 100}
    rows, undecided = [], 0
    with open(path, encoding='utf-8-sig', newline='') as f:
        for r in csv.DictReader(f):
            a = (r.get('审校者A评分') or '').strip()
            b = (r.get('审校者B评分') or '').strip()
            d = (r.get('裁决评分') or r.get('评分') or '').strip()
            raw = d or a
            if raw == '' or raw in ('-', '未评'):
                continue
            sc = LEVEL.get(raw)
            if sc is None:
                try:
                    sc = float(raw)
                except ValueError:
                    continue
            if d == '':
                undecided += 1
            rows.append({'score': sc,
                         'weight': float(r.get('权重') or 1),
                         'fatal': sc >= 100,
                         'id': r.get('编号', ''),
                         'ctx': r.get('上下文', ''),
                         'layer': r.get('分层', ''),
                         'src': r.get('原文', ''),
                         'tr': r.get('当前译文', ''),
                         'reason': (r.get('裁决理由') or r.get('审校者A理由') or ''),
                         'has_decision': bool(d)})
    return rows, undecided


# ================================================================ 输出
def report_scan(findings, entries):
    L = []
    L.append('=' * 70)
    L.append('  P6 语义质量 —— 自动筛查报告')
    L.append('=' * 70)
    total = sum(len(v) for v in findings.values())
    L.append(f'  待审条目总数: {total}  /  全库 {len(entries)} 条')
    L.append('')
    order = ['禁止译法', '术语不一致', '占位符不匹配', '长文本疑似漏译',
             '中英夹杂']
    for k in order:
        v = findings.get(k, [])
        if not v:
            continue
        sev = max(x['sev'] for x in v)
        L.append(f'  ---- {k}：{len(v)} 条（最高严重度 {sev}）----')
        seen = set()
        for x in v[:12]:
            sig = (x['src'], x['tr'])
            if sig in seen:
                continue
            seen.add(sig)
            L.append(f'    [{x["ctx"]}]')
            L.append(f'      原: {x["src"][:78]}')
            L.append(f'      译: {x["tr"][:78]}')
            L.append(f'      由: {x["why"][:78]}')
        if len(v) > 12:
            L.append(f'    … 其余 {len(v) - 12} 条见 JSON')
        L.append('')

    fatal = [x for v in findings.values() for x in v if x['sev'] >= 100]
    severe = [x for v in findings.values() for x in v if x['sev'] == 10]
    L.append('-' * 70)
    L.append(f'  致命级 {len(fatal)} 条   严重级 {len(severe)} 条')
    L.append('  ⚠ 致命级 > 0 即阻断发布（见 TQA §四）')
    L.append('=' * 70)
    return '\n'.join(L)


def write_worklist(picked, outdir):
    os.makedirs(outdir, exist_ok=True)
    csv_path = os.path.join(outdir, 'P6-审校工单.csv')
    with open(csv_path, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        w.writerow(['编号', '分层', '权重', '上下文', '原文', '当前译文',
                    '审校者A评分', '审校者A理由',
                    '审校者B评分', '审校者B理由',
                    '裁决评分', '裁决理由'])
        for i, e in enumerate(picked, 1):
            w.writerow([f'P6-{i:04d}', e['layer'], e['weight'], e['ctx'],
                        e['src'], e['tr'], '', '', '', '', '', ''])

    md_path = os.path.join(outdir, 'P6-审校工单.md')
    by_layer = defaultdict(list)
    for e in picked:
        by_layer[e['layer']].append(e)
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write('# P6 语义质量人工审校工单\n\n')
        f.write(f'> 共 {len(picked)} 条。请两名审校者**独立**填写，互不通气；\n')
        f.write('> 分歧条目由第三人裁决。化学参数/错误信息类以化学专业意见为主。\n\n')
        f.write('## 评分标准\n\n')
        f.write('| 等级 | 分数 | 含义 |\n|---|---:|---|\n')
        f.write('| 无错误 | 0 | 准确、清晰、符合上下文 |\n')
        f.write('| 轻微 | 1 | 表达不自然，不影响操作 |\n')
        f.write('| 严重 | 10 | 含义明显偏差，可能造成理解困难 |\n')
        f.write('| 致命 | 100 | 可能造成错误参数选择或操作风险 |\n\n')
        f.write('## 分层构成\n\n| 分层 | 条数 |\n|---|---:|\n')
        for k in sorted(by_layer):
            f.write(f'| {k} | {len(by_layer[k])} |\n')
        f.write('\n---\n\n')
        for k in sorted(by_layer):
            f.write(f'## {k}（{len(by_layer[k])} 条）\n\n')
            for e in by_layer[k]:
                f.write(f'**{e["ctx"]}**（权重 {e["weight"]}）\n\n')
                f.write(f'- 原文：`{e["src"]}`\n')
                f.write(f'- 当前译文：`{e["tr"]}`\n')
                f.write('- A 评分/理由：\n- B 评分/理由：\n- 裁决：\n\n')
    return csv_path, md_path


def main():
    ap = argparse.ArgumentParser(description='P6 语义质量审校工具链')
    sub = ap.add_subparsers(dest='cmd', required=True)

    p1 = sub.add_parser('scan', help='自动筛查结构性语义缺陷')
    p1.add_argument('--json', action='store_true')
    p1.add_argument('--save', help='结果写 JSON')

    p2 = sub.add_parser('sample', help='分层抽样生成审校工单')
    p2.add_argument('--size', type=int, default=240)
    p2.add_argument('--out', default='review')

    p3 = sub.add_parser('score', help='消费审校记录算 A_s')
    p3.add_argument('review_csv')
    p3.add_argument('--save', default='review/P6-审校结果.json',
                    help='A_s 结果写入 JSON（tqa.py 会自动读取）')
    p3.add_argument('--reviewer', default='', help='审校者署名')

    args = ap.parse_args()
    entries = load_ts()

    if args.cmd == 'scan':
        f = scan(entries)
        data = {k: v for k, v in f.items()}
        if args.save:
            with open(args.save, 'w', encoding='utf-8') as fp:
                json.dump(data, fp, ensure_ascii=False, indent=2)
        if args.json:
            print(json.dumps(data, ensure_ascii=False, indent=2)[:4000])
        else:
            print(report_scan(f, entries))
        fatal = [x for v in f.values() for x in v if x['sev'] >= 100]
        return 1 if fatal else 0

    if args.cmd == 'sample':
        picked, notes, layers = sample(entries, args.size)
        csv_path, md_path = write_worklist(picked, args.out)
        print(f'审校工单已生成：{len(picked)} 条')
        for n in notes:
            print('  ' + n)
        print(f'  CSV : {csv_path}')
        print(f'  清单: {md_path}')
        return 0

    if args.cmd == 'score':
        rows, undecided = read_review(args.review_csv)
        if not rows:
            print('未读到有效评分（评分列为空）')
            return 1
        A_s, stats = compute_A_s(rows)
        fatal = [r for r in rows if r['fatal']]
        print('=' * 62)
        print('  P6 语义质量 —— 审校结果')
        print('=' * 62)
        print(f'  已评条目 : {len(rows)}')
        print(f'  未裁决   : {undecided} 条' +
              ('  ⚠ 建议补第三人或化学专业裁决' if undecided else '  ✅ 全部已裁决'))
        print(f'  等级分布 : 无错误 {stats.get(0,0)} / 轻微 {stats.get(1,0)}'
              f' / 严重 {stats.get(10,0)} / 致命 {stats.get(100,0)}')
        print(f'  A_s      : {A_s:.6f}   ({A_s*100:.4f}%)')
        print(f'  致命级   : {len(fatal)} 条' +
              ('  ❌ 阻断发布' if fatal else '  ✅ 通过'))
        print('=' * 62)
        print()
        print('  → 写入 tqa.py 的 P6 槽位：P6 = ' f'{A_s:.6f}')

        # 落盘供 tqa.py 自动读取
        from datetime import datetime, timezone
        out = {
            'A_s': A_s,
            'n_reviewed': len(rows),
            'n_none': stats.get(0, 0),
            'n_minor': stats.get(1, 0),
            'n_severe': stats.get(10, 0),
            'n_fatal': stats.get(100, 0),
            'undecided': undecided,
            'reviewer': args.reviewer,
            'reviewed_at': datetime.now(timezone.utc).strftime('%Y-%m-%d'),
            'source_csv': args.review_csv,
        }
        os.makedirs(os.path.dirname(args.save) or '.', exist_ok=True)
        with open(args.save, 'w', encoding='utf-8') as fp:
            json.dump(out, fp, ensure_ascii=False, indent=2)
        print(f'  → 已落盘 {args.save}（tqa.py 将自动计入 P6 权重）')
        if fatal:
            print('\n致命级条目：')
            for r in fatal[:20]:
                print(f'  [{r["id"]}] {r["src"][:60]}')
                print(f'          → {r["tr"][:60]}')
                print(f'          理由: {r["reason"][:70]}')
        return 1 if fatal else 0


if __name__ == '__main__':
    sys.exit(main())
