# IQmol 中文版（Linux x86_64）

IQmol v3.2.3 分子编辑与可视化软件的中文本地化版本。
**解压即用，无需安装，不污染系统。**

---

## 一、快速开始

```bash
tar xzf IQmol-linux-x86_64.tar.gz
cd IQmol-linux-x86_64
./run.sh                 # 启动
./run.sh 分子文件.xyz     # 启动并打开指定文件
```

首次运行 `run.sh` 会自动把资源路径写入 `~/.config/iqmol.org/IQmol.conf`，
输出 `[run.sh] 已写入资源路径到 ...` 属正常提示。

---

## 二、系统要求

| 项目 | 要求 |
|---|---|
| 架构 | x86_64 |
| 系统 | 主流 Linux 发行版（glibc 2.35+，如 Ubuntu 22.04+ / Debian 12+ / Fedora 36+） |
| 图形 | 支持 OpenGL 2.0+ 的显卡驱动（软件渲染 llvmpipe 亦可） |
| 桌面 | X11（Wayland 下通过 XWayland 运行） |

> 包内已包含 Qt5、OpenBabel、OpenMesh、QGLViewer 等全部依赖库，
> **无需**额外安装 Qt 或 OpenBabel。

---

## 三、目录结构

```
IQmol-linux-x86_64/
├── run.sh                  启动脚本（设置运行环境 + 注入资源路径）
├── bin/
│   └── IQmol               主程序（11.9 MB）
├── lib/
│   ├── *.so                45 个依赖库（Qt5/OpenBabel/OpenMesh/QGLViewer/...）
│   └── plugins/            Qt 插件（platforms/imageformats/sqldrivers/...）
├── share/
│   ├── shaders/            着色器（Cel/Gooch/Gouraud/Phong/Plastic）
│   ├── fragments/          分子片段库（710 个文件）
│   ├── openbabel/          OpenBabel 数据文件（元素/键参数等）
│   └── qchem_option.db     Q-Chem 选项数据库
└── translations/
    └── zh_CN.qm            中文翻译（1519 条）
```

---

## 四、汉化范围

界面菜单已完整汉化：

| 菜单 | 示例条目 |
|---|---|
| 文件 | 关于、新建分子、新建查看器、打开、打开最近、关闭查看器、保存、另存为、保存图片、录制动画、显示消息日志、退出 |
| 编辑 | 编辑菜单项 |
| 显示 | 全屏、重置视图、显示坐标轴、相机、外观、原子标签 |
| 构建 | 构建菜单项 |
| 计算 | Q-Chem 设置、任务监视器、编辑服务器 |
| 帮助 | 帮助菜单项 |

界面其他元素：模型视图面板、全局、历史记录、欢迎使用 IQmol、状态栏提示等。

翻译总数 **1519 条**，无未翻译条目。

---

## 五、常见问题

### 1. 提示 `error while loading shared libraries: libQt5Core.so.5`

未通过 `run.sh` 启动导致。`run.sh` 会设置 `LD_LIBRARY_PATH` 指向包内 `lib/`。
请坚持使用 `./run.sh`。

### 2. 提示 `Could not load the Qt platform plugin "xcb"`

缺少 X11 相关系统库。安装：

```bash
# Debian / Ubuntu
sudo apt install libxcb-xinerama0 libxcb-icccm4 libxcb-image0 \
     libxcb-keysyms1 libxcb-randr0 libxcb-render-util0 \
     libxcb-shape0 libxcb-xkb1 libxkbcommon-x11-0
# Fedora / RHEL
sudo dnf install xcb-util-wm xcb-util-image xcb-util-keysyms \
     xcb-util-renderutil libxkbcommon-x11
```

### 3. 界面显示英文

确认 `translations/zh_CN.qm` 存在；若手动移动过文件，需保持与 `bin/IQmol` 的
相对位置（`run.sh` 会处理翻译加载路径）。

### 4. 启动后 3D 视图空白 / 黑屏

显卡驱动不支持所需 OpenGL 版本。可尝试软件渲染：

```bash
LIBGL_ALWAYS_SOFTWARE=1 ./run.sh
```

### 5. 想恢复英文界面

删除或改名翻译文件：

```bash
mv translations/zh_CN.qm translations/zh_CN.qm.bak
```

### 6. 想删除资源路径配置

```bash
rm -rf ~/.config/iqmol.org
```

---

## 六、卸载

本程序不安装到系统，直接删除解压出的目录即可：

```bash
rm -rf IQmol-linux-x86_64
rm -rf ~/.config/iqmol.org      # 可选：清除个人偏好设置
```

---

## 七、构建信息

| 项目 | 值 |
|---|---|
| 源码版本 | IQmol v3.2.3（Tag v3.2.2-1-g485ddc6） |
| 编译环境 | Ubuntu 24.04 / GCC 13.3.0 / CMake 3.28 |
| 构建类型 | Release |
| 目标平台 | Linux x86_64 |

源码与构建脚本：<https://github.com/stone-Glitch/IQmol-for-Chinese>

---

## 八、许可

IQmol 遵循 GNU General Public License v3。
本包为 GPL 衍生作品，同样遵循 GPLv3。
详见包内源码仓库中的 LICENSE 文件。
