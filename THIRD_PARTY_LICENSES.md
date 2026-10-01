> 🏠 [项目首页](README.md)

---

# 第三方许可证清单（Third-Party Licenses）

IQmol 中文版基于上游 **IQmol 3.2.3**，本仓库根目录 `LICENSE` 为上游继承的
**GPL-3.0-or-later**。在源码构建与 Windows 分发包（`IQmol-win64-3.2.3-zh_CN.zip`）
中，还会捆绑或链接以下第三方组件。请遵守各自许可证条款。

> 说明：版本号取上游 3.2.3 发布时对应的主流版本；若你的构建环境使用了不同版本，
> 请以实际构建所链接的库版本及其随附许可证为准。

| 组件 | 用途 | 许可证 | 上游 / 备注 |
|---|---|---|---|
| Qt 5（QtCore / Gui / Widgets / OpenGL / Sql / PrintSupport / Xml + LinguistTools） | 应用框架、UI、翻译体系 | **LGPL-3.0-only**（商业可选） | https://www.qt.io |
| libQGLViewer | 3D 视图交互 | **GPL-2.0-or-later** / Commercial | http://libqglviewer.com （静态链接需商业许可或 GPL 合规） |
| yaml-cpp | 配置文件解析 | **MIT** | https://github.com/jbeder/yaml-cpp |
| OpenMesh | 网格数据结构 | **BSD-3-Clause** | https://www.openmesh.net |
| OpenBabel 3.1.1 | 分子文件格式 / 力场 / 元素数据 | **GPL-2.0-or-later** | https://openbabel.org |
| libssh2 | SFTP 远程作业（Network 模块） | **BSD-3-Clause** | https://www.libssh2.org |
| libarchive | 压缩/归档（轨迹等） | **BSD-2-Clause** | https://libarchive.org |
| Boost（headers） | 通用 C++ 库 | **BSL-1.0（Boost Software License）** | https://www.boost.org |
| OpenSSL | 安全传输（MD5 等） | **Apache-2.0**（原 OpenSSL 许可） | https://www.openssl.org |
| ZLIB | 压缩 | **Zlib** | https://zlib.net |
| OpenGL / GLU | 3D 渲染 | **SGI Free Software License B**（类 MIT） | Khronos Group |
| OpenMP runtime（libgomp） | 并行 | **MIT / NCSA**（runtime 部分） | https://www.openmp.org |
| MinGW-w64 / libgfortran（Windows 构建） | 工具链与 Fortran 运行时 | **GPL-3.0-with-GCC-runtime-exception**（运行时库） | https://www.mingw-w64.org |
| Qt 翻译（qtbase_zh_CN.qm / qt_zh_CN.qm） | Qt 自带中文翻译 | **LGPL-3.0-only** | 随 Qt 分发 |

## 合规要点

- **GPL 传染性**：IQmol 本体与 OpenBabel、libQGLViewer 均为 GPL 系列，
  衍生分发需以 GPL 兼容方式提供完整对应源码（本仓库 `main` 分支即完整源码树）。
- **Qt LGPL 动态链接**：若以 LGPL 方式合规，Qt 必须以动态库形式提供并允许用户替换；
  当前 Windows 包为便于「双击即用」采用静态/捆绑方式，请按 Qt 商业或 GPL 条款评估。
- **Q-Chem 选项库（`qchem_option.db`）**：为 Q-Chem 输入关键词参考数据库，
  属上游文档性数据；汉化仅翻译其展示文案，不嵌入任何专有可执行代码。
- 各依赖的完整许可证文本可在对应上游仓库获取；本清单为汇总，不构成法律意见。

---

> 维护者：@stone-Glitch ｜ 最后整理：2026-10-01
