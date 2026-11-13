# IQmol 中文版 3.2.4.1 — 控制通道完整版

基于上游 IQmol 3.2.3 的简体中文本地化版本。本版在既有全界面汉化基础上，
补齐了 **Linux 分发包** 与 **本地控制通道**：外部程序（例如化学可视化插件）
无需模拟鼠标，即可查询状态、加载分子、播放动画、切换帧、生成表面并抓取快照。

## 本版变化

### 控制通道：10 个命令全部接通

通道是本机 Unix domain socket（Windows 为命名管道），每进程随机 token 写入
0600 发现文件，命令走白名单；token 错误的连接直接断开、不回任何内容。

| 类别 | 命令 | 说明 |
|---|---|---|
| 基础 | `ping` / `state` | 状态、版本、场景分子数/表面数/轨迹数/动画状态 |
| 加载 | `load` | 等 `fileOpened` 信号或 20 秒超时后再回复 |
| 快照 | `snapshot` | 离屏渲染 PNG，写入受限目录，路径逃逸无效 |
| 动画 | `play` / `pause` / `stop` | 驱动 Frequencies / GeometryList 层 |
| 帧 | `frame` | 只读查询各轨迹帧数，或按 `track` 切帧 |
| 表面 | `surface` / `listSurfaces` | 生成 vdW / 原分子 / SID 伪密度面并列出中文名 |

协议细节与真实接口适配说明见仓库 `docs/控制通道/控制通道集成说明.md`。

### 版本与打包

- 版本号由 CMake 在配置时用 `git describe` 生成，「关于」对话框、日志、
  控制通道三处一致，不再依赖停滞的 `src/version.h` 快照；
- deb 补装 `man iqmol`；FHS 布局 `/usr/bin/iqmol`、`/usr/lib/iqmol/`、
  `/usr/share/iqmol/`；
- 包内含应用与 Qt 两套中文翻译，随包运行库自收集，不依赖系统 Qt；
- 冒烟脚本 `scripts/iqmol_control_smoke.py` 共 22 项断言。

## 下载

| 文件 | 说明 |
|---|---|
| `iqmol_3.2.4.1_amd64.deb` | Debian / Ubuntu x86_64 安装包，`sudo apt install ./...` |
| `IQmol-linux-x86_64.tar.gz` | 解压即用：`tar xzf ... && ./IQmol-linux-x86_64/run.sh` |
| `SHA256SUMS.txt` | 上述两个包的校验和 |

校验：

```bash
sha256sum -c SHA256SUMS.txt
```

## 已知限制

- `surface` 只支持三种无需外部格点数据的伪密度面；轨道 / 电子密度面需要
  cube 数据，目前返回 `BAD_ARGS`；
- `load` 是追加语义，多次加载后 IQmol 会把先前的 system 设为不可见；
- 离屏（offscreen）环境下 3D 视图无法创建 GL 上下文，`snapshot` 需要真实或
  虚拟显示；软件渲染（llvmpipe）下偶见一次性几何伪影；
- 仅实测 Linux x86_64 与 Windows x64；macOS 未构建验证；
- Q-Chem 是独立第三方组件，其部分对话框仍为英文，不在本仓库汉化范围。

## 验证摘要

Ubuntu + Xvfb 下对 deb 安装后的版本实测：界面中文完整、冒烟 22/22 通过、
`frame` 切帧前后两次快照 MD5 不同、`surface vdw` 生成后表面数 1→2、
`play`/`pause`/`stop` 的计时器状态 true/false/false、双开不会抢占存活实例的
控制通道、`man iqmol` 命中、卸载无残留。

许可证 GPL-3.0，与上游一致。
