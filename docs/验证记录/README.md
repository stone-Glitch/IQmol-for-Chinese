# 构建与验证记录（索引）

本目录归档 IQmol 汉化版的**编译、运行验证、问题诊断与质量检查**记录，用于追溯
每一条结论的依据。所有验证均基于真实编译 + 真实运行（非仅静态推演）。

---

## 一、记录清单

| 文件 | 类型 | 说明 | 日期 |
|---|---|---|---|
| [`2026-09-13-编译与运行验证.md`](2026-09-13-编译与运行验证.md) | 运行验证 | Ubuntu 24.04 完整编译 + 真实运行 + 中文界面截图，1519 条译文 0 未译 | 2026-09-13 |
| [`2026-09-13-OpenBabel插件加载失败诊断与修复.md`](2026-09-13-OpenBabel插件加载失败诊断与修复.md) | 问题诊断 | `Unable to find OpenBabel plugins` 根因（静态插件自注册被 ld 丢弃）与两层修复 | 2026-09-13 |
| [`2026-09-13-仓库整理报告.md`](2026-09-13-仓库整理报告.md) | 整理报告 | 文档过时路径修正、结构对齐、工作区归置 | 2026-09-13 |
| [`IQmol-i18n-构建验证指南.md`](IQmol-i18n-构建验证指南.md) | 构建指南 | 端到端翻译管线（tr → lupdate → ts → lrelease → QTranslator）打通说明；含环境要求、构建步骤、翻译加载逻辑 | 早期（2026-08-28，2026-09-13 补注） |
| [`程序检查记录表.md`](程序检查记录表.md) | 质量检查 | 26 大类通用检查裁剪到本项目的全量核查表（构建/术语/文档/法律合规等），33 项全过 | 早期 |

---

## 二、验证截图

运行时中文界面截图（与 `编译与运行验证.md` 配套）：

| 截图 | 内容 |
|---|---|
| `01_主界面.png` | 主界面（菜单 / 面板 / 状态栏全中文） |
| `02_文件菜单.png` | 文件菜单（中英对照） |
| `03_显示菜单.png` | 显示菜单 |
| `04_计算菜单.png` | 计算菜单 |

> 对话框级中文截图另见仓库根 `dialog_screenshots/`（`AboutDialog.png`、`QUI.png`、
> `ServerDialog.png` 等）与 `doc/figures/`。

---

## 三、如何复现验证

### 1. 编译（以 Linux 为例）

```bash
apt-get install -y gcc g++ cmake make qtbase5-dev qtbase5-dev-tools \
  qttools5-dev libqt5opengl5-dev libqt5sql5-sqlite libboost-dev libssl-dev \
  zlib1g-dev libglu1-mesa-dev libgl1-mesa-dev libxml2-dev libarchive-dev \
  libssh2-1-dev libopenbabel-dev openbabel
mkdir build_linux && cd build_linux
cmake .. -DCMAKE_BUILD_TYPE=Release
make -j$(nproc)
```

Windows 与 macOS 流程见仓库 `scripts/`（`build_windows.sh`、`mac_deploy.sh`）。

### 2. 运行（无显示环境）

```bash
xvfb-run -a -s "-screen 0 1280x1024x24" env \
  QT_QPA_PLATFORM=xcb BABEL_DATADIR=/usr/share/openbabel \
  ./IQmol
```

启动后应看到日志 `[i18n] Loaded translation: "zh_CN"`。

### 3. 校验翻译资产

参见 [`scripts/i18n/README.md`](../../scripts/i18n/README.md)：用 `verify_qm.cpp` /
`verify_ext.cpp` 核对 `zh_CN.qm` 可被 `QTranslator` 加载、且译文与 `zh_CN.ts` 一致。

---

## 四、翻译对照与术语

- 逐条译法、修改理由、责任人见 [`doc/汉化对照表/`](../汉化对照表/)。
- 汉化完整性核查（约 71 处英文残留及处理建议）见 [`doc/界面英文残留清单.md`](../界面英文残留清单.md)。
- 术语遵循全国科学技术名词审定委员会官方译法，保持全表一致。
