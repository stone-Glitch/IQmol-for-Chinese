# Linux 分发包

`scripts/package_linux.sh` 把构建产物与全部运行期依赖收集成**解压即用**的
`dist/IQmol-linux-x86_64.tar.gz`，目标机器无需安装 Qt 或 OpenBabel。

---

## 一、制作

前置：已完成构建（`configure + make`，产物为 `build/IQmol`），且装了
`qttools5-dev-tools`（提供 `lrelease`）。

```bash
bash scripts/package_linux.sh                     # 输出 dist/IQmol-linux-x86_64.tar.gz
bash scripts/package_linux.sh --build DIR         # 指定构建目录（默认 <源码根>/build）
bash scripts/package_linux.sh --out DIR           # 指定输出目录（默认 <源码根>/dist）
bash scripts/package_linux.sh --no-strip          # 不 strip 可执行文件（便于调试）
```

脚本流程：复制可执行文件 → 用 `lrelease` 生成 `zh_CN.qm` 并**放两处** →
`ldd` 递归收集 Qt 运行库与插件 → 收集 `share/`（着色器、片段库、OpenBabel 数据、
`qchem_option.db`）与 OpenBabel 运行期插件 → 精选 `samples/` 示例分子 →
生成 `run.sh` → 自检翻译文件 → 打包。

## 二、使用

```bash
tar xzf IQmol-linux-x86_64.tar.gz
./IQmol-linux-x86_64/run.sh              # 推荐：注入全部运行时环境
./IQmol-linux-x86_64/bin/IQmol           # 也可直接运行（源码已补包内路径搜索）
./IQmol-linux-x86_64/run.sh 分子.xyz     # 启动并打开指定文件
```

`run.sh` 会设置 `LD_LIBRARY_PATH`、`QT_PLUGIN_PATH`、`BABEL_DATADIR`、
`BABEL_LIBDIR`，并把着色器/片段库/Q-Chem 选项库路径写入
`~/.config/iqmol.org/IQmol.conf`（IQmol 在 Linux 下硬编码 `/usr/share/iqmol`，
只能用配置文件覆盖）。

## 三、包结构

| 路径 | 内容 |
|---|---|
| `bin/IQmol` | 可执行文件（界面全中文） |
| `bin/translations/zh_CN.qm` | 翻译（与 `applicationDirPath()` 对齐） |
| `translations/zh_CN.qm` | 翻译（包根布局，**双保险**） |
| `lib/` | Qt 运行库 + 插件 + OpenBabel 运行期插件（`lib/openbabel/<版本>/`） |
| `share/` | shaders / fragments / openbabel 数据 / `qchem_option.db` |
| `samples/` | 精选示例分子（单文件 ≤ 1 MB）+ 中文《示例说明.md》 |
| `run.sh` | 一键启动 |

## 四、两个关键设计（踩过坑的地方）

**1. 翻译文件必须放两处。** 源码 `IQmolApplication::loadTranslations()` 按
`applicationDirPath()`（`bin/`）推算翻译位置，而 Linux 包历来把 qm 放在包根。
历史缺陷 **reA22A**：只放包根时**只有恰好从包根启动才加载成功**（偶然命中
`cwd/translations`），从桌面图标或其它路径启动都静默回退英文。现同时放两处，
并在源码侧补上 `../translations` 搜索路径；`run.sh` 也显式 `cd` 包根。
修复前后的 A/B 实测见仓库外《IQmol-Linux分包-reA22A修复与验收报告.md》。

**2. OpenBabel 数据与插件要随包。** 源码原先把 `BABEL_LIBDIR` / `BABEL_DATADIR`
编译期硬编码为 `/usr/...`，目标机器未装 OpenBabel 时格式转换与力场会**静默失效**。
现优先探测包内 `lib/openbabel/<版本>` 与 `share/openbabel`，找不到才回退系统路径。

## 五、验证

```bash
# 从任意目录启动都应有这行日志（注意日志走 stderr）
QT_QPA_PLATFORM=offscreen ./bin/IQmol zh_CN 2>&1 | grep '\[i18n\]'
# → [i18n] Loaded translation: "zh_CN"

# 打开示例分子，应看到力场计算日志
./run.sh samples/3nir.pdb
# → DEBUG ... Computing energy with forcefield "UFF"
```

## 六、已知事项

- 包体约 46 MB（`lib/` 收集了全量递归依赖，后续可按需裁剪）。
- 将轨迹导出为视频需另行安装 ffmpeg 并加入 PATH（可选）。
- 大体量示例数据（17 MB cube、16 MB fchk、14 MB 谱图目录）未随包，从仓库单独获取。
