> 🏠 [项目首页](README.md)

---

# 变更日志

本项目所有值得记录的变更都会写入本文件，格式参考 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，版本号遵循[语义化版本](https://semver.org/lang/zh-CN/)。

## [Unreleased]

### 文档

- 整理仓库文档一致性：修复指向已删除 `submodules-package` 分支的死链（统一改为 `main` 分支）
- 统一翻译条数口径为 **2125 条 / 155 context**（此前 README 记 2035、部分文档记 2111，再早统一为 2112）
- 消解 OpenBabel 补丁包定性冲突（标注为「旧版冗余包」）
- `docs/仓库结构.md` 补列根目录分发包、许可证清单、SBOM、审校数据等顶层条目

### 新增

- 治理文件：Issue 模板（Bug / 翻译 / 构建）、PR 模板、`SECURITY.md`、`CONTRIBUTING.md`、`CHANGELOG.md`

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
