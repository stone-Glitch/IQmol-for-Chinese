#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""为第二批 tr() 清零产生的 61 条新条目填充中文译文（P2-10 收紧前置）。

与 sync_fragment_names.py 同风格：直接在 ts  XML 文本上做定位替换，
不触碰其他 context。条目键为 (context, source)——source 按 ts 中的存储形式
（&apos; 实体、真实换行）书写。

术语与全库既有译文对齐：墙钟时间 / 临时目录 / 队列 / 服务器 / 用户名称 /
主机地址 / 能量 / 表面 / 网格 / 分子 / 片段 / 影片 等。

用法：
    python3 scripts/i18n/fill_batch2_translations.py            # 预演
    python3 scripts/i18n/fill_batch2_translations.py --apply    # 写入
"""
import argparse
import os
import re
import sys

TOPDIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TS = os.path.join(TOPDIR, 'translations', 'zh_CN.ts')

CONTEXT_RE = re.compile(r'<context>\s*<name>([^<]+)</name>(.*?)</context>', re.S)
MESSAGE_RE = re.compile(
    r'(<message[^>]*>)(.*?)(<source>.*?</source>)(.*?)(<translation[^>]*>).*?(</translation>)',
    re.S)

# (context, source) -> 中文译文
TRANSLATIONS = {
    # ---- Handler::Build ----
    ('Handler::Build',
     'No molecule available.\nPlease select one in the Model View'):
     '没有可用的分子。\n请在模型视图中选择一个',
    # ---- 坐标轴单位标签 ----
    ('IQmol::Configurator::ExcitedStates', 'Energy / Hartree'): '能量 / Hartree',
    ('IQmol::Configurator::GeminalOrbitals', 'Energy/Hartree'): '能量/Hartree',
    ('IQmol::Configurator::Orbitals', 'Energy/Hartree'): '能量/Hartree',
    # ---- 约束配置器（对齐 "原子间距离 %1"/"原子间夹角 %1"）----
    ('IQmol::Configurator::ScalarConstraint', 'Distance '): '距离 ',
    ('IQmol::Configurator::ScalarConstraint', 'Angle '): '角度 ',
    ('IQmol::Configurator::ScalarConstraint', 'Torsion between atoms '): '原子间二面角 ',
    ('IQmol::Configurator::ScalarConstraint', 'Torsion '): '二面角 ',
    ('IQmol::Configurator::VectorConstraint', 'Position '): '位置 ',
    # ---- Layer ----
    ('IQmol::Layer::GeminalOrbitals', 'Problem calculating grid data'):
     '计算网格数据时出现问题',
    ('IQmol::Layer::Group', 'Coordinate mismatch in Group alignment'):
     '组对齐时坐标数目不匹配',
    ('IQmol::Layer::Group', 'Alignment failed in Group::align'):
     '对齐失败（Group::align）',
    ('IQmol::Layer::Molecule', 'Atom selection required'): '需要先选择原子',
    ('IQmol::Layer::Molecule', 'Attempt to add unknown primitive type to molecule'):
     '尝试向分子添加未知图元类型',
    ('IQmol::Layer::Molecule', 'Atempt to remove unknown primitive type to molecule'):
     '尝试从分子移除未知图元类型',
    ('IQmol::Layer::Molecule', 'Unable to nest fragments'): '无法嵌套片段',
    ('IQmol::Layer::Orbitals', 'Still processing previous grid data request'):
     '仍在处理上一个网格数据请求',
    ('IQmol::Layer::Surface', 'Configure Surface: '): '配置表面：',
    ('IQmol::Layer::Surface', 'Mesh simplification in progress'):
     '网格简化正在进行中',
    ('IQmol::Layer::System', 'Failed to open PDB file for writing'):
     '打开 PDB 文件写入失败',
    # ---- MainWindow（H3 PDF 手册入口）----
    ('IQmol::MainWindow', 'User Manual (PDF)'): '用户手册 (PDF)',
    ('IQmol::MainWindow',
     'Could not open the user manual PDF resource. '
     'Please check that the installation is complete.'):
     '无法打开用户手册 PDF 资源，请检查安装是否完整。',
    ('IQmol::MainWindow',
     'Could not create a temporary file to open the user manual.'):
     '无法创建临时文件以打开用户手册。',
    ('IQmol::MainWindow',
     'Could not launch the PDF viewer. Please open it manually: '):
     '未能启动 PDF 查看器，请手动打开：',
    # ---- Network / Parser ----
    ('IQmol::Network', 'Invalid username or password'): '用户名或密码无效',
    ('IQmol::Network::AwsConnection', 'Passwords do not match'):
     '两次输入的密码不一致',
    ('IQmol::Parser::QChemOutput', ' energy'): ' 能量',
    # ---- Process ----
    ('IQmol::Process::AwsConfigurationDialog',
     'Cognito Pool ID should start with the AWS region'):
     'Cognito Pool ID 应以 AWS 区域开头',
    ('IQmol::Process::JobMonitor', 'Invalid username or password'):
     '用户名或密码无效',
    ('IQmol::Process::JobMonitor', 'Network timeout'): '网络超时',
    ('IQmol::Process::JobMonitor', 'Error encountered'): '遇到错误',
    ('IQmol::Process::JobMonitor', 'Directory name cannot contain spaces'):
     '目录名不能包含空格',
    ('IQmol::Process::JobMonitor', 'Copy results from server?'):
     '要从服务器复制结果吗？',
    ('IQmol::Process::JobMonitor', 'Output file no longer exists'):
     '输出文件已不存在',
    ('IQmol::Process::QueueResourcesDialog', 'No queues found on server'):
     '服务器上未找到队列',
    ('IQmol::Process::QueueResourcesDialog',
     'Wall time must be in the format h:mm:ss'):
     '墙钟时间格式必须为 h:mm:ss',
    ('IQmol::Process::QueueResourcesDialog',
     'Validated wall time not in the format h:mm:ss'):
     '校验后的墙钟时间格式不是 h:mm:ss',
    ('IQmol::Process::QueueResourcesDialog', 'Wall time exceeds queue maximum of '):
     '墙钟时间超过队列上限 ',
    ('IQmol::Process::QueueResourcesDialog', 'Memory exceeds queue limit of '):
     '内存超过队列限制 ',
    ('IQmol::Process::QueueResourcesDialog', 'Scratch exceeds queue limit of '):
     '临时目录超过队列限制 ',
    ('IQmol::Process::QueueResourcesDialog',
     'Number of CPUs exceeds queue limit of '):
     'CPU 数量超过队列限制 ',
    ('IQmol::Process::ServerConfigurationDialog', 'Server name not set'):
     '未设置服务器名称',
    ('IQmol::Process::ServerConfigurationDialog', 'Host address not set'):
     '未设置主机地址',
    ('IQmol::Process::ServerConfigurationDialog', 'User name must be set'):
     '必须设置用户名称',
    ('IQmol::Process::ServerConfigurationDialog',
     'Failed to export server configuration'):
     '导出服务器配置失败',
    # ---- Viewer ----
    ('IQmol::Snapshot',
     'Movie making already in progress, please wait'):
     '影片录制已在进行中，请稍候',
    ('IQmol::Snapshot', 'ffmpeg executable not found'): '未找到 ffmpeg 可执行文件',
    ('IQmol::Snapshot', 'Could not remove existing file '):
     '无法删除已存在的文件 ',
    ('IQmol::ViewerModel', 'Invalid string'): '无效的字符串',
    # ---- Qui ----
    ('InputDialog',
     "Could not write to file &apos;%1&apos;\nInput file not saved\n"):
     "无法写入文件 '%1'\n输入文件未保存\n",
    ('InputDialog', 'File Not Saved'): '文件未保存',
    ('InputDialog', 'Are you sure you want to delete the section %1?'):
     '确定要删除节 %1 吗？',
    ('InputDialog', 'Delete Section?'): '删除该节吗？',
    ('Qui::GeometryConstraint::Dialog',
     'Constraints that reference this dummy atom (%1) and any with a '
     'higher id will become invalid'):
     '引用此虚拟原子（%1）及更高 id 的任何约束将变为无效',
    ('Qui::GeometryConstraint::Dialog', 'Warning'): '警告',
    ('Qui::OptionDatabase',
     'Option name %1 already exists in database, overwrite?'):
     '选项名称 %1 已存在于数据库中，是否覆盖？',
    ('Qui::OptionDatabase', 'Option Exists'): '选项已存在',
    ('Qui::OptionDatabase',
     'Permanently delete the %1 record from the option database?'):
     '确定要从选项数据库中永久删除 %1 记录吗？',
    ('Qui::OptionDatabase', 'Delete Option?'): '删除该选项吗？',
    ('Qui::OptionDatabase', 'More than one record for %1 found in database.'):
     '数据库中存在多条 %1 的记录。',
    ('Qui::OptionDatabase', 'EGAD!'): '天哪！',
}


def esc(s):
    return (s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
             .replace("'", '&apos;'))


def fill(text, dry_run):
    """逐 context 定位消息并回填译文。返回 (新文本, 命中明细)。"""
    details = []
    out = []
    last = 0
    for cm in CONTEXT_RE.finditer(text):
        ctx = cm.group(1)
        body = cm.group(2)
        # 收集本 context 中待填的 (source -> translation)
        pending = {src: tr for (c, src), tr in TRANSLATIONS.items() if c == ctx}
        if not pending:
            continue
        new_body = body
        for src, tr in pending.items():
            # 在该 context 体内找含此 source 的 message
            pat = re.compile(
                r'(<message[^>]*>)(.*?<source>' + re.escape(src) +
                r'</source>)(.*?)(<translation[^>]*>).*?(</translation>)', re.S)
            mm = pat.search(new_body)
            if not mm:
                details.append((ctx, src, '条目未找到'))
                continue
            new_body = (new_body[:mm.start()] + mm.group(1) + mm.group(2) +
                        mm.group(3) + '<translation>' + esc(tr) +
                        '</translation>' + new_body[mm.end():])
            details.append((ctx, src, '已填充'))
        out.append(text[last:cm.start()])
        out.append('<context>\n        <name>%s</name>%s</context>' % (ctx, new_body))
        last = cm.end()
    out.append(text[last:])
    return ''.join(out), details


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true', help='实际写盘（默认 dry-run）')
    args = ap.parse_args()
    dry_run = not args.apply

    text = open(TS, encoding='utf-8').read()
    new_text, details = fill(text, dry_run)

    ok = [d for d in details if d[2] == '已填充']
    bad = [d for d in details if d[2] != '已填充']
    for ctx, src, status in details:
        print('  %-8s %-40s %r' % (status, ctx, src[:46]))
    print()
    print('待填 %d 条，已填 %d 条，未命中 %d 条'
          % (len(TRANSLATIONS), len(ok), len(bad)))
    if bad:
        print('!! 有条目未命中（见上），请核对 context/source')
        return 1
    if dry_run:
        print('\n（dry-run，未写盘。确认后加 --apply）')
        return 0
    with open(TS, 'w', encoding='utf-8') as f:
        f.write(new_text)
    print('已写入', TS)
    return 0


if __name__ == '__main__':
    sys.exit(main())
