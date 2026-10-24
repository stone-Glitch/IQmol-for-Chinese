#!/usr/bin/env bash
# ==============================================================================
# check_translations.sh —— 独立的翻译质量检查（不需要构建，秒级完成）
# ==============================================================================
#
# 与 verify_replay.sh 的区别
# ------------------------------------------------------------------------------
# verify_replay.sh  重量级：比对上游、跑构建、出完整报告，用于发布门
# check_translations.sh 轻量级：只看 .ts 文件，秒级完成，用于日常开发与 CI 门禁
#
# 检查项
# ------------------------------------------------------------------------------
#   [硬] 条目总数、context 数
#   [硬] unfinished（未译）
#   [硬] 空译文
#   [硬] 占位符不一致（%1 %2 %n 数量或编号不匹配）
#   [硬] HTML/富文本标签不成对
#   [硬] Q-Chem 关键字值被翻译（致命错误）
#   [软] 疑似未译（译文与原文完全相同且含英文单词）
#   [软] 首尾空格丢失
#   [软] 中文标点用了半角
#   [软] vanished 条目（需人工判断，不阻断）
#
# 用法
# ------------------------------------------------------------------------------
#   scripts/check_translations.sh
#   scripts/check_translations.sh translations/zh_CN.ts
#   scripts/check_translations.sh --strict          # 软错误也阻断
#   scripts/check_translations.sh --json            # 机器可读输出
#   scripts/check_translations.sh --limit 20        # 每条问题最多列 20 个
#   scripts/check_translations.sh --quiet           # 只输出结论
#
# 退出码
# ------------------------------------------------------------------------------
#   0  PASS              无硬错误（--strict 时还要求无软错误）
#   1  FAIL              存在硬错误（或 --strict 下存在软错误）
#   5  ENV               文件不存在 / python3 不可用 / 参数错误
#
# 依赖：bash、python3（深度检查）；无 python3 时自动降级为 grep 粗查
#
# ==============================================================================

set -uo pipefail

SCRIPT_NAME="$(basename "$0")"
EXIT_PASS=0; EXIT_FAIL=1; EXIT_ENV=5

# ---------- 参数 ----------
TS=""
STRICT=0
JSON=0
QUIET=0
LIMIT=15

while [ $# -gt 0 ]; do
    case "$1" in
        --strict)  STRICT=1; shift   ;;
        --json)    JSON=1;   shift   ;;
        --quiet)   QUIET=1;  shift   ;;
        --limit)   LIMIT="$2"; shift 2 ;;
        -h|--help) sed -n '2,45p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
        -*)        echo "[$SCRIPT_NAME] 未知参数：$1" >&2; exit ${EXIT_ENV} ;;
        *)         [ -z "$TS" ] && { TS="$1"; shift; } || { echo "[$SCRIPT_NAME] 多余参数：$1" >&2; exit ${EXIT_ENV}; } ;;
    esac
done

# ---------- 定位 ts 文件 ----------
if [ -z "$TS" ]; then
    ROOT="$(cd "$(dirname "$0")/.." && pwd)"
    TS="$ROOT/translations/zh_CN.ts"
else
    ROOT="$(cd "$(dirname "$0")/.." && pwd)"
    [ -f "$TS" ] || TS="$ROOT/$TS"
fi

[ -f "$TS" ] || { echo "[$SCRIPT_NAME] 找不到翻译文件：$TS" >&2; exit ${EXIT_ENV}; }

HAVE_PY3=0
command -v python3 >/dev/null 2>&1 && HAVE_PY3=1

# ==============================================================================
# 检查主体（python3 路径：精确，基于 XML 解析）
# ==============================================================================
run_checks_py() {
python3 - "$TS" "$STRICT" "$LIMIT" "$JSON" "$QUIET" <<'PY'
import re, sys, json
import xml.etree.ElementTree as ET

ts_path, strict, limit, as_json, quiet = (
    sys.argv[1], sys.argv[2] == '1', int(sys.argv[3]), sys.argv[4] == '1', sys.argv[5] == '1')

# 中文字符检测
KEYWORD_RE = re.compile(r'[一-鿿]')

# 技术 token 形态：全大写/含下划线/纯 ASCII 符号，典型如 B3LYP、SCF_CONVERGENCE
# 这类字符串本来就不该翻译，译文等于原文是正确行为，不能算"疑似未译"
def is_tech_token(s):
    s = s.strip()
    if len(s) < 2 or ' ' in s:
        return False
    return bool(re.fullmatch(r'[A-Z0-9_\-\*\(\)\.]+', s))

try:
    root = ET.parse(ts_path).getroot()
except Exception as e:
    print(f"XML 解析失败：{e}", file=sys.stderr)
    sys.exit(5)

messages = []
contexts = 0
for ctx in root.iter('context'):
    contexts += 1
    cname = ctx.findtext('name') or ''
    for m in ctx.iter('message'):
        src = m.findtext('source') or ''
        tr_el = m.find('translation')
        tr = tr_el.text or '' if tr_el is not None else ''
        ttype = tr_el.get('type') if tr_el is not None else None
        locs = [ (l.get('filename'), l.get('line')) for l in m.iter('location') ]
        messages.append({'ctx': cname, 'src': src, 'tr': tr, 'type': ttype, 'loc': locs})

total = len(messages)
unfinished = sum(1 for m in messages if m['type'] == 'unfinished')
vanished   = sum(1 for m in messages if m['type'] == 'vanished')
empty      = sum(1 for m in messages if m['type'] != 'unfinished' and m['tr'].strip() == '')

hard, soft = [], []

for m in messages:
    s, t, ty = m['src'], m['tr'], m['type']
    if ty in ('unfinished', 'vanished'):
        continue
    where = f"{m['ctx']}"
    if m['loc']:
        where += f" ({m['loc'][0][0]}:{m['loc'][0][1]})"

    # 占位符不一致
    ps = sorted(re.findall(r'%(\d+|n)', s))
    pt = sorted(re.findall(r'%(\d+|n)', t))
    if ps != pt:
        hard.append(('占位符不一致', where, s, f"源={ps} 译={pt}"))
        continue

    # HTML 标签
    ts_ = sorted(re.findall(r'</?([a-zA-Z]+)[^>]*/?>', s))
    tt_ = sorted(re.findall(r'</?([a-zA-Z]+)[^>]*/?>', t))
    if ts_ != tt_:
        hard.append(('标签不一致', where, s, f"源={ts_} 译={tt_}"))
        continue

    # 致命：源串是技术 token（Q-Chem 关键字值），译文却含中文
    if is_tech_token(s) and KEYWORD_RE.search(t):
        hard.append(('疑似翻译了关键字值', where, s, f"译={t}"))
        continue

    # 软：疑似未译（译文与原文相同且含英文单词）
    # 豁免技术 token —— 它们本就应保持英文
    if t and t == s and re.search(r'[A-Za-z]{3,}', s) and not is_tech_token(s):
        soft.append(('疑似未译', where, s, '译文与原文相同'))
        continue

    # 软：首尾空格丢失
    if s != t and (s != s.strip() or t != t.strip()):
        if s.startswith(' ') != t.startswith(' ') or s.endswith(' ') != t.endswith(' '):
            soft.append(('首尾空格变化', where, repr(s), repr(t)))
            continue

    # 软：中文句子里出现半角逗号/句号
    if KEYWORD_RE.search(t) and re.search(r'[一-鿿][,;!?][一-鿿]', t):
        soft.append(('半角标点', where, t, '中文语境建议用全角'))
        continue

# ---------- 输出 ----------
if as_json:
    print(json.dumps({
        'file': ts_path,
        'total': total, 'contexts': contexts,
        'unfinished': unfinished, 'vanished': vanished, 'empty': empty,
        'hard_count': len(hard), 'soft_count': len(soft),
        'hard': [{'kind': k, 'where': w, 'src': s, 'detail': d} for k, w, s, d in hard[:limit]],
        'soft': [{'kind': k, 'where': w, 'src': s, 'detail': d} for k, w, s, d in soft[:limit]],
    }, ensure_ascii=False, indent=2))
elif quiet:
    # --quiet：一行统计，适合 commit hook / 流水线
    print(f"total={total} contexts={contexts} unfinished={unfinished} "
          f"vanished={vanished} empty={empty} hard={len(hard)} soft={len(soft)}")
else:
    print("=" * 62)
    print(f" 翻译质量检查：{ts_path}")
    print("=" * 62)
    print(f"条目总数        : {total}")
    print(f"context 数      : {contexts}")
    print(f"unfinished      : {unfinished}")
    print(f"vanished        : {vanished}   (需人工判断，不阻断)")
    print(f"空译文          : {empty}")
    print()

    print("-- 硬错误 --")
    if hard:
        for k, w, s, d in hard[:limit]:
            print(f"  [{k}] {w}")
            print(f"      源: {s[:70]}")
            print(f"      {d}")
        if len(hard) > limit:
            print(f"  ... 另有 {len(hard)-limit} 条")
    else:
        print("  无")
    print(f"  合计 {len(hard)} 条")
    print()

    print("-- 软提示 --")
    if soft:
        for k, w, s, d in soft[:limit]:
            print(f"  [{k}] {w}")
            print(f"      源: {s[:70]}")
            print(f"      {d}")
        if len(soft) > limit:
            print(f"  ... 另有 {len(soft)-limit} 条")
    else:
        print("  无")
    print(f"  合计 {len(soft)} 条")
    print()

    print("=" * 62)
    if unfinished or empty or hard:
        print("结论 : FAIL（存在硬错误）")
    elif strict and soft:
        print("结论 : FAIL（--strict 模式下软提示也阻断）")
    else:
        print("结论 : PASS")
    if vanished:
        print(f"注意 : 有 {vanished} 条 vanished，请人工确认是已删除还是解析失败")
    print("=" * 62)

if unfinished or empty or hard:
    sys.exit(1)
if strict and soft:
    sys.exit(1)
sys.exit(0)
PY
}

# ==============================================================================
# 降级路径（无 python3：只用 grep 粗查，能力有限但保证不卡死 CI）
# ==============================================================================
run_checks_sh() {
    local total contexts unf van empty
    total=$(grep -c '<message' "$TS")
    contexts=$(grep -c '<context>' "$TS")
    unf=$(grep -c 'type="unfinished"' "$TS")
    van=$(grep -c 'type="vanished"' "$TS")
    empty=$(grep -c '<translation></translation>' "$TS")

    echo "=============================================================="
    echo " 翻译质量检查（降级模式：python3 不可用，仅粗查）"
    echo "=============================================================="
    echo "条目总数   : $total"
    echo "context 数 : $contexts"
    echo "unfinished : $unf"
    echo "vanished   : $van"
    echo "空译文     : $empty"
    echo
    echo "⚠️ 未执行：占位符一致性、HTML 标签、关键字值误译检查"
    echo "   请安装 python3 以获得完整检查"
    echo "=============================================================="

    if [ "$unf" -ne 0 ] || [ "$empty" -ne 0 ]; then
        echo "结论 : FAIL"
        return 1
    fi
    echo "结论 : PASS"
    return 0
}

# ==============================================================================
# 主流程
# ==============================================================================
if [ "$HAVE_PY3" -eq 1 ]; then
    run_checks_py
    rc=$?
else
    run_checks_sh
    rc=$?
fi

# --quiet：详细统计由 python 输出一行，这里只补一句 PASS/FAIL
if [ "$QUIET" -eq 1 ] && [ "$JSON" -eq 0 ]; then
    [ "$rc" -eq 0 ] && echo "PASS" || echo "FAIL"
fi

exit $rc
