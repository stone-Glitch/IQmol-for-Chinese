# Pull Request

## 改动落在哪一层

> 本仓库是「上游工作树 + 一层中文交付」。跨层混杂的 PR 会被要求拆分。
> 详见 [CONTRIBUTING.md](../CONTRIBUTING.md) 第 0 节。

- [ ] **第一层：上游源码**（`src/`、`CMakeLists.txt`、`modules/`）
- [ ] **第二层：翻译基础设施**（`tr()`、`translations/*.ts`）
- [ ] **第三层：构建 / 部署 / 打包**（`scripts/`、`cmake/`、`.github/`）
- [ ] **第四层：中文交付物**（手册、`docs/汉化工程/`、截图）

## 做了什么

<!-- 一句话说明。不要贴 diff，说明意图。 -->

## 为什么

<!-- 解决的问题。有关 issue 请写 Fixes #N -->

## 验证方式

<!-- 写你实际执行了什么、看到了什么，不要只写"已测试"。 -->

| 改动类型 | 最低验证要求 |
|---|---|
| 纯文案 | 编译 qm，启动，打开相关对话框截图 |
| 源码 `tr()` | 英文 / 中文 / 跟随系统三种语言各启动一次 |
| 构建脚本 | 干净构建 + 增量构建各一次 |
| 部署脚本 | 全新解压环境启动成功，Qt 插件与 OpenBabel 数据就位 |
| 上游同步 | 跑 `scripts/verify_replay.sh` 并附报告 |

<details>
<summary>环境信息（粘贴实际输出）</summary>

```
OS：
Qt：        (qmake --version)
CMake：     (cmake --version)
编译器：
本仓库 HEAD：(git rev-parse HEAD)
上游基线：
```

</details>

## 自查清单

**通用**

- [ ] 没有提交二进制、构建产物、`.qm`、`build/` 目录
- [ ] 没有批量重排 / 格式化上游代码（会让 replay 与 merge 失效）
- [ ] commit 按模块分组，不是一个大杂烩 commit
- [ ] 没有改动 `modules/` 子模块指针（除非本 PR 就是要升子模块）

**翻译类**

- [ ] 界面新增文字已在源码中加 `tr()`
- [ ] 重跑了 `./scripts/update_translations.sh`
- [ ] `unfinished` 为 0，空译文为 0
- [ ] 占位符（`%1`、`%2`）与 HTML 标签与源串一致
- [ ] Q-Chem 关键字**值**未被翻译
- [ ] 术语与 CONTRIBUTING.md 术语表一致
- [ ] 标点用全角，数字与单位间保留半角空格
- [ ] 在界面上看过实际显示效果，未被截断

**构建 / 部署类**

- [ ] 给出至少一个平台的完整构建日志
- [ ] Windows 相关改动：确认过四个离线包的解压顺序
- [ ] 改动了部署路径：确认过 qm 双路径（包根 `translations/` 与 `bin/translations/`）

## 截图 / 日志

<!-- 界面改动请附截图（中文 + 英文对照最好）；构建改动请附日志 -->
