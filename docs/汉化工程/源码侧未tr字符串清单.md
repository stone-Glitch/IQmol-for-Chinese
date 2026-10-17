# 源码侧未 tr() 字符串清单（P2-10）

> 生成：2026-10-17，由 `scripts/i18n/check_tr_coverage.py` 扫描 `src/`（排除 `save/` 备份副本 + 白名单）得出。
> **现状：✅ 已清零（2026-10-17）**。49 种（52 处）真漏翻全部包裹 `tr()` / `QCoreApplication::translate()` 并补中文译文，`zh_CN.qm` 已重编，门禁基线由 49 收紧为 **0（硬门禁：新增任何未授权裸字符串即失败）**。
> **性质**：#43（界面英文残留排查）当时只修了其清单内列的 71 处；本清单是**新增发现**——全仓 `QMsgBox` 错误/警告信息与约束/表面配置器标签从未被 `tr()` 包裹，`lupdate` 扫不到，界面显示英文。

## 〇、清理结果（2026-10-17）

| 项 | 结果 |
|---|---|
| 源码侧残留 | 49 种 / 52 处 → **0**（白名单命中 8 种不变） |
| 新增译文 | **61 条**（45 处单行包裹 + 7 块多行重构 + 4 条 MainWindow PDF 手册入口，含 3 条原中文源码串改英文源后补译） |
| zh_CN.ts | 2126 → **2110 条**（剔除陈旧/错 context 条目 77 条，FragmentTable 298 条手工条目已用 `sync_fragment_names.py` 恢复） |
| 门禁 | `--baseline 49` → **`--baseline 0 --limit 5`**（`.github/workflows/i18n-tqa.yml`） |
| 验证 | `tqa.py --gate` 绿（99.98/100，漂移 0）；`check_tr_coverage.py --gate --baseline 0` 绿；qm 运行时抽查 14/14 命中；全量编译通过 |

执行脚本：`scripts/i18n/fix_tr_leaks_batch2.py`（源码包裹）+ `scripts/i18n/fill_batch2_translations.py`（译文回填）。

**非 QObject 类的处理**（经继承链核实，共 4 处上下文用显式 `translate`）：

| 文件 | 所属 | context | 原因 |
|---|---|---|---|
| src/Network/Network.C:210 | 自由函数 `TestNetworkConnection()` | `IQmol::Network` | 非类成员，无 `tr()` |
| src/Parser/QChemOutputParser.C:1155 | `IQmol::Parser::QChemOutput` | `IQmol::Parser::QChemOutput` | `Parser::Base` 非 QObject |
| src/Qui/OptionDatabase.C:172/210/266 | `Qui::OptionDatabase` | `Qui::OptionDatabase` | 非 QObject |
| src/Viewer/BuildHandler.C:69 | `Handler::Build` | `Handler::Build` | `Handler::Base` 非 QObject |

**顺带修正**：`src/Main/MainWindow.C` 3 处 `tr()` 源码串原为中文（0de3fb9 引入，会导致英文界面也显示中文），已改为英文源码 + 译文分离。

## 一、分布（历史记录）

| 类别 | 数量 | 说明 |
|---|---|---|
| `QMsgBox` 错误/警告/信息（warning / information / critical / question） | 约 40 | `QMsgBox::warning(0,"IQmol","...")` 等，运行时提示，界面可见 |
| 配置器标签（setText / setLabel / setWindowTitle） | 9 | 约束 / 表面 / 坐标轴标签 |

## 二、清单（49 种，按字母序；2026-10-17 已全部清理）

| # | 原文 source | 出现位置 | consumer |
|---|-------------|----------|----------|
| 1 | ` energy` | src/Parser/QChemOutputParser.C:1155 | setLabel |
| 2 | `Alignment failed in Group::align` | src/Layer/GroupLayer.C:183 | warning |
| 3 | `Angle ` | src/Configurator/ConstraintConfigurator.C:164 | setText |
| 4 | `Atempt to remove unknown primitive type to molecule` | src/Layer/MoleculeLayer.C:1482 | warning |
| 5 | `Atom selection required` | src/Layer/MoleculeLayer.C:957 ; src/Layer/MoleculeLayer.C:1043 | warning |
| 6 | `Attempt to add unknown primitive type to molecule` | src/Layer/MoleculeLayer.C:1428 | warning |
| 7 | `Cognito Pool ID should start with the AWS region` | src/Process/AwsConfigurationDialog.C:70 | warning |
| 8 | `Configure Surface: ` | src/Layer/SurfaceLayer.C:64 | setWindowTitle |
| 9 | `Coordinate mismatch in Group alignment` | src/Layer/GroupLayer.C:169 | warning |
| 10 | `Copy results from server?` | src/Process/JobMonitor.C:845 | question |
| 11 | `Could not remove existing file ` | src/Viewer/Snapshot.C:199 | warning |
| 12 | `Delete Option?` | src/Qui/OptionDatabase.C:210 | question |
| 13 | `Delete Section?` | src/Qui/InputDialog.C:775 | question |
| 14 | `Directory name cannot contain spaces` | src/Process/JobMonitor.C:447 | warning |
| 15 | `Distance ` | src/Configurator/ConstraintConfigurator.C:142 | setText |
| 16 | `EGAD!` | src/Qui/OptionDatabase.C:266 | information |
| 17 | `Energy / Hartree` | src/Configurator/ExcitedStatesConfigurator.C:112 | setLabel |
| 18 | `Energy/Hartree` | src/Configurator/GeminalOrbitalsConfigurator.C:133 ; src/Configurator/OrbitalsConfigurator.C:322 | setLabel |
| 19 | `Error encountered` | src/Process/JobMonitor.C:321 | warning |
| 20 | `Failed to export server configuration` | src/Process/ServerConfigurationDialog.C:526 | warning |
| 21 | `Failed to open PDB file for writing` | src/Layer/SystemLayer.C:183 | critical |
| 22 | `File Not Saved` | src/Qui/InputDialog.C:495 | warning |
| 23 | `Host address not set` | src/Process/ServerConfigurationDialog.C:69 | warning |
| 24 | `Invalid string` | src/Viewer/ViewerModel.C:233 | warning |
| 25 | `Invalid username or password` | src/Network/Network.C:210 ; src/Process/JobMonitor.C:308 | warning |
| 26 | `Memory exceeds queue limit of ` | src/Process/QueueResourcesDialog.C:98 | warning |
| 27 | `Mesh simplification in progress` | src/Layer/SurfaceLayer.C:576 | information |
| 28 | `Movie making already in progress, please wait` | src/Viewer/Snapshot.C:185 | warning |
| 29 | `Network timeout` | src/Process/JobMonitor.C:313 | warning |
| 30 | `No molecule available.\n` | src/Viewer/BuildHandler.C:69 | warning |
| 31 | `No queues found on server` | src/Process/QueueResourcesDialog.C:42 | warning |
| 32 | `Number of CPUs exceeds queue limit of ` | src/Process/QueueResourcesDialog.C:106 | warning |
| 33 | `Option Exists` | src/Qui/OptionDatabase.C:172 | question |
| 34 | `Output file no longer exists` | src/Process/JobMonitor.C:934 | warning |
| 35 | `Passwords do not match` | src/Network/AwsConnection.C:230 | warning |
| 36 | `Position ` | src/Configurator/ConstraintConfigurator.C:56 | setText |
| 37 | `Problem calculating grid data` | src/Layer/GeminalOrbitalsLayer.C:275 | warning |
| 38 | `Scratch exceeds queue limit of ` | src/Process/QueueResourcesDialog.C:102 | warning |
| 39 | `Server name not set` | src/Process/ServerConfigurationDialog.C:69 | warning |
| 40 | `Still processing previous grid data request` | src/Layer/OrbitalsLayer.C:250 | warning |
| 41 | `Torsion ` | src/Configurator/ConstraintConfigurator.C:187 | setText |
| 42 | `Torsion between atoms ` | src/Configurator/ConstraintConfigurator.C:186 | setText |
| 43 | `Unable to nest fragments` | src/Layer/MoleculeLayer.C:1618 | warning |
| 44 | `User name must be set` | src/Process/ServerConfigurationDialog.C:98 | warning |
| 45 | `Validated wall time not in the format h:mm:ss` | src/Process/QueueResourcesDialog.C:82 | warning |
| 46 | `Wall time exceeds queue maximum of ` | src/Process/QueueResourcesDialog.C:95 | warning |
| 47 | `Wall time must be in the format h:mm:ss` | src/Process/QueueResourcesDialog.C:71 | warning |
| 48 | `Warning` | src/Qui/GeometryConstraint.C:408 | warning |
| 49 | `ffmpeg executable not found` | src/Viewer/Snapshot.C:192 | warning |

## 三、清理方式（每处二选一；本次 49 种全部走第 1 类"该译"）

1. **该译**：源码补 `tr("...")`（变量拼接的改为 `tr("...%1...").arg(x)`）→ 跑 `lupdate` 收敛进 `zh_CN.ts` → 补译文 → 重编 `zh_CN.qm`。
   > ⚠ TQA 已有「未完成条目 > 0」门禁：加 `tr()` 后**必须同步补译文**，否则 `tqa.py --gate` 会红。建议一处一提交，便于回退。
   > ⚠ `lupdate -no-obsolete` 会清掉 `FragmentTable` 等手工维护 context，之后必须跑 `scripts/i18n/sync_fragment_names.py --apply` 恢复。
2. **确认不译**（技术标识 / 内部用途）：加入 `scripts/i18n/source_tr_whitelist.json`，带 `reason`。

## 四、边界项处置（原建议 → 实际）

- ` energy`（QChemOutputParser.C:1155，setLabel）：**已译**「 能量」（显式 context `IQmol::Parser::QChemOutput`）。
- `Energy / Hartree`、`Energy/Hartree`：**已译**「能量 / Hartree」「能量/Hartree」（`Hartree` 为单位保留）。
- `EGAD!`（OptionDatabase 提示）：**已译**「天哪！」。

## 五、与白名单的关系

白名单 `source_tr_whitelist.json` 现 9 条：`IQmol`（品牌标题）、`" D"` / `"q = "`（物理符号 / 单位）、`energy` / `opt` / `scan` / `comment` / `efp_fragments` / `efp_parameters`（解析器 / Q-Chem 关键字）。这些为**已授权保留英文**，不在本清单。
