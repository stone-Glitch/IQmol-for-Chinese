# IQmol 鼠标悬浮提示（tooltip）功能说明

> 面向：中文版使用者与汉化维护者
> 关联任务：rWMcJU（本文档）／r397Su（Q-Chem 关键词 tooltip 汉化）

---

## 一、它是什么

鼠标悬浮提示（tooltip，也常译"工具提示"）是**把光标停在某个界面元素上约一秒后自动弹出的小浮窗**，
用来说明"这个东西是干什么的 / 这个参数该填什么"。它不打断操作、不需要点击，
是 IQmol 里密度最高的一类帮助信息。

IQmol 中主要有三类：

| 类型 | 出现位置 | 内容 | 中文版状态 |
|---|---|---|---|
| 工具栏/按钮提示 | 主窗口工具栏、查看器工具条 | 按钮名称与快捷键，如"打开""全屏" | ✅ 已汉化（源码 `tr()` → `zh_CN.qm`） |
| **Q-Chem 关键词提示** | Q-Chem 输入文件编辑器，悬停在 `$rem` 段关键词上 | 该关键词的**手册级说明**：用途、取值、默认值、建议 | ✅ 已汉化（2026-09-26，477 条有效文本全覆盖） |
| 控件/输入项提示 | 各类配置器（Configure…）的输入框、下拉框 | 字段含义、单位、取值范围 | ✅ 已汉化（同上来源） |

## 二、怎么用

1. **触发**：把光标停在目标上，**不要点击**，停留约 1 秒（Qt 默认延迟）。
2. **阅读**：浮窗出现在光标附近，自动避开屏幕边缘。
3. **消失**：移开光标即消失；若浮窗挡住视线，把光标移开再移回来即可重新定位。
4. **键盘用户**：Qt 的 tooltip 只对鼠标生效；键盘操作请用 `帮助 → 显示帮助`（F1 类入口）查看完整文档。

最常用的一处是 **Q-Chem 输入文件编辑器**：写 `$rem` 段时对某个关键词不确定，
把光标压在关键词名上，浮窗会给出完整说明，例如：

```
SCF_ALGORITHM
  选择用于 SCF 收敛的算法。
  建议：
  除限制性开壳层计算外均使用 DIIS，此时推荐使用 GDM。如果 DIIS 在初始迭代中
  未能找到合理的近似解，推荐的后备选项是 RCA_DIIS……
```

这类提示里出现的 `DIIS` / `GDM` / `RCA_DIIS` 是**取值本身**，与关键词名一样不译。

## 三、中文版的提示文字来自哪里（维护者必读）

这是本项目唯一"不在源码里"的翻译通道，容易漏：

| 来源 | 覆盖范围 | 汉化方式 | 工具 |
|---|---|---|---|
| 源码 `tr("…")` 字符串 | 菜单、对话框、按钮、消息 | `lupdate` 提取 → `translations/zh_CN.ts` → `lrelease` 生成 `zh_CN.qm` | `scripts/update_translations.sh` |
| **`share/qchem_option.db`** | Q-Chem 关键词说明（tooltip） | 直接改数据库 `options.Description` 字段 | `scripts/i18n/qchem_db_translate.py` |

数据库里的说明是 **Qt RichText HTML**（含 DOCTYPE、`<style>`、`<span style=…>`），
手工编辑极易破坏标签，因此统一用工具处理：

```bash
# 导出待译文本段（HTML 安全，只抽出可见文本）
python3 scripts/i18n/qchem_db_translate.py export --batch 1/6 --out /tmp/b1.json
# 翻译后回写（自动备份原库，占位符不守恒会拒绝写入）
python3 scripts/i18n/qchem_db_translate.py import --in /tmp/b1.json
# 校验：条数 / 空描述 / HTML 结构
python3 scripts/i18n/qchem_db_translate.py verify
```

三条硬规则：

1. **关键词名不译** —— 它是输入文件语法，译了就跑不动；
2. **`{KEY}` 交叉引用原样保留** —— 说明文字里花括号包着的是其它关键词名，工具会做守恒校验；
3. **只改 `Description` 字段** —— schema、`Name`、`Type`、`Default` 一律不动。

汉化进度与对照表：`docs/汉化对照表/qchem关键词说明.md`（504 条，原文/译文两列）。

## 四、常见问题

| 现象 | 原因 | 处理 |
|---|---|---|
| 关键词上不弹提示 | 该关键词不在 `qchem_option.db` 中（自定义/新版本新增） | 查 Q-Chem 官方手册；可把新关键词补进数据库 |
| 提示是英文 | 数据库未随包更新 | Windows：`deploy_windows.sh` 会复制 `share/qchem_option.db`；Linux：`package_linux.sh` 同样随包，重打包即可 |
| 提示框乱码 | HTML 头部的 charset 被破坏 | 用 `qchem_db_translate.py verify` 检查；不要手工改 HTML |
| 按钮提示仍是英文 | `zh_CN.qm` 未加载（路径问题） | 见 `docs/验证记录/2026-09-24-Linux分发包中文翻译加载失败定位.md` |
