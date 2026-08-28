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

