# IQmol3
IQmol version 3

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
**`submodules-package` 分支**提供了打包好的完整子模块源码（108 MB，分 3 卷），
版本与 `.gitmodules` 记录的 commit 完全一致。

**下载**（3 个分片均需下载）：

| 分片 | 大小 |
|---|---|
| [`part_00`](https://github.com/stone-Glitch/IQmol-for-Chinese/raw/refs/heads/submodules-package/submodules-package/part_00) | 45 MB |
| [`part_01`](https://github.com/stone-Glitch/IQmol-for-Chinese/raw/refs/heads/submodules-package/submodules-package/part_01) | 45 MB |
| [`part_02`](https://github.com/stone-Glitch/IQmol-for-Chinese/raw/refs/heads/submodules-package/submodules-package/part_02) | 18 MB |

下载慢时，把链接中的 `https://github.com/` 换成 `https://ghfast.top/https://github.com/` 走国内镜像。

**合并并解压到仓库根目录**：

```bash
cat part_00 part_01 part_02 > IQmol-submodules.zip   # Linux/macOS/MSYS2
# Windows cmd: copy /b part_00 + part_01 + part_02 IQmol-submodules.zip
unzip -o IQmol-submodules.zip                        # 必须在仓库根目录执行
```

合并后校验：大小 `112,618,126` 字节，MD5 `787d6023c5ec715ec0334427da4baa75`。
完整步骤（含 Windows PowerShell 写法、校验命令、常见问题）见该分支下的
`submodules-package/使用说明.md`。

> 解压后**不要**再运行 `git submodule update --init --recursive`，否则会重新联网克隆覆盖。

