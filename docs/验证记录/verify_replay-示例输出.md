# 脚本输出示例

两个脚本都已**在构造的最小仓库上实测通过**，下面是真实输出格式。

---

# 一、check_translations.sh（日常门启用，秒级）

## 有问题时

```
==============================================================
 翻译质量检查：translations/zh_CN.ts
==============================================================
条目总数        : 12
context 数      : 2
unfinished      : 1
vanished        : 1   (需人工判断，不阻断)
空译文          : 1

-- 硬错误 --
  [占位符不一致] Main
      源: Save %1 as %2
      源=['1', '2'] 译=['2']
  [疑似翻译了关键字值] Main
      源: B3LYP
      译=B3LYP泛函
  合计 2 条

-- 软提示 --
  [疑似未译] Main
      源: Molecule
      译文与原文相同
  [首尾空格变化] Main
      源: ' atoms'
      '原子'
  [半角标点] Main
      源: 注意,请
      中文语境建议用全角
  合计 3 条

==============================================================
结论 : FAIL（存在硬错误）
注意 : 有 1 条 vanished，请人工确认是已删除还是解析失败
==============================================================
```

退出码 `1`。

## 干净时

```
条目总数        : 3
context 数      : 1
unfinished      : 0
vanished        : 0   (需人工判断，不阻断)
空译文          : 0

-- 硬错误 --
  无
  合计 0 条

-- 软提示 --
  无
  合计 0 条

==============================================================
结论 : PASS
==============================================================
```

退出码 `0`。

## 关键设计：技术 token 豁免

`B3LYP` 这类 Q-Chem 关键字值**本来就不该翻译**，译文等于原文是正确行为。
脚本用「全大写 / 含下划线 / 纯 ASCII 符号 / 无空格」识别它们，
因此 `B3LYP → B3LYP` **不会**被误报为"疑似未译"；但 `B3LYP → B3LYP泛函` 会被判为致命错误。

同理，`cc-pVDZ`、`SCF_CONVERGENCE`、`GEOM_OPT` 都在豁免范围内。

## 四种输出模式

```bash
bash scripts/check_translations.sh                    # 人类可读（默认）
bash scripts/check_translations.sh --quiet            # 一行 + PASS/FAIL
bash scripts/check_translations.sh --json             # 机器可读
bash scripts/check_translations.sh --strict           # 软提示也阻断
```

`--quiet` 输出：

```
total=12 contexts=2 unfinished=1 vanished=1 empty=1 hard=2 soft=3
FAIL
```

---

# 二、verify_replay.sh（发布门用，产出可审计目录）

## VERDICT.txt（最先看这个）

通过时：

```
==============================================
 IQmol 汉化重放验证结论
==============================================
结论     : PASS (exit 0)
时间     : 2026-07-15 08:22:41 UTC
上游     : /opt/iqmol-upstream @ 4f2a1c9
本地     : /home/dev/IQmol-for-Chinese @ c38116e
文件复现 : 69/69
原因     :  全部检查通过。
==============================================

退出码：0=PASS 1=FILES_DIFFER 2=TRANSLATION_FAIL 3=BUILD_FAIL 4=SMOKE_FAIL 5=ENV
```

失败时只改结论与原因两行，其余结构不变，方便 diff 相邻两次报告：

```
结论     : FILES_DIFFER (exit 1)
文件复现 : 67/69
原因     : 文件比对：2 处差异 / 0 上游缺失 / 0 本地缺失。
```

翻译导致失败时（实测验证过）：

```
结论     : TRANSLATION_FAIL (exit 2)
文件复现 : 1/1
原因     : 翻译检查未通过。
```

> 注意：文件复现可以是 100%，但如果翻译检查不过，整体仍判 FAIL。
> **"文件能重放"和"翻译是好的"是两件事。**

## file-diff-summary.txt

```
文件                                                        状态
------------------------------------------------------------  --------
src/Main/MainWindow.C                                         IDENTICAL
src/Viewer/GLObject.h                                         IDENTICAL
src/Qui/InputOptions.C                                        IDENTICAL
...
src/Util/Preferences.C                                        DIFFERS (4 行差异)
src/Qui/ServerConfig.C                                        DIFFERS(WHITELISTED) (2 行差异)

总计 69 个文件：
  IDENTICAL          : 67
  DIFFERS            : 0
  MISSING_IN_UPSTREAM: 0
  MISSING_IN_LOCAL   : 0
  复现率              : 100.00% (69/69)
```

| 状态 | 含义 | 处理 |
|---|---|---|
| `IDENTICAL` | 逐字节一致 | 无需处理 |
| `DIFFERS` | 有差异，生成 `file-diff.patch` | 查 patch，判断是上游变更还是重放遗漏 |
| `DIFFERS(WHITELISTED)` | 已知且可接受的差异（`--whitelist` 声明） | 必须在白名单里写明理由 |
| `MISSING_IN_UPSTREAM` | 上游树里没有 | 上游删除或改名，人工确认 |
| `MISSING_IN_LOCAL` | 本地没有 | 重放未覆盖，补进 manifest |

**白名单不是逃避工具。** 每行都要带理由：

```
# 文件                        理由
src/Qui/ServerConfig.C        上游 v3.2.3 后新增字段，本仓库有意保留旧结构，见 issue #42
CMakeLists.txt                本仓库额外引入 translations 目标，属预期差异
```

## translation-check.txt（委托 check_translations.sh 生成）

若 `scripts/check_translations.sh` 存在且与 `verify_replay.sh` 同目录，
verify_replay 会**委托**它做翻译检查（检查项更全），输出并入本报告：

```
# 由 check_translations.sh 生成（完整检查）

==============================================================
 翻译质量检查：/path/to/translations/zh_CN.ts
==============================================================
条目总数        : 2112
...
```

不存在时退回内置精简检查（只查 unfinished / 空译文 / 占位符）。

## manifest.json

```json
{
  "schema": "iqmol-zh-verify/1",
  "generated_utc": "2026-07-15T08:22:41Z",
  "upstream": {
    "path": "/opt/iqmol-upstream",
    "commit": "4f2a1c9e...",
    "describe": "v3.2.3",
    "requested_tag": "v3.2.3",
    "requested_base": null
  },
  "localization": {
    "path": "/home/dev/IQmol-for-Chinese",
    "commit": "c38116e..."
  },
  "patches": [
    { "file": "patches/0001-i18n-tr-wrapping.patch", "sha256": "a1b2...", "bytes": 18422 },
    { "file": "patches/0002-openbabel-uninstall-guard.patch", "sha256": "c3d4...", "bytes": 1024 }
  ],
  "translation": {
    "ts_file": "translations/zh_CN.ts",
    "sha256": "7d3f9a2c..."
  }
}
```

## report.md

压成一张表 + 一段结论，**可直接贴进 PR 描述或 Release notes**。它会自动带上这句限定：

> **重要限定**：文件一致不等于二进制等价、运行时等价或翻译覆盖率达标。
> 本报告证明的是「在指定上游 commit 上，汉化改动可被完整重放且源码逐字节一致」，
> 不包含 qm 内容比对、OpenBabel 行为比对或功能回归测试。

**这句限定不要删。** 主动声明边界的报告，比声称"完全等价"的报告更有说服力。

---

# 三、两个脚本怎么配合

| | check_translations.sh | verify_replay.sh |
|---|---|---|
| 耗时 | 秒级 | 分钟～小时（要编译） |
| 依赖 | 只需 python3 | 需要 Qt、CMake、OpenBabel |
| 用途 | **日常门禁**：每次改翻译都跑 | **发布门**：每个上游版本跑一次 |
| 输出 | 终端 | `verify-reports/<时间戳>/` 目录 |
| CI | PR 触发，失败阻断 | 手动/定时，产出 artifact |

**日常用左边，发布用右边，右边会调用左边。**

---

# 四、CI 接入

翻译门禁（秒级，先进 CI）：见 `03-贡献指南/.github/workflows/check-translations.yml`
重放验证（长耗时，手动/定时）：见 `03-贡献指南/.github/workflows/verify-replay.yml`

**接入顺序很重要**：先让轻量的翻译门禁稳定变绿，再考虑加构建矩阵。
当前仓库 CI 是失败状态——**红叉比没有 CI 更伤可信度**。
