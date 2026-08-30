# IQmol3
IQmol version 3

> 📌 **本仓库 = IQmol3 官方版 + 简体中文全面本地化**
> 上游原版：[nutjunkie/IQmol3](https://github.com/nutjunkie/IQmol3)
>
> **文档导航**
>
> | 你想做什么 | 看这里 |
> |---|---|
> | 了解目录结构、代码模块、汉化文件在哪 | [仓库结构说明.md](仓库结构说明.md) |
> | 在 Windows 上编译出 IQmol.exe | [doc/构建说明-中文版.md](doc/构建说明-中文版.md) |
> | 子模块下载不动（国内网络） | 本文「子模块离线包」章节 |
> | 学会用这个软件 | [中文用户手册](doc/IQmolUserGuide.pdf)（34 页） |
> | 维护/更新翻译 | 本文「简体中文本地化」章节 + `scripts/update_translations.sh` |

This is IQmol, a molecular builder and visualization package written by Andrew
Gilbert.  IQmol is able to build molecules, set up and submit input for Q-Chem
calculations, and analyse the output.  Analyses include display of molecular
surfaces (densites, molecular orbitals) and animations of frequencies and 
reaction pathways.  A user guide can be found in the doc directory.

For an up-to-date list of features and pre-compiled binaries, please visit the 
website:  http://iqmol.org

This is a rebase of the original code that migrates to CMake and updates several
of the external libraries, including them as submodules in an attempt to ease the
build process.

The source relies on submodules, so to checkout the code use the recursive flag:

```
git clone --recursive https://github.com/nutjunkie/IQmol3.git
```

To compile, make sure that you QT installation can be found by cmake.  This
means that the CMAKE\_PREFIX\_PATH environment variable should include the
directory containing the Qt5Config.cmake file
```
export CMAKE_PREFIX_PATH=/directory/containing_Qt5Config.cmake
./configure
cd build
make
```

## 简体中文本地化（Simplified Chinese Localization）

本仓库在原版 IQmol3 基础上完成了面向简体中文用户的全面本地化：

- **界面翻译**：`translations/zh_CN.ts`（1519 条翻译，111 个上下文，全部完成），
  构建时由 CMake 自动调用 lrelease 生成 `zh_CN.qm` 并随可执行文件输出到
  `translations/` 目录。系统需安装 Qt5 Linguist 工具（lupdate/lrelease，
  如 `qtbase5-dev-tools`、`qttools5-dev-tools`），缺失时构建仍可继续，但界面回退英文。
- **源码国际化**：对约 20 个源文件补充了 `tr()` 包裹与可翻译上下文，使菜单、
  对话框、图层名称等运行期字符串可被翻译体系识别。
- **中文用户手册**：`doc/IQmolUserGuide.tex` 已翻译为中文（34 页，含反应路径、
  制作电影、配置三个补全章节），使用 `xelatex` 编译：
  ```
  ./scripts/build_docs.sh          # 编译 doc/IQmolUserGuide.pdf
  ./scripts/build_docs.sh --clean  # 编译后清理 LaTeX 中间文件
  ```
  手册配图位于 `doc/figures/`，其中对话框截图为中文界面实拍。
- **翻译维护**：源码变更后运行以下命令更新翻译并生成 qm（脚本会自动修复
  lupdate 因 GLObject.h 解析错误而误标的 vanished 条目）：
  ```
  ./scripts/update_translations.sh          # lupdate + 防退化 + lrelease
  ./scripts/update_translations.sh --sync   # 并同步 qm 到 build 目录
  ```
- **界面截图**：`dialog_screenshots/` 保存了中文界面下各对话框的运行时截图，
  可用于文档配图与翻译效果验证。

## 子模块离线包（国内网络适用）

`modules/` 下的 9 个第三方库是 Git 子模块，上游仓库体积较大，国内网络克隆时常断连、
卡在 6% 或直接 `Failed to connect to github.com:443`。为此本仓库在
**`submodules-package` 分支**提供了打包好的完整子模块源码（共 49,335 个文件），
版本与 `.gitmodules` 记录的 commit 完全一致，单文件 73 MB，无需合并：

下载这两个文件放到同一目录：

| 文件 | 大小 |
|---|---|
| [`IQmol-submodules.tar.gz`](https://github.com/stone-Glitch/IQmol-for-Chinese/raw/refs/heads/submodules-package/submodules-package/IQmol-submodules.tar.gz) | 73 MB |
| [`extract_submodules.bat`](https://github.com/stone-Glitch/IQmol-for-Chinese/raw/refs/heads/submodules-package/submodules-package/extract_submodules.bat) | 3.5 KB |

在 **cmd** 里带仓库路径运行（不是 PowerShell）：

```bat
cd /d D:\Downloads
extract_submodules.bat "D:\IQmol"
```

脚本会自动校验大小（`75,759,260` 字节）和 MD5（`9c0ed6e3527cf0dd1c8d5628cc31538f`），
然后解压到仓库根目录。也可以手动：

```bash
tar -xzf IQmol-submodules.tar.gz    # 在仓库根目录执行；MSYS2 终端最稳
```

> 选 tar.gz 而不是 zip：tar.gz 把文件打包成一个流再整体压缩，对 4.9 万个小文件
> 效率高得多——同样内容 tar.gz 只要 73 MB，zip 要 108 MB。

### OpenBabel 额外依赖（必看）

子模块解压后，OpenBabel 在编译期还会联网拉取 3 个依赖（maeparser / coordgenlibs / rapidjson），
国内网络拉不到会直接 `FATAL_ERROR`。本仓库另提供一个预置包（已按 `external/` 布局摆好），
解压到 **`modules/openbabel/`** 即可离线构建：

| 文件 | 大小 |
|---|---|
| `IQmol-openbabel-deps.tar.gz` | 1.2 MB |

```bat
cd /d D:\IQmol\modules\openbabel
tar -xzf D:\Downloads\IQmol-openbabel-deps.tar.gz
```

### 注意事项

- 下载慢时，把链接中的 `https://github.com/` 换成 `https://ghfast.top/https://github.com/` 走国内镜像
  （实测约 1.4 MB/s，支持断点续传）。
- **解压到仓库根目录**，不是 `modules` 里面——压缩包顶层就是 `modules/`。
- **仓库放短路径**（如 `D:\IQmol`），Windows 260 字符路径上限会导致深层目录解压失败。
- 解压后**不要**再运行 `git submodule update --init --recursive`，否则会重新联网克隆覆盖。
- **CMake 必须用 3.x（3.31）**，不要用 4.x（详见 `doc/构建说明-中文版.md`）。

完整步骤见该分支下的 `submodules-package/使用说明.md`。

