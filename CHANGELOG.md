> 🏠 [项目首页](README.md)

---

# 变更日志

本项目所有值得记录的变更都会写入本文件，格式参考 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，版本号遵循[语义化版本](https://semver.org/lang/zh-CN/)。

## [Unreleased]

### 文档整理（2026-10-18 全库一致性扫描）

- **数字漂移修复 2 处**：`推广视频制作计划.md`（`context = 156`→158）与 `B站投稿单.md`（`# → 156`→158）。两处均为门禁盲区——原匹配模式只认「数字在后」（`156 条翻译`），漏掉「词在数字前」（`context = 156`）与代码块箭头式期望输出（`# → 156`）两种写法
- **数字门禁加固**：`verify_doc_numbers.py` 补齐五类紧邻用法（数字在后 / 词在前含等号冒号 / 三数连写 / 等号+括号 / 箭头期望输出），回溯叙述行仍只提示不判失败；负向注入测试通过（重新注入两种 stale 写法均被抓获）
- **索引同步**：`推广视频/README.md` 补录孤儿文件 `B站投稿单.md`；`审校与排查/README.md` 外部评审节补列 02/03 号回应并将进度快照更新为「已整改 10 / 未整改 2」（P0-1、P3-12）；`工程待办与现状登记.md` 纳管节同步 3 份归档、P2-10 行更新为已整改、2.1 节补 Windows CI 全绿实证；`验证记录/README.md` 补 2026-10-17 行并将名不副实的「三篇合并记录」节标题改为「诊断与核查记录」；`docs/README.md` 三条行文刷新（工程待办去已清零的「71 处」、验证记录去过时「新增」框定、推广视频补投稿单/外播文案包）
- **口径修正**：根 README 速览表平台行去掉 macOS（与「汉化成果速览」html「仅实测 Windows x64 与 Linux x86_64」对齐，遵守外播红线）；宣传视频行移除无法核验的「已发布 B 站」表述；Release 分发口径由「git LFS/Commit 形式」改为「GitHub Releases 分发（附 SHA256SUMS）」；`界面英文残留清单.md` 状态行更新（G 组已定案、H 组已实质完成、P2-10 已清零）；`汉化工程/README.md`「四组」→「三组」（专项审查节已并入）；`整改对照表.md` 第七节结论标注为 2026-10-11 时点口径并补 2026-10-18 现状，消除与总览表的内部矛盾
- 全仓相对链接复扫：**234 处 0 死链**；各目录索引页脚日期批量更新

### 文档清理

- **移除 7 篇已完结的一次性过程文档**（结论均已由在役文档接管）：`P6-审校工单.md`（`semantic_audit.py` 的生成物，审校已结论、记录表为收敛视图；改入 `.gitignore` 防重跑污染）、`未汉化字符串排查报告.md` 与 `工程审查核查报告-实证版.md`（由外部评审整改对照表 + P2-10 清单接管）、`文档整理报告.md`、`审查技术订正说明.md`、`菜单中文化穷举审查.md`、`发布与上传.md`（沙箱受限网络场景已过时）
- 同步更新 4 个索引与 `仓库结构.md`；`check_wiki_sync.sh` 移除已删文档的映射；`界面英文残留清单.md` 内对已删文档的引用改为本地结论记载。全仓相对链接复扫：**0 死链**（仅剩上游 vendored hdf5 文档自带的 7 处，非本仓内容）
- P2-10 清单（`源码侧未tr字符串清单.md`）补登 `汉化工程` 索引——此前漏登记

### 推广物料与门禁

- **主视觉去敏感化**：`docs/assets/ui/view3d_viagra_demo.png`（西地那非分子）→ `view3d_porphyrin.png`（卟啉分子，离屏渲染 1620×910），同步更新展示主页、成果速览 HTML、素材清单等 4 处引用；录屏文档标注 viagra 素材禁作公开主视觉
- **数字核验门禁升级并接入 CI**：`verify_doc_numbers.py` 扫描范围从推广视频扩展到 README、汉化展示主页等全部公开面（11 个文档）；纳入新陈旧值（2126/156）；回溯叙述（"原写…修正为…"）不再误报；清除死代码。i18n-tqa.yml 新增「宣传数字核验门禁」step——README 与文案数字再打架，CI 直接红
- **新增外播文案包**（`docs/推广视频/外播文案包-2026-10-18.md`）：对外口径卡（2110 条 / 158 context / 34 页 / v3.2.4.1-zh_CN，唯一事实源）+ B 站置顶评论 + 3 秒口播（3 变体）+ 知乎文章大纲 + 教师傻瓜包 + 发布检查单；附外部依赖登记（Pages/Gitee/网盘待授权）
- `docs/.nojekyll` 就位（GitHub Pages 开启 toggle 后即可用）；视频简介过时版本号 3.2.3 → 3.2.4.1

### 工程与发布

- **Windows CI 三连败根因修复**（run #3/#4/#5）：`check_submodules_drift.sh` 在 Windows runner 上从未通过——连续误报「modules/hdf5 版本漂移」而 Linux 全绿。根因双重叠加：① Windows 原生 Python（hostedtoolcache）stdout 文本模式把 `\n` 写成 `\r\n`，清单侧每个 sha 带尾随 `\r`，与 gitlink 侧永远失配（错误消息里的 `\r` 还会让 CI 注释渲染到该处截断，只剩半句）；② `en_US.UTF-8` locale 下 `sort` 把 `modules/hdf5` 排到 HighFive 之前，第一个被比对的条目随环境变化。修复：固定 `LC_ALL=C`、gitlink/清单双侧剥 `\r`、Python 改走 `sys.stdout.buffer` 写字节、漂移详情先于 `fail()` 打印（原 `fail()` 内 `exit 1` 使详情 echo 成为死代码）。已做三重回归：CRLF 模拟环境下旧脚本复现失败 / 新脚本通过、篡改清单仍能抓出、还原后归绿
- **build_windows.sh**：CMake 3.31.6 官方发布包 SHA256 钉入脚本（`d163cd3a…4f836`，与 Kitware 官方 `cmake-3.31.6-SHA-256.txt` 核对）——strict 完整性校验此前在 CI 上因未设 `CMAKE_ZIP_SHA256` 环境变量而空转，遇 MSYS2 CMake 4.x 触发自动下载时会误报「下载被劫持」；期望值优先级：环境变量 > 内置表 > 空（拒绝，失败关闭）。`lookup_sha256` 增加 CRLF 防护
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
