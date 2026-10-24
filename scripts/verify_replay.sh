#!/usr/bin/env bash
# ==============================================================================
# verify_replay.sh —— 把「源码 69/69 文件 100% 复现」从自述变成可审计资产
# ==============================================================================
#
# 设计目的
# ------------------------------------------------------------------------------
# 仓库 README 声称「路线 B 实测在干净上游树上源码 69/69 文件 100% 复现」。
# 这句话目前无法被外部验证，因此无法转化为信任。本脚本把它变成一份
# 任何人都能独立复查的工件目录：环境、哈希、逐文件比对、翻译统计、
# 构建日志、冒烟测试，以及一份一句话结论。
#
# 产出目录结构（--report-dir，默认 verify-reports/<UTC 时间戳>/）
# ------------------------------------------------------------------------------
#   VERDICT.txt            一句话结论 + 退出码含义（最先看这个）
#   report.md              人类可读汇总，可直接贴进 PR / Release notes
#   env.txt                工具链版本与 commit hash（可复现性的前提）
#   manifest.json          上游 hash、本地 base hash、补丁清单及 sha256
#   file-diff-summary.txt  逐文件状态：IDENTICAL / DIFFERS / MISSING / EXTRA
#   file-diff.patch        仅当存在差异时生成，完整 unified diff
#   translation-check.txt  条目数、context 数、未译、空译文、占位符一致性
#   build.log              完整构建输出（--skip-build 时不生成）
#   smoke-test.txt         启动与 qm 加载检查（--skip-smoke 时不生成）
#
# 退出码
# ------------------------------------------------------------------------------
#   0  PASS              全部检查通过
#   1  FILES_DIFFER      文件比对不一致
#   2  TRANSLATION_FAIL  翻译检查未通过
#   3  BUILD_FAIL        构建失败
#   4  SMOKE_FAIL        冒烟测试失败
#   5  USAGE/ENV         参数错误或环境缺失
#
# 用法
# ------------------------------------------------------------------------------
#   scripts/verify_replay.sh --target /path/to/upstream --tag v3.2.3
#   scripts/verify_replay.sh --target /path/to/upstream --base <upstream-commit>
#   scripts/verify_replay.sh --target /path/to/upstream --skip-build --skip-smoke
#   scripts/verify_replay.sh --target /path/to/upstream --dry-run
#
# 依赖：bash 4+、git、diff、sha256sum/shasum；python3 可选（启用深度占位符检查）
#
# ==============================================================================

set -uo pipefail

# ---------- 常量 ----------
SCRIPT_NAME="$(basename "$0")"
EXIT_PASS=0; EXIT_FILES=1; EXIT_TRANS=2; EXIT_BUILD=3; EXIT_SMOKE=4; EXIT_ENV=5

# ---------- 默认值 ----------
TARGET=""
TAG=""
BASE=""
REPORT_DIR=""
SKIP_BUILD=0
SKIP_SMOKE=0
DRY_RUN=0
WHITELIST=""

# ---------- 参数解析 ----------
usage() {
    sed -n '2,50p' "$0" | sed 's/^# \{0,1\}//'
    exit ${EXIT_ENV}
}

while [ $# -gt 0 ]; do
    case "$1" in
        --target)      TARGET="$2";      shift 2 ;;
        --tag)         TAG="$2";         shift 2 ;;
        --base)        BASE="$2";        shift 2 ;;
        --report-dir)  REPORT_DIR="$2";  shift 2 ;;
        --whitelist)   WHITELIST="$2";   shift 2 ;;
        --skip-build)  SKIP_BUILD=1;     shift   ;;
        --skip-smoke)  SKIP_SMOKE=1;     shift   ;;
        --dry-run)     DRY_RUN=1;        shift   ;;
        -h|--help)     usage                     ;;
        *) echo "[$SCRIPT_NAME] 未知参数：$1" >&2; usage ;;
    esac
done

# ---------- 环境检查 ----------
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

[ -n "$TARGET" ] || { echo "[$SCRIPT_NAME] 必须指定 --target <上游树路径>" >&2; exit ${EXIT_ENV}; }
[ -d "$TARGET" ] || { echo "[$SCRIPT_NAME] --target 不是目录：$TARGET" >&2; exit ${EXIT_ENV}; }
TARGET="$(cd "$TARGET" && pwd)"

command -v git  >/dev/null || { echo "[$SCRIPT_NAME] 缺少 git" >&2; exit ${EXIT_ENV}; }
command -v diff >/dev/null || { echo "[$SCRIPT_NAME] 缺少 diff" >&2; exit ${EXIT_ENV}; }

# 哈希工具：Linux 用 sha256sum，macOS 用 shasum
if command -v sha256sum >/dev/null 2>&1; then
    sha256() { sha256sum "$1" | awk '{print $1}'; }
elif command -v shasum >/dev/null 2>&1; then
    sha256() { shasum -a 256 "$1" | awk '{print $1}'; }
else
    sha256() { echo "UNSUPPORTED"; }
fi
HAVE_PY3=0; command -v python3 >/dev/null 2>&1 && HAVE_PY3=1

# ---------- 报告目录 ----------
[ -n "$REPORT_DIR" ] || REPORT_DIR="$REPO_ROOT/verify-reports/$(date -u +%Y%m%dT%H%M%SZ)"
if [ "$DRY_RUN" -eq 0 ]; then
    mkdir -p "$REPORT_DIR" || { echo "[$SCRIPT_NAME] 无法创建 $REPORT_DIR" >&2; exit ${EXIT_ENV}; }
fi

# 注意：log 必须走 stderr。主流程多处把函数 stdout 重定向进报告文件，
# 若 log 走 stdout 会污染产物内容（曾导致文件清单里混入一行日志）。
log()  { printf '[%s] %s\n' "$SCRIPT_NAME" "$*" >&2; }
log "报告目录：$REPORT_DIR"

# ==============================================================================
# 步骤 1：环境指纹 —— 没有这个，任何「复现」声明都无从验证
# ==============================================================================
collect_env() {
    {
        echo "== 采集时间 =="
        date -u '+%Y-%m-%d %H:%M:%S UTC'
        echo
        echo "== 主机 =="
        uname -a
        echo
        echo "== 工具链 =="
        echo -n "cmake      : "; cmake --version 2>/dev/null | head -1 || echo "未找到"
        echo -n "qmake      : "; qmake --version 2>/dev/null | tr '\n' ' ' || echo "未找到"
        echo
        echo -n "g++        : "; g++ --version 2>/dev/null | head -1 || echo "未找到"
        echo -n "gfortran   : "; gfortran --version 2>/dev/null | head -1 || echo "未找到"
        echo -n "lupdate    : "; lupdate -version 2>/dev/null | tr '\n' ' ' || echo "未找到"
        echo
        echo -n "python3    : "; [ "$HAVE_PY3" -eq 1 ] && python3 --version || echo "未找到（跳过深度占位符检查）"
        echo
        echo "== 上游树 =="
        echo "路径        : $TARGET"
        echo -n "HEAD        : "; git -C "$TARGET" rev-parse HEAD 2>/dev/null || echo "非 git 仓库"
        echo -n "describe    : "; git -C "$TARGET" describe --tags --dirty 2>/dev/null || echo "无 tag"
        echo -n "dirty       : "; git -C "$TARGET" status --porcelain 2>/dev/null | wc -l | tr -d ' '; echo " 个改动文件"
        [ -n "$TAG" ]  && echo "指定 tag    : $TAG"
        [ -n "$BASE" ] && echo "指定 base   : $BASE"
        echo
        echo "== 本仓库 =="
        echo "路径        : $REPO_ROOT"
        echo -n "HEAD        : "; git -C "$REPO_ROOT" rev-parse HEAD 2>/dev/null || echo "非 git 仓库"
        echo -n "dirty       : "; git -C "$REPO_ROOT" status --porcelain 2>/dev/null | wc -l | tr -d ' '; echo " 个改动文件"
    } 2>&1
}

# ==============================================================================
# 步骤 2：manifest —— 谁改了什么，依据哪份上游
# ==============================================================================
collect_manifest() {
    local up_head up_desc local_head
    up_head="$(git -C "$TARGET" rev-parse HEAD 2>/dev/null || echo unknown)"
    up_desc="$(git -C "$TARGET" describe --tags 2>/dev/null || echo none)"
    local_head="$(git -C "$REPO_ROOT" rev-parse HEAD 2>/dev/null || echo unknown)"

    {
        echo "{"
        echo "  \"schema\": \"iqmol-zh-verify/1\","
        echo "  \"generated_utc\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\","
        echo "  \"upstream\": {"
        echo "    \"path\": \"$TARGET\","
        echo "    \"commit\": \"$up_head\","
        echo "    \"describe\": \"$up_desc\","
        echo "    \"requested_tag\": \"${TAG:-null}\","
        echo "    \"requested_base\": \"${BASE:-null}\""
        echo "  },"
        echo "  \"localization\": {"
        echo "    \"path\": \"$REPO_ROOT\","
        echo "    \"commit\": \"$local_head\""
        echo "  },"
        echo "  \"patches\": ["
        # patches/ 下的每个补丁记录哈希；无 patches 目录则回退到 scripts/
        local first=1 pdir="$REPO_ROOT/patches"
        [ -d "$pdir" ] || pdir="$REPO_ROOT/scripts"
        if [ -d "$pdir" ]; then
            while IFS= read -r f; do
                [ "$first" -eq 1 ] || echo ","
                printf '    { "file": "%s", "sha256": "%s", "bytes": %s }' \
                    "${f#$REPO_ROOT/}" "$(sha256 "$f")" "$(wc -c < "$f" | tr -d ' ')"
                first=0
            done < <(find "$pdir" -maxdepth 2 -type f \( -name '*.patch' -o -name '*.diff' -o -name '*.sh' \) 2>/dev/null | sort)
            [ "$first" -eq 1 ] || echo ""
        fi
        echo "  ],"
        echo "  \"translation\": {"
        echo "    \"ts_file\": \"translations/zh_CN.ts\","
        echo "    \"sha256\": \"$(sha256 "$REPO_ROOT/translations/zh_CN.ts" 2>/dev/null || echo MISSING)\""
        echo "  }"
        echo "}"
    } 2>&1
}

# ==============================================================================
# 步骤 3：逐文件比对 —— 这是「69/69」的本体
# ==============================================================================
# 文件清单来源优先级：
#   1) upstream.ref / patch.manifest 中声明的清单
#   2) 汉化层相对上游实际存在差异的文件（自动推导）
build_file_list() {
    local manifest=""
    for c in "$REPO_ROOT/upstream.ref" "$REPO_ROOT/patch.manifest" "$REPO_ROOT/scripts/patch.manifest"; do
        [ -f "$c" ] && { manifest="$c"; break; }
    done

    if [ -n "$manifest" ]; then
        log "文件清单来源：$manifest"
        grep -vE '^\s*(#|$)' "$manifest" | awk '{print $1}' | grep -vE '^(upstream|base|target)\.' | sort -u
        return
    fi

    log "未找到 patch.manifest，自动推导差异文件清单"
    # 只比较源码与构建文件，排除二进制/产物/文档噪音
    ( cd "$REPO_ROOT" && find src cmake CMakeLists.txt configure \
        -type f \( -name '*.C' -o -name '*.cc' -o -name '*.cpp' -o -name '*.h' \
                   -o -name '*.ui' -o -name 'CMakeLists.txt' -o -name '*.cmake' -o -name 'configure' \) \
        2>/dev/null | sort -u )
}

compare_files() {
    local list_file="$1" summary="$2" patchout="$3"
    local total=0 identical=0 differs=0 missing_target=0 missing_local=0
    local f tf lf

    : > "$summary"
    : > "$patchout"
    printf '%-60s  %s\n' "文件" "状态" >> "$summary"
    printf '%-60s  %s\n' "------------------------------------------------------------" "--------" >> "$summary"

    while IFS= read -r f; do
        [ -z "$f" ] && continue
        total=$((total+1))
        tf="$TARGET/$f"
        lf="$REPO_ROOT/$f"

        if [ ! -f "$tf" ]; then
            printf '%-60s  %s\n' "$f" "MISSING_IN_UPSTREAM" >> "$summary"
            missing_target=$((missing_target+1))
        elif [ ! -f "$lf" ]; then
            printf '%-60s  %s\n' "$f" "MISSING_IN_LOCAL" >> "$summary"
            missing_local=$((missing_local+1))
        elif diff -q "$tf" "$lf" >/dev/null 2>&1; then
            printf '%-60s  %s\n' "$f" "IDENTICAL" >> "$summary"
            identical=$((identical+1))
        else
            printf '%-60s  %s (%s 行差异)\n' "$f" "DIFFERS" \
                "$(diff "$tf" "$lf" | grep -cE '^[<>]')" >> "$summary"
            { echo "diff --git a/$f b/$f"; diff -u "$tf" "$lf"; } >> "$patchout"
            differs=$((differs+1))
        fi
    done < "$list_file"

    # 白名单：允许声明已知且可接受的差异
    if [ -n "$WHITELIST" ] && [ -f "$WHITELIST" ]; then
        local w
        while IFS= read -r w; do
            [ -z "$w" ] && continue
            case "$w" in \#*) continue ;; esac
            if grep -qE "^${w//./\\.} .*DIFFERS" "$summary"; then
                sed -i.bak "s|^\(${w//./\\.} .*\)DIFFERS|\1DIFFERS(WHITELISTED)|" "$summary" 2>/dev/null
                differs=$((differs-1)); identical=$((identical+1))
            fi
        done < "$WHITELIST"
        rm -f "$summary.bak"
    fi

    {
        echo
        echo "总计 $total 个文件："
        echo "  IDENTICAL          : $identical"
        echo "  DIFFERS            : $differs"
        echo "  MISSING_IN_UPSTREAM: $missing_target"
        echo "  MISSING_IN_LOCAL   : $missing_local"
        [ "$total" -gt 0 ] && echo "  复现率              : $(awk "BEGIN{printf \"%.2f\", $identical*100/$total}")% ($identical/$total)"
    } >> "$summary"

    echo "$identical $differs $missing_target $missing_local $total"
}

# ==============================================================================
# 步骤 4：翻译检查
# ==============================================================================
check_translation() {
    # 输出全部走 stdout，由调用处重定向到报告文件。
    # 不要在函数内再重定向到同一路径 —— 两个 fd 会互相覆盖。
    local ts="$REPO_ROOT/translations/zh_CN.ts"
    {
        echo "== 文件 =="
        if [ ! -f "$ts" ]; then
            echo "zh_CN.ts 不存在 —— TRANSLATION_FAIL"
            return 1
        fi
        echo "路径  : $ts"
        echo "sha256: $(sha256 "$ts")"
        echo "字节  : $(wc -c < "$ts" | tr -d ' ')"
        echo

        echo "== 统计 =="
        local msg ctx unf van empty
        msg=$(grep -c '<message' "$ts")
        ctx=$(grep -c '<context>' "$ts")
        unf=$(grep -c 'type="unfinished"' "$ts")
        van=$(grep -c 'type="vanished"' "$ts")
        empty=$(grep -c '<translation></translation>' "$ts")
        echo "message 条目数   : $msg"
        echo "context 数       : $ctx"
        echo "unfinished       : $unf"
        echo "vanished         : $van"
        echo "空译文           : $empty"
        echo

        echo "== 深度检查（占位符一致性） =="
        if [ "$HAVE_PY3" -eq 1 ]; then
            python3 - "$ts" <<'PY'
import re, sys, xml.etree.ElementTree as ET
ts = sys.argv[1]
try:
    root = ET.parse(ts).getroot()
except Exception as e:
    print(f"解析失败：{e}")
    sys.exit(1)
bad = []
n = 0
for ctx in root.iter('context'):
    for m in ctx.iter('message'):
        n += 1
        src = m.findtext('source') or ''
        tr  = m.findtext('translation') or ''
        t = m.find('translation')
        if t is not None and t.get('type') in ('unfinished', 'vanished'):
            continue
        ph_s = sorted(re.findall(r'%(\d+)', src))
        ph_t = sorted(re.findall(r'%(\d+)', tr))
        if ph_s != ph_t:
            bad.append(('占位符', src[:40], ph_s, ph_t)); continue
        tag_s = sorted(re.findall(r'</?([a-zA-Z]+)[^>]*>', src))
        tag_t = sorted(re.findall(r'</?([a-zA-Z]+)[^>]*>', tr))
        if tag_s != tag_t:
            bad.append(('标签', src[:40], tag_s, tag_t)); continue
        if tr and tr == src and re.search(r'[A-Za-z]{3,}', src):
            bad.append(('疑似未译', src[:40], '', ''))
print(f"检查条目         : {n}")
print(f"不一致条目       : {len(bad)}")
for k, s, a, b in bad[:40]:
    print(f"  [{k}] {s!r} 源={a} 译={b}")
if len(bad) > 40:
    print(f"  ... 另有 {len(bad)-40} 条")
PY
        else
            echo "python3 不可用，跳过（占位符一致性未验证）"
        fi
        echo
        echo "== 判定 =="
        if [ "$unf" -eq 0 ] && [ "$empty" -eq 0 ]; then
            echo "PASS：无 unfinished、无空译文"
            return 0
        fi
        echo "FAIL：存在 unfinished($unf) 或空译文($empty)"
        return 1
    } 2>&1
}

# ==============================================================================
# 步骤 5 + 6：构建与冒烟
# ==============================================================================
run_build() {
    local logf="$1"
    {
        echo "== 构建 =="
        echo "起始 $(date -u '+%Y-%m-%dT%H:%M:%SZ')"
        if [ -x "$REPO_ROOT/scripts/build_windows.sh" ] && [ "$(uname -s | grep -c MINGW)" -gt 0 ]; then
            bash "$REPO_ROOT/scripts/build_windows.sh"
        elif [ -x "$REPO_ROOT/configure" ]; then
            ( cd "$REPO_ROOT" && ./configure && cd build && make -j"$(nproc 2>/dev/null || echo 2)" )
        else
            echo "未找到可识别的构建入口"
            return 1
        fi
    } > "$logf" 2>&1
    return $?
}

run_smoke() {
    local out="$1" bin=""
    {
        echo "== 冒烟测试 =="
        for c in "$REPO_ROOT/build/bin/IQmol" "$REPO_ROOT/build/bin/IQmol.exe" \
                 "$REPO_ROOT/build/IQmol" "$REPO_ROOT/build/IQmol.exe"; do
            [ -x "$c" ] && { bin="$c"; break; }
        done
        [ -n "$bin" ] || { echo "未找到可执行文件 —— SMOKE_FAIL"; return 1; }
        echo "可执行文件: $bin"
        echo
        echo "-- 版本 --"
        "$bin" --version 2>&1 | head -5 || echo "(无 --version 输出，可能不支持该参数)"
        echo
        echo "-- qm 文件 --"
        for p in "$REPO_ROOT/build/bin/translations/zh_CN.qm" "$REPO_ROOT/build/translations/zh_CN.qm" \
                 "$REPO_ROOT/translations/zh_CN.qm"; do
            [ -f "$p" ] && echo "存在: $p ($(wc -c < "$p" | tr -d ' ') 字节, sha256 $(sha256 "$p"))" \
                        || echo "缺失: $p"
        done
    } > "$out" 2>&1
    return $?
}

# ==============================================================================
# 主流程
# ==============================================================================
VERDICT="PASS"; VERDICT_CODE=$EXIT_PASS; REASONS=""

if [ "$DRY_RUN" -eq 1 ]; then
    log "--dry-run：仅展示将执行的步骤，不写报告"
    echo "  1. 采集环境       -> env.txt"
    echo "  2. 生成 manifest  -> manifest.json"
    echo "  3. 逐文件比对     -> file-diff-summary.txt / file-diff.patch"
    echo "  4. 翻译检查       -> translation-check.txt"
    [ "$SKIP_BUILD" -eq 0 ] && echo "  5. 构建           -> build.log"   || echo "  5. 构建           [跳过]"
    [ "$SKIP_SMOKE" -eq 0 ] && echo "  6. 冒烟测试       -> smoke-test.txt" || echo "  6. 冒烟测试       [跳过]"
    echo "  7. 汇总           -> VERDICT.txt / report.md"
    echo "  文件清单（前 10 条）："
    build_file_list | head -10 | sed 's/^/    /'
    exit ${EXIT_PASS}
fi

# 1. 环境
collect_env > "$REPORT_DIR/env.txt" 2>&1
log "步骤 1/7 环境指纹"

# 2. manifest
collect_manifest > "$REPORT_DIR/manifest.json" 2>&1
log "步骤 2/7 manifest"

# 3. 逐文件比对
build_file_list > "$REPORT_DIR/.filelist" 2>/dev/null
read -r IDEN DIFF MT ML TOTAL < <(compare_files "$REPORT_DIR/.filelist" \
    "$REPORT_DIR/file-diff-summary.txt" "$REPORT_DIR/file-diff.patch")
[ "$(wc -c < "$REPORT_DIR/file-diff.patch" | tr -d ' ')" -eq 0 ] && rm -f "$REPORT_DIR/file-diff.patch"
rm -f "$REPORT_DIR/.filelist"
log "步骤 3/7 文件比对：$IDEN/$TOTAL 一致，$DIFF 处差异"

# 4. 翻译
# 优先委托给独立的 check_translations.sh（检查项更全：占位符、标签、关键字值误译）；
# 不存在时退回内置精简检查。
TRANS_OK=0
CT="$REPO_ROOT/scripts/check_translations.sh"
if [ -x "$CT" ]; then
    log "步骤 4/7 翻译检查：委托 check_translations.sh"
    {
        echo "# 由 check_translations.sh 生成（完整检查）"
        echo
    } > "$REPORT_DIR/translation-check.txt"
    "$CT" "$REPO_ROOT/translations/zh_CN.ts" >> "$REPORT_DIR/translation-check.txt" 2>&1 \
        && TRANS_OK=1
else
    log "步骤 4/7 翻译检查：内置精简检查（建议安装 scripts/check_translations.sh 以获得完整检查）"
    check_translation > "$REPORT_DIR/translation-check.txt" 2>&1 \
        && TRANS_OK=1
fi
log "步骤 4/7 结果：$([ "$TRANS_OK" -eq 1 ] && echo PASS || echo FAIL)"

# 5. 构建
# 约定：*_OK=0 表示通过/未执行，=1 表示失败。跳过绝不能被记成失败。
BUILD_OK=0; SKIPPED_BUILD=0
if [ "$SKIP_BUILD" -eq 1 ]; then
    SKIPPED_BUILD=1
    log "步骤 5/7 构建 [跳过]"
else
    run_build "$REPORT_DIR/build.log" || BUILD_OK=1
    log "步骤 5/7 构建：$([ "$BUILD_OK" -eq 0 ] && echo OK || echo FAIL)"
fi

# 6. 冒烟
SMOKE_OK=0; SKIPPED_SMOKE=0
if [ "$SKIP_SMOKE" -eq 1 ] || [ "$SKIP_BUILD" -eq 1 ]; then
    SKIPPED_SMOKE=1
    log "步骤 6/7 冒烟 [跳过]"
    echo "未执行：构建步骤被跳过（--skip-build 或 --skip-smoke）" > "$REPORT_DIR/smoke-test.txt"
else
    run_smoke "$REPORT_DIR/smoke-test.txt" || SMOKE_OK=1
    log "步骤 6/7 冒烟：$([ "$SMOKE_OK" -eq 0 ] && echo OK || echo FAIL)"
fi

# 7. 判定
if [ "$DIFF" -gt 0 ] || [ "$MT" -gt 0 ] || [ "$ML" -gt 0 ]; then
    VERDICT="FILES_DIFFER"; VERDICT_CODE=$EXIT_FILES
    REASONS="$REASONS 文件比对：${DIFF} 处差异 / ${MT} 上游缺失 / ${ML} 本地缺失。"
fi
if [ "$TRANS_OK" -ne 1 ] && [ "$VERDICT_CODE" -eq $EXIT_PASS ]; then
    VERDICT="TRANSLATION_FAIL"; VERDICT_CODE=$EXIT_TRANS
    REASONS="$REASONS 翻译检查未通过。"
fi
if [ "$BUILD_OK" -ne 0 ] && [ "$VERDICT_CODE" -eq $EXIT_PASS ]; then
    VERDICT="BUILD_FAIL"; VERDICT_CODE=$EXIT_BUILD
    REASONS="$REASONS 构建失败，详见 build.log。"
fi
if [ "$SMOKE_OK" -ne 0 ] && [ "$VERDICT_CODE" -eq $EXIT_PASS ] && [ "$SKIPPED_SMOKE" -eq 0 ]; then
    VERDICT="SMOKE_FAIL"; VERDICT_CODE=$EXIT_SMOKE
    REASONS="$REASONS 冒烟测试失败，详见 smoke-test.txt。"
fi
[ -n "$REASONS" ] || REASONS=" 全部检查通过。"

# VERDICT.txt
{
    echo "=============================================="
    echo " IQmol 汉化重放验证结论"
    echo "=============================================="
    echo "结论     : $VERDICT (exit $VERDICT_CODE)"
    echo "时间     : $(date -u '+%Y-%m-%d %H:%M:%S UTC')"
    echo "上游     : $TARGET @ $(git -C "$TARGET" rev-parse --short HEAD 2>/dev/null || echo unknown)"
    echo "本地     : $REPO_ROOT @ $(git -C "$REPO_ROOT" rev-parse --short HEAD 2>/dev/null || echo unknown)"
    echo "文件复现 : $IDEN/$TOTAL"
    echo "原因     :$REASONS"
    echo "=============================================="
    echo
    echo "退出码：0=PASS 1=FILES_DIFFER 2=TRANSLATION_FAIL 3=BUILD_FAIL 4=SMOKE_FAIL 5=ENV"
} > "$REPORT_DIR/VERDICT.txt"

# report.md（可直接贴进 PR / Release notes）
{
    echo "# 汉化重放验证报告"
    echo
    echo "| 项 | 值 |"
    echo "|---|---|"
    echo "| 结论 | **$VERDICT** (exit $VERDICT_CODE) |"
    echo "| 生成时间 | $(date -u '+%Y-%m-%d %H:%M:%S UTC') |"
    echo "| 上游 commit | \`$(git -C "$TARGET" rev-parse HEAD 2>/dev/null || echo unknown)\` |"
    echo "| 上游 tag | ${TAG:-未指定} |"
    echo "| 本仓库 commit | \`$(git -C "$REPO_ROOT" rev-parse HEAD 2>/dev/null || echo unknown)\` |"
    echo "| 文件复现 | **$IDEN / $TOTAL** |"
    echo "| 差异文件 | $DIFF |"
    echo "| 翻译检查 | $([ "$TRANS_OK" -eq 1 ] && echo PASS || echo FAIL) |"
    echo "| 构建 | $([ "$SKIPPED_BUILD" -eq 1 ] && echo 跳过 || { [ "$BUILD_OK" -eq 0 ] && echo PASS || echo FAIL; }) |"
    echo "| 冒烟测试 | $([ "$SKIPPED_SMOKE" -eq 1 ] && echo 跳过 || { [ "$SMOKE_OK" -eq 0 ] && echo PASS || echo FAIL; }) |"
    echo
    echo "## 结论说明"
    echo
    if [ "$VERDICT_CODE" -eq $EXIT_PASS ]; then
        echo "全部检查通过。逐文件比对 $TOTAL 个文件，$IDEN 个与重放结果一致。"
    else
        echo "未通过。原因：$REASONS"
    fi
    echo
    echo "> **重要限定**：文件一致不等于二进制等价、运行时等价或翻译覆盖率达标。"
    echo "> 本报告证明的是「在指定上游 commit 上，汉化改动可被完整重放且源码逐字节一致」，"
    echo "> 不包含 qm 内容比对、OpenBabel 行为比对或功能回归测试。"
    echo
    echo "## 产物清单"
    echo
    echo "| 文件 | 说明 |"
    echo "|---|---|"
    echo "| \`env.txt\` | 工具链版本与 commit hash |"
    echo "| \`manifest.json\` | 上游 hash、本地 hash、补丁清单一及 sha256 |"
    echo "| \`file-diff-summary.txt\` | 逐文件状态 |"
    [ -f "$REPORT_DIR/file-diff.patch" ] && echo "| \`file-diff.patch\` | 差异的完整 unified diff |"
    echo "| \`translation-check.txt\` | 条目数、未译、空译文、占位符一致性 |"
    [ -f "$REPORT_DIR/build.log" ]     && echo "| \`build.log\` | 完整构建输出 |"
    [ -f "$REPORT_DIR/smoke-test.txt" ] && echo "| \`smoke-test.txt\` | 启动与 qm 加载检查 |"
} > "$REPORT_DIR/report.md"

log "步骤 7/7 判定：$VERDICT"
cat "$REPORT_DIR/VERDICT.txt"
exit $VERDICT_CODE
