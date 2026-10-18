> 🏠 [项目首页](README.md)

---

# 变更日志

本项目所有值得记录的变更都会写入本文件，格式参考 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，版本号遵循[语义化版本](https://semver.org/lang/zh-CN/)。

## [Unreleased]

### 工程与发布

- **版本口径统一为 `3.2.4.1-zh_CN`**：`CMakeLists.txt` 定为 3.2.4.1；发布脚本 `publish_release.sh` 改为从 CMakeLists 动态派生版本与资产名（消除 `v3.2.3` 硬编码，以及"两个 Release 同文件名不同哈希"的治理问题）；同名资产改为拒绝静默覆盖
- **供应链 P0 止血**：`build_windows.sh` 的 SHA256 校验改为失败关闭（CMake 压缩包、子模块离线包强制校验，缺失即拒绝）；新增 `dependencies.lock`（9 子模块 gitlink commit + 许可证清单）；`LICENSE` 补 `SPDX-License-Identifier: GPL-3.0-or-later`
- **治理文件**：新增 `GOVERNANCE.md` / `RELEASING.md` / `SUPPORTED_PLATFORMS.md` / `THIRD_PARTY_ASSETS.md`；`.gitignore` 补 `.token`（发布凭证勿提交）
- **源码侧漏翻清零**：P2-10 将 49 处未 `tr()` 的界面字符串全部包裹，新增 61 条译文并剔除陈旧/错 context 条目；源码侧 `tr` 覆盖门禁收紧为硬上限 0（此前负向有效于 `--baseline 48`）

### 文档

- 整理仓库文档一致性：修复指向已删除 `submodules-package` 分支的死链（统一改为 `main` 分支）
- 统一翻译条数口径为 **2110 条 / 158 context**（P2-10 清零后；此前 README 记 2035、部分文档记 2111，再早 2112 → 2125 → 2126）
- 消解 OpenBabel 补丁包定性冲突（标注为「旧版冗余包」）
- `docs/仓库结构.md` 补列根目录分发包、许可证清单、SBOM、审校数据等顶层条目
- 新增供应链/安全/可复现性审计的本地核验回应（`docs/审校与排查/外部评审/03-供应链安全审计-本地核验回应-2026-10-18.md`）

### 新增

- 治理文件：Issue 模板（Bug / 翻译 / 构建）、PR 模板、`SECURITY.md`、`CONTRIBUTING.md`、`CHANGELOG.md`

---

## [3.2.4.1-zh_CN] - 2026-10-03

> 相对 `3.2.3-zh_CN` 的累积更新（含 `v3.2.4-zh_CN` 与 `v3.2.4.1-zh_CN` 两个 tag；其中 `v3.2.4-zh_CN` 仅打标签、未发 Release，实际最新发布为 `v3.2.4.1-zh_CN`）。

### 修复

- **F1 缺陷修复**：修正历史记录面板 / 撤销栈中 9 处未翻译的操作命令名（硬编码英文 → 中文）（`9b66b37`）
- **Windows 构建/打包链路打通**：补装 `qt5-translations`、修正 MSYS2 包名、去掉 `setup-msys2` 的 `update:true`、根因修复符号链接、解包子模块加 7z 回退（`dce7b42` 起系列修复）
- **TQA 翻译质量门禁**：修复 F1 引入的门禁红灯与 ARM runner 的 Setup Fortran 失败（`33c03b0`）
- **Release 自动化**：声明 `contents: write` 修复 Release 上传 403，封面数字改为脚本化实测（`63f018a`）

### 文档与工程

- 上游迁移链路补齐三类缺口，selfcheck 基线 69→95（`1c03107`）
- 增量构建指纹漏报修复、跨链接器兼容性加固（`92a97da`）
- 多卡片界面逐卡片截图、全套界面无头重渲染（`5888c06`、`7eb98b5`）
- 仓库结构整理：移除误提交发行包、分散目录归位（`493e1c7` 等）
- 推广视频全流程产出、44 篇文档全面整理

### 说明

- 翻译口径维持 **2125 条 / 155 context / 0 unfinished**（本批未改动翻译条目总量）
- 已知问题（帮助文档部分英文截图、运行期未 `tr()` 字符串）仍见 [README](README.md#已知问题源自上游)

---

## [3.2.3-zh_CN] - 2026-09-26

首个面向简体中文用户的预编译发布版本，基于上游 [nutjunkie/IQmol3](https://github.com/nutjunkie/IQmol3) v3.2.3（commit `94356ab`）。

### 新增

- **界面全量汉化**：`translations/zh_CN.ts` 共 **2112 条**翻译、153 个 context，`0 unfinished`；构建时由 CMake 自动调用 `lrelease` 生成 `zh_CN.qm`
- **Windows 预编译分发包**：`IQmol-win64-3.2.3-zh_CN.zip`（含 `IQmol.exe`、`README_zh_CN.txt`、Qt 运行库与 900+ 依赖 DLL）—— 经 **GitHub Release** 分发，不入仓库
- **子模块离线包**：`submodules-package/` 提供完整第三方库源码打包（49,335 个文件），供国内网络跳过联网克隆
- **中文界面截图集**：`dialog_screenshots/`（顶层核心对话框 + `all/` 全量 81 个 `.ui` + `cards/` 多卡片界面）
- **翻译审校数据**：`docs/审校与排查/`（P6 审校工单 CSV 与结果 JSON）与 `docs/汉化工程/`（术语词典、质量评估方案等）
- **构建与打包文档**：`docs/构建与打包/`（三平台编译、Linux 分发包、发布与上传、零补丁打包）
- **第三方许可证清单**：`THIRD_PARTY_LICENSES.md`
- **软件物料清单**：`sbom.json`（CycloneDX 格式）
- **CI 工作流**：`.github/workflows/`（Ubuntu 24.04 构建、Windows MinGW 构建、i18n 质量检查）

### 说明

- 汉化仅覆盖界面 / 帮助 / Q-Chem 关键词文案；上游计算功能、SSH 实现、文件解析未做改动
- 已知问题（源自上游）见 [README](README.md#已知问题源自上游)

---

> 维护者：@stone-Glitch ｜ 最后整理：2026-10-01
