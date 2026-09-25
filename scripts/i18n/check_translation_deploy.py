#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_translation_deploy.py —— 翻译部署链路「防回退」静态自检

背景（reA22A）
-------------
Linux 预编译包曾出现「zh_CN.qm 在包里，界面却仍是英文」：
IQmolApplication 按 applicationDirPath()（= bin/）找翻译，
而包内 qm 只放在包根 translations/，导致只有恰好从包根启动时才命中。

修复分三层，任何一层被后续改动回退都会让 bug 复活：
    ① 源码：搜索路径补 applicationDirPath()/../translations
    ② 打包：bin/translations/ 与 包根 translations/ 各放一份 + 打包后自检
    ③ 启动：run.sh 显式 cd 到包根（双保险）

本脚本**只读文本、不构建、不需要 Qt**，因此可放进 CI 每次提交都跑，
用来在编译之前就拦住"改动把修复抹掉了"这类回归。

用法
----
    python3 scripts/i18n/check_translation_deploy.py           # 人类可读
    python3 scripts/i18n/check_translation_deploy.py --json    # 机器可读
退出码：0 全部通过；1 存在 FAIL
"""
import argparse
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

CHECKS = [
    {
        'id': 'app-search-path',
        'desc': '源码搜索路径包含 可执行文件上一级/translations（Linux 包根）',
        'file': 'src/Main/IQmolApplication.C',
        'needle': 'appDir + "/../translations"',
    },
    {
        'id': 'app-search-path-system',
        'desc': '源码搜索路径包含 系统安装布局兜底 ../share/iqmol/translations',
        'file': 'src/Main/IQmolApplication.C',
        'needle': '"/../share/iqmol/translations"',
    },
    {
        'id': 'pkg-linux-bin-qm',
        'desc': 'Linux 打包脚本把 qm 复制到 bin/translations/',
        'file': 'scripts/package_linux.sh',
        'needle': '$STAGE/bin/translations/zh_CN.qm',
    },
    {
        'id': 'pkg-linux-root-qm',
        'desc': 'Linux 打包脚本保留包根 translations/zh_CN.qm',
        'file': 'scripts/package_linux.sh',
        'needle': '$STAGE/translations/zh_CN.qm',
    },
    {
        'id': 'pkg-linux-selfcheck',
        'desc': 'Linux 打包脚本内建「两处 qm 都在」自检',
        'file': 'scripts/package_linux.sh',
        'needle': '翻译文件自检通过',
    },
    {
        'id': 'runsh-chdir',
        'desc': 'run.sh 启动前 cd 到包根目录（不依赖调用者 cwd）',
        'file': 'scripts/package_linux.sh',
        'needle': 'cd "$ROOT"',
    },
    {
        'id': 'pkg-win-bin-qm',
        'desc': 'Windows 部署脚本把 qm 放到 bin/translations/',
        'file': 'scripts/deploy_windows.sh',
        'needle': 'BIN_DIR/translations',
    },
    {
        'id': 'verify-both-qm',
        'desc': '端到端自检脚本检查两处 qm',
        'file': 'scripts/verify_linux_pkg.sh',
        'needle': 'bin/translations/zh_CN.qm',
    },
    {
        'id': 'verify-multicwd',
        'desc': '端到端自检脚本换多个工作目录验证（不只在包根启动）',
        'file': 'scripts/verify_linux_pkg.sh',
        'needle': 'for d in /',
    },
]


def main():
    ap = argparse.ArgumentParser(description='翻译部署链路静态自检')
    ap.add_argument('--json', action='store_true', help='机器可读输出')
    args = ap.parse_args()

    results = []
    for c in CHECKS:
        path = os.path.join(REPO, c['file'])
        if not os.path.isfile(path):
            results.append({**c, 'ok': False, 'reason': f"文件不存在: {c['file']}"})
            continue
        with open(path, encoding='utf-8', errors='replace') as f:
            body = f.read()
        ok = c['needle'] in body
        results.append({**c, 'ok': ok,
                        'reason': '' if ok else f"未找到关键片段: {c['needle']}"})

    # 翻译产物存在性
    qm = os.path.join(REPO, 'translations/zh_CN.qm')
    ts = os.path.join(REPO, 'translations/zh_CN.ts')
    for label, p in (('zh_CN.qm', qm), ('zh_CN.ts', ts)):
        exists = os.path.isfile(p) and os.path.getsize(p) > 0
        results.append({'id': f'asset-{label}', 'desc': f'{label} 存在且非空',
                        'file': f'translations/{label}', 'ok': exists,
                        'reason': '' if exists else '文件缺失或为空'})

    n_ok = sum(1 for r in results if r['ok'])
    n_fail = len(results) - n_ok

    if args.json:
        print(json.dumps({'total': len(results), 'passed': n_ok,
                          'failed': n_fail, 'results': results},
                         ensure_ascii=False, indent=2))
        return 0 if n_fail == 0 else 1

    print('=' * 66)
    print(' 翻译部署链路静态自检（reA22A 防回退）')
    print('=' * 66)
    for r in results:
        tag = 'PASS' if r['ok'] else 'FAIL'
        print(f'  [{tag}] {r["desc"]}')
        if not r['ok']:
            print(f'         {r["reason"]}  <- {r["file"]}')
    print('-' * 66)
    print(f' 通过 {n_ok} / {len(results)}')
    print('=' * 66)
    return 0 if n_fail == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
