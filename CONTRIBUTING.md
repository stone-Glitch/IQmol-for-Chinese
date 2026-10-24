# 贡献指南

感谢你愿意参与 IQmol 中文版。这份文档让你**在打开编辑器之前就知道改动该落在哪一层**，以及**哪些提交会被拒绝**。

| 配套文档 | 用途 |
|---|---|
| [术语表.md](术语表.md) | 新增/修改译法前必查 |
| [翻译审校清单.md](翻译审校清单.md) | 提交翻译 PR 前逐项过 |
| [FAQ与故障速查.md](FAQ与故障速查.md) | 遇到问题按症状查 |

---

## 0. 四层工作树（最重要的一节）

本仓库不是"一个 app 目录"，而是**上游工作树 + 一层中文交付**。

| 层 | 内容 | 风险 | 谁审 |
|---|---|---|---|
| **第一层：上游源码** | `src/`、`CMakeLists.txt`、`modules/` | 高 | 维护者；**bug 优先回报上游** |
| **第二层：翻译基础设施** | 源码中的 `tr()`、`translations/*.ts`、`*.qm` | 中 | 维护者 + 术语审校 |
| **第三层：构建/部署/打包** | `scripts/`、`.github/workflows/`、`cmake/`、`installer/` | 高 | 维护者 + CI |
| **第四层：中文交付物** | 用户手册、`docs/汉化工程/`、界面截图、发布说明 | 低 | 维护者 |

**判定流程：**

```
改动涉及 IQmol 软件本身的功能？
  └─ 是 → 去上游提，本仓库不做
改的是界面上人能看到的文字？
  ├─ 只改措辞 → 第二层：translations/zh_CN.ts
  └─ 新增了文字 → 源码加 tr() + 重跑 lupdate → 第二层（但碰了第一层的文件）
改的是构建、部署、打包、CI？
  └─ 是 → 第三层，需要给出至少一个平台的完整验证
改的是手册、docs、截图、Release 说明？
  └─ 是 → 第四层
想提交安装包或大二进制？
  └─ 一律拒绝，见第 5 节
```

**跨层混杂的 PR 会被要求拆分。** 尤其不要把平台脚本改动和文案改动塞进同一个 PR——
它们风险不同、回滚成本不同、审查者不同。

**最重要的一条**：不能把"中文界面正常"当成"上游功能没被破坏"。这两件事要分开验证。

---

## 1. 开始之前

### 环境

- Qt **5.x**（5.15 LTS 推荐）；Qt6 暂不支持
- CMake **3.x**（3.31）
- Qt5 Linguist 工具（`lupdate`/`lrelease`，Debian 系 `qttools5-dev-tools`）
- Python 3（翻译检查脚本需要）
- Windows 额外：MinGW-w64 + Fortran 编译器

完整步骤见 [docs/构建与打包/构建与部署指南.md](docs/构建与打包/构建与部署指南.md)。

**建议做的第一件事**：用上游原始 commit 跑通一次绿色构建。这样日后出问题时，
你能立刻判断是上游引入的还是汉化层引入的。

### 不要做的事

- ❌ 不要运行 `git submodule update --init --recursive`（离线包解压后会被重新联网克隆覆盖）
- ❌ 不要用 7-Zip / 360 压缩解压 `.tar.gz`（会静默丢文件），用 MINGW64 终端的 `tar`
- ❌ 不要往 git 里提交任何二进制产物

---

## 2. 快速上手：不需要构建环境的贡献

**这才是新手最该从这儿开始的地方。**

```bash
# 翻译质量检查（秒级，不需要 Qt、不需要编译）
bash scripts/check_translations.sh
bash scripts/check_translations.sh --strict    # 软提示也阻断
bash scripts/check_translations.sh --json      # 机器可读

# 找出高频但未进术语表的英文词
grep -oP '(?<=<source>)[A-Za-z][A-Za-z ]{3,20}(?=</source>)' translations/zh_CN.ts \
  | sort | uniq -c | sort -rn | head -40
```

零风险贡献：

- 翻译文本审计（空译文、占位符、术语一致性）
- 补术语表条目
- 补 `docs/` 文档与 FAQ
- 整理 CI 失败日志并建诊断 issue

---

## 3. 分支与提交规范

### 分支命名

```
i18n/<scope>          i18n/configurator-labels
build/<platform>      build/mingw-openbabel-patch
docs/<topic>          docs/contributing
fix/<issue>           fix/58-qm-not-loaded
upstream/<tag>        upstream/v3.2.4
```

### commit message

Conventional Commits，scope 用模块名：

```
i18n(Viewer): 修正图层名称译法
build(windows): 修复 OpenBabel uninstall 目标重名
docs(汉化工程): 补充 TQA 六维指标定义
fix(deploy): qm 输出到 bin/translations/ 双路径
```

**粒度**：`tr()` 包裹按模块分组提交，不要一个 20 文件的大 commit。
详见 [01-上游PR提案/commit切分方案.md](../01-上游PR提案/commit切分方案.md)。

---

## 4. 翻译规范

完整术语见 [术语表.md](术语表.md)，审校步骤见 [翻译审校清单.md](翻译审校清单.md)。
这里只列最容易出错的几条：

### 4.1 什么该翻，什么不该翻

| ✅ 翻 | ❌ 不翻 |
|---|---|
| 菜单、对话框标题、按钮 | **Q-Chem 关键字值**（`B3LYP`、`cc-pVDZ`） |
| 提示、错误消息、状态栏 | 文件扩展名、内部标识符 |
| 单位、格式说明、帮助文本 | 日志/debug tag、正则、第三方数据名 |

**翻译 Q-Chem 关键字值会直接破坏输入文件**，这是本仓库最严重的一类错误。
`check_translations.sh` 会自动查这一类。

### 4.2 `lupdate` 必须带 `-extensions C,ui`

IQmol 源码多用大写 `.C`，`lupdate` 默认扩展名不含 `.C`。
不加这个参数会导致 292 个文件的 `tr()` **零提取**，而退出码仍是 0 —— 表面成功，实际归零。

### 4.3 vanished 条目四态处理

`vanished` 只表示 lupdate 在原位置找不到源字符串，**不等于已删除**。

| 情况 | 处理 |
|---|---|
| 确认已删除 | 移除 |
| 位置/签名变化 | 保留译文并复核 |
| lupdate 解析失败 | 修 include 路径或参数 |
| 模糊匹配 | 人工确认 source location |

不要无条件恢复，也不要用 `-no-obsolete` 一键清洗。

### 4.4 形式要求

- 占位符 `%1`/`%2`/`%n` 原样保留，位置可调
- HTML 标签成对保留
- `&` 快捷键前缀保留在原位置
- 首尾空格不要 trim（常是有意的对齐）
- 中文用全角标点；数字与单位间保留半角空格

### 4.5 更新流程

```bash
./scripts/update_translations.sh          # lupdate + 防退化 + lrelease
./scripts/update_translations.sh --sync   # 并同步 qm 到 build 目录
bash scripts/check_translations.sh        # 提交前必跑
```

---

## 5. 硬性禁止

1. **不提交二进制产物。** 安装包、`.qm`、构建产物、`build/` 一律进 `.gitignore` 或发到 Releases。
   - 需要分发的大文件 → GitHub Releases，附 SHA-256
   - 需要版本化的大文件 → Git LFS
2. **不提交第三方源码到主树。** `modules/` 是 submodule，补丁进 `patches/` 并写明来源、上游 commit、许可证、应用顺序。
3. **不改动上游功能语义。** 发现上游 bug → 提 issue 或向上游提 PR。
4. **不批量重排/格式化上游代码。** 会让 replay 和 merge 全部失效。

---

## 6. CI

仓库有两条 workflow：

| workflow | 触发 | 耗时 | 门禁 |
|---|---|---|---|
| `i18n-tqa.yml` | PR 改动 `translations/`、`src/` 等 | 秒级 | **是**，失败阻断（翻译质量门禁 TQA） |
| `verify-replay.yml` | 手动 / 每月定时 | 长（要编译） | 否，产出报告 artifact |

本地提交前可用 `scripts/check_translations.sh` 做同样的翻译检查（不依赖 CI、秒级完成）；
`scripts/verify_replay.sh` 用于发布门——验证汉化改动能在干净上游树上完整重放，产出 `verify-reports/` 可复查报告。

**为什么翻译检查先进 CI**：它不编译、不装 Qt、不装 OpenBabel，几乎不可能因环境挂掉。
构建矩阵（Ubuntu / Windows / macOS × Qt 5.15）待翻译门禁稳定后再逐个加，加一个验证一个。

---

## 7. 上游同步

日常同步用**路线 A**（git merge）保留上游语义；每个发布版本再跑一次**路线 B**（基于 tag 的 replay）作为发布门。两者不是二选一。

```bash
bash scripts/sync_upstream.sh --status                              # 看差距
bash scripts/sync_upstream.sh --merge                               # 合并
bash scripts/migrate_to_upstream.sh --check --target /path/upstream # 预检
bash scripts/migrate_to_upstream.sh --apply --target /path/upstream # 执行
bash scripts/verify_replay.sh --target /path/upstream --tag v3.2.3  # 出验证报告
```

每次上游发新版，评估成本**不要看 commit 数，要看受影响模块**：
GUI / `tr()` / 配置器风险最高，CMake / submodule 中高，文档低。

向本仓库提 `tr()` 改动时，可考虑**同时向上游提 PR**——那是与语言无关的 i18n 基础设施，
上游要做任何非英语界面都需要它。详见 [01-上游PR提案/](../01-上游PR提案/)。

---

## 8. Release 流程

1. 同步上游到目标 tag，跑 `verify_replay.sh` 确认可重放
2. 跑 `check_translations.sh --strict`，处理所有软提示
3. 三平台（至少 Windows + Linux）构建并冒烟测试
4. 编译手册 PDF（`./scripts/build_docs.sh`）
5. 打包，计算 SHA-256
6. **发到 GitHub Releases**（不是 git），附：
   - 上游基线 tag 与 commit hash
   - 本仓库 commit hash
   - 各平台包的 SHA-256
   - 本次翻译变更摘要
   - `verify-reports/` 的报告链接
7. 更新 README 的版本徽章与上手链接

**每个 release 都应留下可复查的记录**——这是本仓库从"个人项目"走向"可信工具"的关键。

---

## 9. 上手建议

**零风险（不需要构建环境）**
- 翻译文本审计、术语表补充、文档、CI 日志诊断

**低风险（需要构建环境）**
- 补一份可复现的构建报告（精确到版本号、commit hash、失败日志）——当前最缺
- 给 OpenBabel 三个补丁包补齐哈希、来源、上游 commit、许可证、应用顺序、回滚说明
- 补跨平台 smoke test

**需与维护者确认**
- 改 CI workflow、大范围术语重译、移动 `docs/汉化工程/` 下的文件
