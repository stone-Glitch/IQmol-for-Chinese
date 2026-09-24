#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
p6_review_rules.py —— P6 双人独立审校的评分规则（可复用）

背景
----
`semantic_audit.py` 负责「筛查 + 抽样 + 汇总」，但**评分本身**需要判据。
本模块把判据固化为可复用规则，对应 TQA 要求的两个审校视角：

  审校者 A —— 中文表达视角
    中文是否成词、语序是否自然、界面语体是否恰当（标签不带句号等）

  审校者 B —— 计算化学视角
    术语是否符合全国科学技术名词审定委员会规范

裁决策略：取两方中**更严**的一档（保守），化学术语风险以 B 为准。

为什么不塞进 semantic_audit.py
------------------------------
规则会随术语规范演进频繁修改，而筛查/汇总逻辑稳定。
分离后：改规则不动工具，且规则可单独做**对抗性测试**（见 selftest）。

规则自身的对抗性测试
--------------------
审校规则也会有假阳性/假阴性。本模块提供 `selftest()`：
把已知缺陷与已知正确译文喂进规则，断言「该抓的抓到、该放的放掉」。
**规则每次改动都应重跑 selftest** —— 否则会得到「全零缺陷」这种看着漂亮
但毫无意义的结论。
"""
import re

# ================================================================ 审校者 A
# 中文表达视角。判据：读起来是不是中文、像不像界面标签。
A_RULES = [
    # 注意：不要给「猜测」加否定预查放行「猜测类型/猜测选项」——
    # 这些恰恰是待修项（应为「初始猜测类型」）。曾经加过 (?!类型|选项)，被自检抓到。
    (r'^猜测',                   10, '「猜测」单用不成词，应为「初始猜测」'),
    (r'^仅自旋',                 10, '「仅自旋」是直译，应为「纯自旋」'),
    (r'猜测打印',                 1,  '「猜测打印」语序不通'),
    (r'^设定$',                   1,  '「设定」作标签过简，宜明确为「设定值」或保留'),
    (r'[，。；：]\s*[，。；：]',    10, '标点重复'),
]

# 合法叠字：不应被判为重复字错误
LEGIT_REDUP = {
    '谢谢', '刚刚', '常常', '慢慢', '渐渐', '往往', '稍稍', '仅仅',
    '处处', '个个', '天天', '年年', '月月', '步步', '件件', '种种',
    '多多', '轻轻', '静静', '默默', '悄悄', '缓缓', '纷纷', '统统',
    '面面', '点点', '些些', '样样', '条条', '层层', '纷纷', '一一',
}
REDUP = re.compile(r'([\u4e00-\u9fff])\1')


def score_A(row):
    """审校者 A 评分 → (score, reason)"""
    t = row.get('当前译文', '') or ''
    for pat, sc, why in A_RULES:
        if re.search(pat, t):
            return sc, why
    # 重复字（排除合法叠字）
    hits = [m.group(0) for m in REDUP.finditer(t)
            if m.group(0) not in LEGIT_REDUP]
    if hits:
        return 10, f'重复字：{"、".join(sorted(set(hits)))}'
    # 短标签末尾不应带句号（界面语体）
    #
    # ⚠️ 仅适用于「标签」。完整句子（HTML 页面正文、提示句）本就该带句号，
    #    例如 HelpBrowser 的 "No results found." 会渲染进 <body> 段落。
    #    判据用「原文是否也带句号」区分：原文带句号 → 是句子，放行。
    src = row.get('原文', '')
    t_stripped = t.strip()
    sentence = bool(re.search(r'[.。!！?？;；]$', src.strip()))
    if (len(src) < 20 and not sentence
            and re.search(r'[。．]$', t_stripped)):
        return 1, '短标签末尾不应加句号'
    # 译文相对原文过度膨胀（界面空间有限）
    if len(src) > 8 and len(t) > len(src) * 3:
        return 1, '译文相对原文过度膨胀'
    return 0, ''


# ================================================================ 审校者 B
# 计算化学视角：术语规范。顺序即优先级 —— **长形式必须排在短形式之前**，
# 否则 `functional` 会先命中 `Functional Group`。
B_TERMS = [
    ('functional group', r'\bfunctional groups?\b',              '官能团'),
    ('geminal',          r'\bgeminals?\b',                       '成对'),
    ('spin-only',        r'spin[- ]only',                        '纯自旋'),
    ('basis function',   r'\bbasis functions?\b',                '基函数'),
    ('basis set',        r'\bbasis sets?\b',                     '基组'),
    ('functional',       r'\bfunctionals?\b(?!\s+groups?\b)',    '泛函'),
    ('multiplicity',     r'\bmultiplicity\b',                    '多重度'),
    ('partial charge',   r'\bpartial charges?\b',                '部分电荷'),
    ('charge',           r'\bcharges?\b',                        '电荷'),
    ('convergence',      r'\bconvergence\b',                     '收敛'),
    ('orbital',          r'\borbitals?\b',                       '轨道'),
    ('density',          r'\bdensit(y|ies)\b',                   '密度'),
    ('optimization',     r'\boptimi[sz]ation\b',                 '优化'),
    # ⚠️ gradient 有歧义：颜色渐变（Center Gradient / Color Gradient）应译「渐变」，
    #    计算量梯度（Gradient / Gradient Steps）应译「梯度」。
    #    这里只收数学/计算语境，颜色语境由 COLOR_GRADIENT 排除。
    ('gradient',         r'\bgradients?\b',                      '梯度'),
    ('frequency',        r'\bfrequenc(y|ies)\b',                 '频率'),
    ('isosurface',       r'\bisosurfaces?\b',                    '等值面'),
    ('transition state', r'\btransition states?\b',              '过渡态'),
    ('virtual orbital',  r'\bvirtual orbitals?\b',               '虚轨道'),
    ('occupied orbital', r'\boccupied orbitals?\b',              '占据轨道'),
]

# 颜色渐变语境：此时 gradient 不是数学梯度，译「渐变」才正确
COLOR_GRADIENT = re.compile(
    r'\b(color|colour|centre|center|background|linear|radial)\s+gradient\b'
    r'|\bgradient\s+(editor|stop|steps?)\b'
    r'|QLinearGradient|qlineargradient', re.I)

# 确定性错误译法：出现直接判
B_FATAL = [
    (r'重数',   10, 'multiplicity 应为「多重度」'),
    (r'仅自旋', 10, 'spin-only 应为「纯自旋」'),
    (r'^猜测',  10, 'guess 应为「初始猜测」'),
    (r'等值线面|等值曲面', 1, 'isosurface 宜统一为「等值面」'),
    # geminal 的历史误译：同一条目在库中出现 4 种译法，属严重级术语不一致
    (r'孪位|孪生|双生轨道', 10, 'geminal 应为「成对」系列，勿用「孪位/孪生/双生」'),
]


def score_B(row):
    """审校者 B 评分 → (score, reason)"""
    s = row.get('原文', '') or ''
    t = row.get('当前译文', '') or ''
    for pat, sc, why in B_FATAL:
        if re.search(pat, t):
            return sc, why
    for name, pat, zh in B_TERMS:
        if not re.search(pat, s, re.I):
            continue
        # 颜色渐变语境下 gradient ≠ 梯度，跳过（否则误伤「中心渐变」）
        if name == 'gradient' and COLOR_GRADIENT.search(s):
            continue
        if zh in t:
            continue
        # 术语对位缺规范词 → 轻微（可能是意译，不必然是错，需人复核）
        return 1, f'术语 {name} 的对位译文未出现规范词「{zh}」'
    return 0, ''


# ================================================================ 裁决
def adjudicate(row):
    """
    → (score_A, reason_A, score_B, reason_B, decision, decision_reason)
    裁决取两方更严的一档；化学术语以 B 为准。
    """
    sa, ra = score_A(row)
    sb, rb = score_B(row)
    if sb >= sa:
        dec, reason, by = sb, rb, 'B(化学)'
    else:
        dec, reason, by = sa, ra, 'A(中文)'
    detail = (reason + f'｜裁决依 {by}') if reason else ''
    return sa, ra, sb, rb, dec, detail


# ================================================================ 自检
def selftest():
    """
    对抗性测试：规则必须能抓到已知缺陷，且不误伤已知正确译文。
    返回 (通过数, 失败列表)。
    """
    MUST_CATCH = [
        ({'原文': 'Guess Type',   '当前译文': '猜测类型'},     'A', 10),
        ({'原文': 'Spin-Only Density', '当前译文': '仅自旋密度'}, 'A', 10),
        ({'原文': 'Spin-Only Density', '当前译文': '仅自旋密度'}, 'B', 10),
        ({'原文': 'Multiplicity', '当前译文': '重数'},         'B', 10),
        ({'原文': 'Some Text',    '当前译文': '这会会出问题'},   'A', 10),
        ({'原文': 'Some Text',    '当前译文': '错误：：参数'},    'A', 10),
        ({'原文': 'SCF Guess Print', '当前译文': 'SCF 猜测打印'}, 'A', 1),
        # geminal 的 4 种历史误译，B 侧必须逐一抓到
        ({'原文': 'Geminal',         '当前译文': '对偶'},          'B', 1),
        ({'原文': 'Geminal',         '当前译文': '孪位'},          'B', 10),
        ({'原文': 'Geminal Alpha %1', '当前译文': '孪生 Alpha %1'}, 'B', 10),
        ({'原文': 'Geminal(s):',     '当前译文': '双生轨道：'},     'B', 10),
        ({'原文': 'Geminal Orbitals', '当前译文': '对偶轨道'},      'B', 1),
        # 数学梯度仍必须抓到（排除逻辑不能把真阳性一起放掉）
        ({'原文': 'Gradient',         '当前译文': '渐变'},          'B', 1),
        # 真标签带句号仍须抓到（反向验证句号排除逻辑没放过头）
        ({'原文': 'Basis Set',        '当前译文': '基组。'},        'A', 1),
    ]
    MUST_PASS = [
        ({'原文': 'Functional Group', '当前译文': '官能团'},      'B'),
        ({'原文': 'Spin-Only Density', '当前译文': '纯自旋密度'},  'B'),
        ({'原文': 'Multiplicity',     '当前译文': '多重度'},      'B'),
        ({'原文': 'Thank you',        '当前译文': '谢谢'},        'A'),
        ({'原文': 'Basis',            '当前译文': '基组'},        'B'),
        ({'原文': 'Basis Function',   '当前译文': '基函数'},      'B'),
        # 定稿译法不得被自己的规则误伤
        ({'原文': 'Geminal',          '当前译文': '成对'},        'B'),
        ({'原文': 'Geminal Correlation', '当前译文': '成对相关'},  'B'),
        ({'原文': 'Geminal Orbitals', '当前译文': '成对轨道'},     'B'),
        ({'原文': 'Geminal Alpha %1', '当前译文': '成对 Alpha %1'}, 'B'),
        ({'原文': 'Geminal(s):',      '当前译文': '成对轨道：'},    'B'),
        # 颜色渐变 ≠ 数学梯度：gradient 规则必须放行颜色语境
        # （曾被全库回归抓到假阳性，见 2026-09-24 审校记录）
        ({'原文': 'Center Gradient',  '当前译文': '中心渐变'},     'B'),
        ({'原文': 'Color Gradient Editor', '当前译文': '颜色渐变编辑器'}, 'B'),
        # 完整句子的句号应保留（原文自带句号 → 不是标签）
        ({'原文': 'No results found.', '当前译文': '未找到匹配结果。'}, 'A'),
    ]
    fn = score_A if True else None  # noqa
    fails = []
    n = 0
    for row, who, expect in MUST_CATCH:
        got = score_A(row)[0] if who == 'A' else score_B(row)[0]
        n += 1
        if got < expect:
            fails.append(f'漏抓 [{who}] {row["当前译文"]!r}：期望 ≥{expect}，实得 {got}')
    for row, who in MUST_PASS:
        got = score_A(row)[0] if who == 'A' else score_B(row)[0]
        n += 1
        if got != 0:
            fails.append(f'误伤 [{who}] {row["当前译文"]!r}：期望 0，实得 {got}')
    return n - len(fails), fails


if __name__ == '__main__':
    ok, fails = selftest()
    print(f'规则自检：{ok} 通过 / {len(fails)} 失败')
    for f in fails:
        print('  ✗ ' + f)
    raise SystemExit(1 if fails else 0)
