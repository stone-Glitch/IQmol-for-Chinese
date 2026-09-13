#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""填充 zh_CN.ts 的中文译文（按 source 原文匹配）"""
import xml.etree.ElementTree as ET

TS = "/workspace/IQmol3/translations/zh_CN.ts"

TRANSLATIONS = {
    "History:": "历史记录：",
    "Welcome to IQmol": "欢迎使用 IQmol",
    "Save Changes?": "保存更改？",
    "Save": "保存",
    "Discard": "放弃",
    "Cancel": "取消",
    "File": "文件",
    "About": "关于",
    "New Molecule": "新建分子",
    "New Viewer": "新建查看器",
    "Open": "打开",
    "Open Dir": "打开目录",
    "Open Recent": "打开最近",
    "Close Viewer": "关闭查看器",
    "Save As": "另存为",
    "Save Picture": "保存图片",
    "Record Animation": "录制动画",
    "Show Message Log": "显示消息日志",
    "Quit": "退出",
    "Edit": "编辑",
    "Undo": "撤销",
    "Redo": "重做",
    "Cut": "剪切",
    "Copy": "复制",
    "Paste": "粘贴",
    "Select All": "全选",
    "Select None": "取消选择",
    "Invert Selection": "反选",
    "Reindex Atoms": "原子重新编号",
    "Preferences": "首选项",
    "Display": "显示",
    "Full Screen": "全屏",
    "Reset View": "重置视图",
    "Show Axes": "显示坐标轴",
    "Camera": "相机",
    "Appearance": "外观",
    "Atom Labels": "原子标签",
    "Element": "元素",
    "Index": "序号",
    "Mass": "质量",
    "NMR": "核磁共振（NMR）",
    "Partial Charge": "部分电荷",
    "Spin Densities": "自旋密度",
    "Atom Label": "原子标签",
    "Build": "构建",
    "Insert Molecule by ID": "按 ID 插入分子",
    "Fill Valencies With Hydrogens": "用氢原子填充化合价",
    "Reperceive Bonds": "重新识别键",
    "Set Isotopes": "设置同位素",
    "Set Geometric Constraint": "设置几何约束",
    "Freeze Selected Atoms": "冻结所选原子",
    "Minimize Structure": "结构最小化",
    "Select Force Field": "选择力场",
    "Translate To Center": "平移到中心",
    "Symmetrize Molecule": "分子对称化",
    "Set Symmetry Tolerance": "设置对称容差",
    "Auto-detect Symmetry": "自动检测对称性",
    "Calculation": "计算",
    "Q-Chem Setup": "Q-Chem 设置",
    "Job Monitor": "任务监视器",
    "Edit Servers": "编辑服务器",
    "Gromacs Setup": "Gromacs 设置",
    "Edit Gromacs Config": "编辑 Gromacs 配置",
    "Edit Gomacs Server": "编辑 Gromacs 服务器",
    "Edit Amber Config": "编辑 Amber 配置",
    "Amber System Builder": "Amber 系统构建器",
    "Help": "帮助",
    "Show Help": "显示帮助",
    "Network access available": "网络连接可用",
    "Open File": "打开文件",
    "Loading": "正在加载",
    "Open Job Directory": "打开任务目录",
    "Only one molecule can be visible when reindexing atoms.": "原子重新编号时只能显示一个分子。",
    "Clear List": "清空列表",
    "Use <esc> to exit full screen mode": "按 Esc 退出全屏模式",
    "Wonky molecule detected": "检测到异常分子",
    "Do you want to proceed?": "是否继续？",
    "(none)": "（无）",
}

# 解析并填充
ET.register_namespace("", "")
tree = ET.parse(TS)
root = tree.getroot()

filled = 0
unmatched = []
for msg in root.iter("message"):
    src_el = msg.find("source")
    trans_el = msg.find("translation")
    if src_el is None or trans_el is None:
        continue
    src = src_el.text or ""
    if src in TRANSLATIONS:
        trans_el.text = TRANSLATIONS[src]
        # 移除 unfinished 标记
        if "type" in trans_el.attrib:
            del trans_el.attrib["type"]
        filled += 1
    else:
        unmatched.append(src)

tree.write(TS, encoding="utf-8", xml_declaration=True)

print(f"已填充译文: {filled} 条")
if unmatched:
    print(f"未匹配的源字符串: {unmatched}")
