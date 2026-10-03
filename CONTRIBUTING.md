> 🏠 [项目首页](README.md)

---

# 贡献指南

感谢你对 IQmol 简体中文本地化项目的兴趣！本文说明如何参与。

## 目录

- [可以贡献什么](#可以贡献什么)
- [报告翻译问题](#报告翻译问题)
- [提交代码 / 翻译改动](#提交代码--翻译改动)
- [术语规范](#术语规范)
- [文档口径约定](#文档口径约定)
- [提交信息规范](#提交信息规范)

## 可以贡献什么

| 类型 | 说明 |
|---|---|
| 翻译修正 | 界面 / 帮助文档 / Q-Chem 关键词的译文错误、术语不统一 |
| 补全译文 | 界面仍有英文残留且源字符串已被 `tr()` 包裹 |
| 源码汉化 | 为未被 `tr()` 包裹的字符串补充包裹，使其可被翻译 |
| 构建 / 打包 | 三平台构建脚本、离线包、CI 改进 |
| 文档 | 修正文档错误、补充说明 |

## 报告翻译问题

优先用 [翻译问题模板](https://github.com/stone-Glitch/IQmol-for-Chinese/issues/new?template=translation_issue.yml) 提交 Issue，请包含：

- **界面位置**（哪个对话框 / 菜单 / 选项卡）
- **原文**（英文）
- **当前译文**
- **建议译文**（如有）
- **截图**（最直观）

> 若界面仍是英文，请先判断：该字符串是否出自上游尚未 `tr()` 包裹的代码？可在 Issue 中说明，维护者会补充包裹。

## 提交代码 / 翻译改动

1. **Fork 并克隆**（注意子模块）：
   ```bash
   git clone --recursive https://github.com/<you>/IQmol-for-Chinese.git
   ```
   国内网络若子模块克隆失败，见 [`submodules-package/使用说明.md`](submodules-package/使用说明.md)。

2. **修改后自检**：
   ```bash
   grep -c '<message' translations/zh_CN.ts          # 条目总数（当前 2125）
   grep -c 'type="unfinished"' translations/zh_CN.ts # 应为 0
   ```
   若改了 `.ts`，构建时会由 CMake 自动调用 `lrelease` 生成 `.qm`。

3. **提交 PR**，按 [PR 模板](https://github.com/stone-Glitch/IQmol-for-Chinese/blob/main/.github/PULL_REQUEST_TEMPLATE.md) 填写，界面改动请附中文截图。

## 术语规范

- 遵循**全国科学技术名词审定委员会**官方译法（如 `Job` → 任务、`Surface` → 表面、`Impulse` 谱图峰形 → 冲激）。
- 计算化学关键字（Q-Chem / Amber / Gromacs 的关键词、网络协议名 `SSH`/`SFTP`、软件名 `POV-Ray`、格式 `PNG`/`SMILES` 等）**保留英文**。
- 术语词典与审核清单见 [`docs/汉化工程/术语词典审核清单.md`](docs/汉化工程/术语词典审核清单.md)；界面中英对照见 [`docs/汉化对照表/README.md`](docs/汉化对照表/README.md)。
- 遇到不确定的术语，**先建 Issue 讨论**，不要擅自采用非官方译法。

## 文档口径约定

- 译文条数的**权威口径**是 `translations/zh_CN.ts` 的 `<message` 计数（当前 **2125 条 / 155 context / 0 unfinished**），**不是文档里出现的数字**。
- 同一事实只在**一处**维护，其它文档用相对链接引用，避免口径漂移。
- 文档语言为简体中文；代码注释与命令保持原文。

## 提交信息规范

采用约定式提交（Conventional Commits）前缀，便于生成变更日志：

| 前缀 | 用途 |
|---|---|
| `feat(i18n):` | 新增译文 / 汉化功能 |
| `fix(i18n):` | 翻译修正 |
| `docs:` | 文档 |
| `build:` / `ci:` | 构建 / 持续集成 |
| `chore:` | 杂项 |

示例：`fix(i18n): 修正「Spin-Orbit Coupling」译文为「自旋-轨道耦合」`

---

有任何疑问，欢迎开 Issue 讨论。

---

> 维护者：@stone-Glitch ｜ 最后整理：2026-10-01
