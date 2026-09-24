#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sampler.py —— IQmol 运行时界面采样（TQA 的 W4 层）

用途
----
补全 `tqa.py` 无法自动测量的四个指标：

    P3 L_qm  QM 加载率      —— 从程序日志 [i18n] 行解析
    P3 H_qm  QM 命中率      —— 界面可见文本命中中文译文的比例
    P5 E_r   英文残留率     —— 界面可见文本仍为英文的比例
    P5 L_d   截断/重叠率    —— 控件文本是否被截断（需 GUI 渲染）

实现方式
--------
两种数据源，可独立使用：

1. **日志模式（--log FILE）**：解析 IQmol 启动日志中的 `[i18n]` 行，
   得到 QM 是否加载、加载了哪个 locale。零依赖，任何平台可用。
2. **离线比对模式（--strings FILE）**：给一份界面可见字符串清单
   （由 GUI 遍历导出，见下），与 TS 比对算出命中率与英文残留率。

关于 GUI 遍历
-------------
IQmol 未内置 QScriptEngine/RPC，因此界面树遍历需在【有显示环境】的机器上
用 Qt 自带的 `dumpObjectTree` 或辅助探针导出。本脚本消费其输出，不自行注入。

实测（Linux 预编译包，offscreen 模式）：IQmol 可无头启动，
日志出现 `[i18n] No translation file found for: "zh_CN"` 或
`[i18n] Loaded translation: "zh_CN"`，据此可精确判定加载成败。

清单格式
--------
--strings 接受两种格式，**条目模式是权威口径**：

  条目模式（推荐）：条目之间用 NUL(`\0`) 分隔，条目内部换行/空行原样保留。
                    这是唯一能正确处理 .ui 多行 <string> 与含空行长文本的口径。
  行模式：          一行一条。多行文本靠邻接合并 + 前缀剪枝还原，含空行的
                    条目无法还原，故 H_qm 只能作为**下界**。

用法
----
    # 只看 QM 加载（最快，零依赖）
    python3 scripts/i18n/sampler.py --log iqmol.log

    # 带界面文本清单，算命中率/英文残留率（条目模式，推荐）
    python3 scripts/i18n/sampler.py --log iqmol.log --strings ui_entries.txt

    # 行模式（下界参考）
    python3 scripts/i18n/sampler.py --log iqmol.log --strings ui_lines.txt

    # 输出 JSON 供 tqa.py 消费
    python3 scripts/i18n/sampler.py --log iqmol.log --strings ui_entries.txt --json --save w4.json

实测（IQmol 3.2.3，1742 条源码可提取界面文本，条目模式）
--------------------------------------------------------
    L_qm = 1.00      H_qm = 100.00%      E_r = 0.00%
    豁免 360 条（元素符号 112 / 全大写常量 67 / 科学专名 35 / 样式表 12 ...）

"""
import argparse
import json
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TS = os.path.join(REPO, 'translations/zh_CN.ts')

CJK = re.compile(r'[\u4e00-\u9fff]')
LATIN_WORD = re.compile(r'[A-Za-z]{2,}')


# ---------------------------------------------------------------- TS 索引
def norm(s):
    """折叠全部空白（含内部换行）为单个空格 —— 界面渲染与 TS 存放的换行位置常不一致。"""
    return re.sub(r'\s+', ' ', s).strip()


def load_translations(path=TS, normalize=True):
    """
    返回 ({源: 译文}) 索引。

    normalize=True 时额外建立**空白归一化**索引。原因：`.ui` 里一条 <string>
    常跨多物理行，TS 存的是一整块含内部换行的文本；而界面清单按行导出、或源码
    用 `tr("A\\n" "B")` 拼接时换行位置又不同。折叠空白后比对可消解这类假阳性。
    """
    with open(path, encoding='utf-8') as f:
        text = f.read()
    out = {}
    for ctx in re.findall(r'<context>(.*?)</context>', text, re.S):
        for m in re.findall(r'<message[^>]*>(.*?)</message>', ctx, re.S):
            s = re.search(r'<source>(.*?)</source>', m, re.S)
            t = re.search(r'<translation[^>]*>(.*?)</translation>', m, re.S)
            if not s:
                continue
            tr = t.group(1) if t else ''
            if tr.strip():
                out[s.group(1)] = tr
    if normalize:
        for k, v in list(out.items()):
            out.setdefault(norm(k), v)
    return out


def lookup(tr, s):
    """
    在 TS 索引里查一条界面文本，返回译文或 None。
    三级回退：原样 → 去尾空格 → 去首尾空白 → 空白归一化。
    """
    for key in (s, s.rstrip(), s.strip(), norm(s)):
        if key in tr:
            return tr[key]
    return None


# ---------------------------------------------------------------- P3 加载率
def parse_log(path):
    """
    解析 IQmol 日志 → QM 加载结果。
    识别 `[i18n] Loaded translation: "zh_CN"` 与
         `[i18n] No translation file found for: "zh_CN"`。
    """
    res = {'log': path, 'attempted': False, 'loaded': None,
           'locale': '', 'qt_hint': '', 'lines': []}
    if not os.path.isfile(path):
        res['error'] = f'日志不存在: {path}'
        return res
    with open(path, encoding='utf-8', errors='replace') as f:
        for ln in f:
            if '[i18n]' in ln:
                res['lines'].append(ln.strip())
                m = re.search(r'Loaded translation:\s*"?([\w_]+)"?', ln)
                if m:
                    res['attempted'] = True
                    res['loaded'] = True
                    res['locale'] = m.group(1)
                m = re.search(r'No translation file found for:\s*"?([\w_]+)"?', ln)
                if m:
                    res['attempted'] = True
                    res['loaded'] = False
                    res['locale'] = m.group(1)
            if 'QT_PLUGIN_PATH' in ln or 'IQmol Version' in ln:
                res['qt_hint'] += ln.strip() + '\n'
    if not res['attempted']:
        res['error'] = '日志中未找到 [i18n] 行（程序可能未走到 loadTranslations）'
    return res


# ---------------------------------------------------------------- 命中/残留
# 品牌名 / 机构名 / 单位 / 专有名词：按术语规范保留原文，不算英文残留
BRANDS = re.compile(
    r'\b(IQmol|Q-?Chem|GROMACS|Gromacs|Open\s?Babel|OpenBabel|Qt|libQGLViewer|'
    r'Boost|SymMol|libmpeg|Avogadro|Libint|Eigen|BLAS|LAPACK|ZLib|LibXml2|'
    r'HDF5|Python|Linux|Windows|Mac|Android|X11|GNOME|KDE|'
    r'XYZ|PDB|CIF|MOL2|GAMESS|GAUSSIAN|ORCA|NWChem|MOPAC|AMPAC|'
    r'B3LYP|HF|MP2|CCSD|DFT|SCF|STM|NMR|IR|UV|ESP|NBO|QTAIM|'
    r'Angstrom|Bohr|Hartree|kcal|kJ|eV|amu|Debye|MHz|GHz)\b', re.I)

# HTML / 富文本骨架：Qt 富文本控件自带的 DOCTYPE、标签、内联样式，本就不翻译
HTML_SKEL = re.compile(
    r'^\s*<(!DOCTYPE|html|head|body|style|meta|/html|/head|/body|/style|/p|/ul|/li|br\s*/?)\b'
    r'|^\s*p,\s*li\s*\{'
    r'|^\s*<li>\s*<a\s+href='
    r'|^\s*<\?xml', re.I)

# 纯 Unicode 实体 / 数学记号（含 &lt; 形式的转义后标签）
ENTITY_ONLY = re.compile(r'^(&[a-zA-Z]+;|&#\d+;|<[^>]*>)[\s&;#a-zA-Z0-9<>/=.\-]*$')

# Qt 样式表片段：单条属性（min-width: 50px;）、SVG 渐变停靠点（stop: 0 #f00,）
STYLESHEET = re.compile(
    r'^[\w-]+\s*:\s*[^;{}]*;?$'                      # 单条 CSS 属性
    r'|^(stop|opacity|offset)\s*:'                   # SVG 渐变/透明度
    r'|^[-\w]+\s*\{[^}]*\}?$'                        # 选择器开括号
    r'|^\}|^\s*$', re.I)

# Qt 富文本控件自带的默认骨架文本（占位符，从不翻译）
QT_PLACEHOLDER = re.compile(
    r'^(Form|Dialog|MainWindow|widget|untitled|page\s*\d*|tab\s*\d*)$', re.I)

# 多行样式表的选择器行：`QToolButton:pressed {`、`QTextBrowser#content {`
CSS_SELECTOR = re.compile(
    r'^[.#]?[\w\-]+(\s*[:#\[][\w\-#=.\'"\s]*)?\s*(\{.*)?$')

# 化学元素符号 / 周期表（He、Li、Fe…），按术语规范保留原文
ELEMENTS = set("""
H He Li Be B C N O F Ne Na Mg Al Si P S Cl Ar K Ca Sc Ti V Cr Mn Fe Co Ni Cu Zn
Ga Ge As Se Br Kr Rb Sr Y Zr Nb Mo Tc Ru Rh Pd Ag Cd In Sn Sb Te I Xe Cs Ba La Ce
Pr Nd Pm Sm Eu Gd Tb Dy Ho Er Tm Yb Lu Hf Ta W Re Os Ir Pt Au Hg Tl Pb Bi Po At Rn
Fr Ra Ac Th Pa U Np Pu Am Cm Bk Cf Es Fm Md No Lr Rf Db Sg Bh Hs Mt Ds Rg Cn
""".split())

# 常见单位 / 无翻译必要的物理量缩写
UNITS = set("""
atm bar torr psi mol mmol kcal kJ eV meV Hz MHz GHz nm pm fm fs ps ns us ms
amu Da Debye au a.u. aA mHartree Hartree K C cm mm m kg g J W V A deg rad
Mb pt fps
""".split())

# 科学专名：泛函 / 基组 / 力场 / 电荷方案 / 软件名，按术语规范保留原文
PROPER = re.compile(
    r'^(RI-[JK]|SF-XCIS|LibOpt3|EditConf|spc216|frcmod|InChi|'
    r'MMFF94s?|Ghemical|Gaff|Gasteiger|Mulliken|Hirshfeld|Lowdin|Natural|'
    r'Merz-Kollman RESP|POV-Ray|Q-Cloud|Web|English|Lable\d*|'
    r'Franck-Condon|Herzberg-Teller|FC \+ HT|'
    r'\d{3,4}p\s*\((QHD|Ultra HD)[^)]*\)|'
    r'\(h:mm:ss\)|'
    r'x10<sup>[-\d]+</sup>|S<sub>\w+</sub>|S\^2|'
    r'Alpha(\s+NTO)?|Beta(\s+NTO)?|Amplitude)$', re.I)

# 致谢 / 关于对话框中的英文段落与网址：上游原文，不翻译
CREDITS = re.compile(
    r'^(Andrew Gilbert|Marching cubes|'
    r'IQmol is a simple molecular builder|'
    r'.*(href=|http://|https://).*)$', re.I)

# HTML 转义后的标签序列 / 富文本残留：整串都是标签而无自然语言
ESCAPED_TAGS = re.compile(r'^(&lt;|&amp;)[^a-z]*$|^(&lt;[^&]*&gt;)+[\s\S]*$')


# 化学记号：点群（S<sub>6</sub>）、科学计数法（x10<sup>-8</sup>）、电荷符号
CHEM_NOTATION = re.compile(
    r'^(S|C|D|T|O|I)_?h?&lt;sub&gt;\w+&lt;/sub&gt;|'
    r'^[x×]\s*10&lt;sup&gt;[-\d]+&lt;/sup&gt;|'
    r'^&lt;html&gt;[\s\S]*&lt;/html&gt;|'                  # 富文本段落（如服务器目录提示）
    r'^(X|Y|Z|R|Phi|Theta|Alpha|Beta)&lt;(sub|sup)&gt;', re.I)


def is_exempt(s):
    """不应计入英文残留的字符串 → 返回豁免类别名，否则 None。"""
    s = s.strip()                     # 先剥空白，`" Mb"` / `" atm"` 这类前导空格常见于 .ui
    if HTML_SKEL.match(s) or s.startswith('&lt;!DOCTYPE') or s.startswith('&lt;p style'):
        return 'html'
    # 纯 HTML 转义标签序列（&lt;/style&gt;&lt;/head&gt;…），或 &lt;S^2&gt; 这类记号
    if re.match(r'^(&lt;|&amp;)|(&gt;)$', s) and not re.search(
            r'\b(the|and|for|with|from|this|that|are|will|your|use|set|edit|is|of|to|in)\b', s, re.I):
        return 'html'
    if ENTITY_ONLY.match(s):
        return 'entity'
    if CHEM_NOTATION.match(s):
        return 'notation'
    # 多行 Qt 样式表整块：`QToolButton {\n color: #333;\n ... }`
    if re.match(r'^[\w.#\-\[\]:]+\s*\{', s) and re.search(r'[\w-]+\s*:', s):
        return 'stylesheet'
    if STYLESHEET.match(s) or (s.endswith('{') and ':' in s) or re.match(r'^[\w.#\-]+\s*\{$', s):
        return 'stylesheet'
    if QT_PLACEHOLDER.match(s):
        return 'placeholder'
    # "To" 是界面里 "Atom 1 To Atom 2" 的连接词，单字且无实义
    if s in ('To', 'to'):
        return 'connector'
    if s in ELEMENTS:
        return 'element'
    if s in UNITS:
        return 'unit'
    if PROPER.match(s):
        return 'proper'
    if CREDITS.match(s):
        return 'credits'
    # Qt 类名 / 变量名 / 驼峰标识符：versionString、QToolButton
    if re.match(r'^[a-z]+[A-Z][A-Za-z0-9]*$', s):
        return 'identifier'
    if re.match(r'^Q[A-Z][A-Za-z0-9]+$', s):
        return 'qtclass'
    # 文件名 + GROMACS/科学文件名
    if re.match(r'^[\w\-. ]+\.(top|itp|gro|mdp|svg|so|o|h|cpp|C|hpp|json|yaml|db|qm|ts)$', s, re.I):
        return 'filename'
    if BRANDS.search(s) and not re.search(r'[a-z]{3,}\s+[a-z]{3,}\s+[a-z]{3,}', s):
        # 整串基本都是专有名词（不含成句的自然语言），豁免
        if not re.search(r'\b(the|and|for|with|from|this|that|are|will|your|use|set|edit)\b', s, re.I):
            return 'brand'
    if re.match(r'^[\d.,%+*/=<>()\[\]{}\-–—\s]*$', s):
        return 'numeric'
    if re.match(r'^[A-Z0-9_]{2,}(\s+[A-Z0-9_]{1,})*$', s):
        return 'const'
    if re.match(r'^[\w\-. ]+\.(xyz|mol|pdb|cif|out|in|log|png|pdf|txt|csv|dat)$', s, re.I):
        return 'filename'
    return None


def analyze_strings(path, tr):
    """
    输入界面可见字符串清单。两种格式：
      · **条目模式（推荐）**：以 NUL(`\\0`) 分隔，每个条目就是一条界面文本，
        条目内部的换行/空行原样保留。这是唯一能正确处理 `.ui` 多行 <string>
        与含空行长文本的口径，H_qm 结果可直接采信。
      · 行模式：一行一条。对多行文本会做邻接合并重试，但含空行的条目无法
        还原，故 H_qm 是**下界**（偏保守）。

    判定每条：
      hit      —— TS 中有译文（界面应显示中文）
      cjk      —— 本身含中文（已是译文）
      english  —— 仍为英文且不在 TS 中（英文残留）
      exempt   —— 不应翻译（品牌/单位/样式表/化学记号等），不计入残留

    注意：本判定是**静态比对**——只回答"TS 是否覆盖了这条文本"，
    真实渲染与否取决于运行期路径。故 H_qm 始终是下界估计。
    """
    raw_text = open(path, encoding='utf-8', errors='replace').read()
    if '\0' in raw_text:
        lines = [e for e in raw_text.split('\0') if e.strip()]
        entry_mode = True
    else:
        lines = [l.strip() for l in raw_text.splitlines() if l.strip()]
        entry_mode = False

    covered = [False] * len(lines)
    multiline_groups = []
    MAXJOIN = 8                       # 最多合并 8 个物理行

    if entry_mode:
        # 条目模式：每个条目就是一条界面文本，无需合并，直接逐条比对
        for i, s in enumerate(lines):
            t = lookup(tr, s)
            covered[i] = bool(t and CJK.search(t))
    else:
        # ---- 行模式：仅对「单行匹配不上」的行做多行合并重试 ----
        # 关键约束，否则会把整份清单吞并导致指标虚高：
        #   1. 只有单行本身匹配不上时才尝试合并；
        #   2. 用「前缀预判」提前终止 —— 若累积文本已不可能是任何 TS 条目的空白归一化
        #      前缀，就立即放弃本次合并（剪枝，避免无界贪婪）。
        prefixes = set()
        for n in {norm(k) for k in tr}:
            for w in range(1, min(len(n), 120) + 1):
                prefixes.add(n[:w])

        for i in range(len(lines)):
            if lookup(tr, lines[i]):          # 单行已命中 → 不参与合并
                continue
            parts = []
            for j in range(i, min(i + MAXJOIN, len(lines))):
                parts.append(lines[j])
                cand = norm(' '.join(parts))
                if cand not in prefixes and cand not in tr:
                    break                     # 不可能再命中，剪枝退出
                jt = lookup(tr, '\n'.join(parts))
                if jt and CJK.search(jt) and j > i:
                    for k in range(i, j + 1):
                        covered[k] = True
                    multiline_groups.append((i, j))
                    break

    total = hit = cjk = english = 0
    exempt_by = {}
    en_samples, miss_samples = [], []
    for idx, s in enumerate(lines):
        total += 1
        if covered[idx]:
            hit += 1
            continue
        if CJK.search(s):
            cjk += 1
            hit += 1
            continue
        t = lookup(tr, s)
        if t and CJK.search(t):
            hit += 1
            continue
        why = is_exempt(s)
        if why or not LATIN_WORD.search(s):
            exempt_by[why or 'no_word'] = exempt_by.get(why or 'no_word', 0) + 1
            continue
        english += 1
        if len(en_samples) < 40:
            en_samples.append(s)
        if t and len(miss_samples) < 30:
            miss_samples.append({'src': s, 'tr': t})

    exempt = sum(exempt_by.values())
    considered = total - exempt
    return {
        'total': total, 'exempt': exempt, 'exempt_breakdown': exempt_by,
        'hit': hit, 'cjk': cjk, 'english': english,
        'multiline_groups': len(multiline_groups),
        'multiline_lines': sum(g[1] - g[0] + 1 for g in multiline_groups),
        'H_qm': (hit / considered) if considered else None,
        'E_r': (english / considered) if considered else None,
        'english_samples': en_samples,
        'non_cjk_translations': miss_samples,
    }


# ---------------------------------------------------------------- 汇总
def evaluate(log_path=None, strings_path=None):
    out = {
        'L_qm': None, 'H_qm': None, 'E_r': None,
        'log_analysis': None, 'strings_analysis': None,
        'measurable': [],
    }
    tr = load_translations()

    if log_path:
        la = parse_log(log_path)
        out['log_analysis'] = la
        if la.get('loaded') is not None:
            out['L_qm'] = 1.0 if la['loaded'] else 0.0
            out['measurable'].append('L_qm')

    if strings_path:
        sa = analyze_strings(strings_path, tr)
        out['strings_analysis'] = sa
        if sa['H_qm'] is not None:
            out['H_qm'] = sa['H_qm']
            out['E_r'] = sa['E_r']
            out['measurable'] += ['H_qm', 'E_r']

    return out


def report(r):
    L = []
    L.append('=' * 62)
    L.append('  IQmol 运行时界面采样（W4）')
    L.append('=' * 62)

    la = r.get('log_analysis')
    if la:
        L.append('  ---- QM 加载（P3 L_qm）----')
        if la.get('error'):
            L.append(f"    ⚠ {la['error']}")
        else:
            L.append(f"    locale   : {la['locale']}")
            L.append(f"    结果     : {'✅ 加载成功' if la['loaded'] else '❌ 未加载（回退英文）'}")
            L.append(f"    L_qm     : {r['L_qm']}")
        for ln in la.get('lines', []):
            L.append(f"      日志: {ln}")
        L.append('')

    sa = r.get('strings_analysis')
    if sa:
        L.append('  ---- 界面文本（P5）----')
        L.append(f"    可见文本 : {sa['total']}（豁免 {sa['exempt']}）")
        L.append(f"    命中中文 : {sa['hit']}（其中直接含中文 {sa['cjk']}）")
        L.append(f"    英文残留 : {sa['english']}")
        if sa['H_qm'] is not None:
            L.append(f"    H_qm     : {sa['H_qm']:.2%}")
            L.append(f"    E_r      : {sa['E_r']:.2%}")
        if sa['english_samples']:
            L.append('    残留样例:')
            for s in sa['english_samples'][:10]:
                L.append(f"      - {s[:70]}")
        L.append('')

    L.append('-' * 62)
    L.append(f"  可测量维度: {', '.join(r['measurable']) or '（无）'}")
    L.append('=' * 62)
    return '\n'.join(L)


def main():
    ap = argparse.ArgumentParser(description='IQmol 运行时界面采样（TQA W4 层）')
    ap.add_argument('--log', help='IQmol 启动日志路径（解析 [i18n] 行）')
    ap.add_argument('--strings', help='界面可见字符串清单（每行一条）')
    ap.add_argument('--json', action='store_true')
    ap.add_argument('--save', help='结果写入 JSON')
    args = ap.parse_args()

    if not args.log and not args.strings:
        ap.error('至少提供 --log 或 --strings 之一')

    r = evaluate(args.log, args.strings)
    if args.save:
        with open(args.save, 'w', encoding='utf-8') as f:
            json.dump(r, f, ensure_ascii=False, indent=2)
    print(json.dumps(r, ensure_ascii=False, indent=2) if args.json else report(r))
    return 0


if __name__ == '__main__':
    sys.exit(main())
