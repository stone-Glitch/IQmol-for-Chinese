# 源码侧未 tr() 字符串清单（P2-10）

> 生成：2026-10-17，由 `scripts/i18n/check_tr_coverage.py` 扫描 `src/`（排除 `save/` 备份副本 + 白名单）得出。
> **门禁策略**：防恶化 `baseline=49` + 目标上限 `5`（用户 2026-10-17 决策）。当前 49 种为基线，禁止新增；分批清零到 ≤5 后，把 `.github/workflows/i18n-tqa.yml` 的 `--baseline 49` 改为 `5`，即收紧为硬门禁。
> **性质**：#43（界面英文残留排查）当时只修了其清单内列的 71 处；本清单是**新增发现**——全仓 `QMsgBox` 错误/警告信息与约束/表面配置器标签从未被 `tr()` 包裹，`lupdate` 扫不到，界面显示英文。

## 一、分布

| 类别 | 数量 | 说明 |
|---|---|---|
| `QMsgBox` 错误/警告/信息（warning / information / critical / question） | 约 40 | `QMsgBox::warning(0,"IQmol","...")` 等，运行时提示，界面可见 |
| 配置器标签（setText / setLabel / setWindowTitle） | 9 | 约束 / 表面 / 坐标轴标签 |

## 二、清单（49 种，按字母序）

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

## 三、清理方式（每处二选一）

1. **该译**：源码补 `tr("...")`（变量拼接的改为 `tr("...%1...").arg(x)`）→ 跑 `update_translations.sh` / `lupdate` 收敛进 `zh_CN.ts` → 补译文 → 重编 `zh_CN.qm`。
   > ⚠ TQA 已有「未完成条目 > 0」门禁：加 `tr()` 后**必须同步补译文**，否则 `tqa.py --gate` 会红。建议一处一提交，便于回退。
2. **确认不译**（技术标识 / 内部用途）：加入 `scripts/i18n/source_tr_whitelist.json`，带 `reason`。

## 四、边界项（建议先裁决再处理）

- ` energy`（QChemOutputParser.C:1155，setLabel）：Q-Chem 输出能量列标签，界面可能可见，建议译「能量」。
- `Energy / Hartree`、`Energy/Hartree`：坐标轴单位标签，`Hartree` 为单位可保留、`Energy` 可译。
- `EGAD!`（OptionDatabase 提示）：口语化，建议译。

## 五、与白名单的关系

白名单 `source_tr_whitelist.json` 现 9 条：`IQmol`（品牌标题）、`" D"` / `"q = "`（物理符号 / 单位）、`energy` / `opt` / `scan` / `comment` / `efp_fragments` / `efp_parameters`（解析器 / Q-Chem 关键字）。这些为**已授权保留英文**，不在本清单。
