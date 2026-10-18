# Windows CI 子模块漂移误报根因修复与验证（2026-10-18）

> 对应工作项：Windows CI（`windows-mingw.yml`）run #3 / #4 / #5 三连败 → run #6 全绿（`fc2c7e7`）。
> 修复提交：`fc2c7e7`（`scripts/check_submodules_drift.sh` + `scripts/build_windows.sh`）。

## 一、故障现象

| 项 | 实况 |
|---|---|
| 失败运行 | run #3 / #4 / #5，均在约 2 分钟内快速失败（远早于正常构建时长） |
| 报错 | `::error:: 子模块 modules/hdf5 版本漂移：清单 a0edeee… != 仓库 a0edeee…`，exit 1 |
| 点名模块 | `modules/hdf5` |
| 对照面 | Linux 本地与 Ubuntu CI **全部通过**；MANIFEST 与 gitlink 人工比对一致 |
| 附带症状 | CI 注释里的错误消息被 `\r` 截断，日志只剩半句（「清单 <sha>」之后消失），极难排查 |

注意报错里「清单 sha != 仓库 sha」两串**肉眼相同**——这是本题的钥匙：失配的不是内容，是**不可见字符**。

## 二、根因（双重叠加，缺一不可）

本地构造 CRLF Python wrapper（`sed` 给每行 stdout 追加 `\r`，模拟 hostedtoolcache 原生 Windows Python）后，**旧脚本逐字复现** CI 报错（含点名 hdf5），根因证实：

1. **CRLF 污染（主因）**：Windows runner 上的 `python3` 是 hostedtoolcache 原生 Windows Python，stdout 文本模式把 `\n` 写成 `\r\n`——清单侧每个 sha 带尾随 `\r`，与 gitlink 侧（git 输出无 `\r`）**永远失配**。同一报错消息里的 `\r` 还会让 CI 注释渲染器在该处截断。
2. **locale 敏感排序（帮凶/误导项）**：`en_US.UTF-8` 下 `sort` 字典序忽略大小写，`modules/hdf5` 排到 `HighFive` 之前（C locale 相反）。于是「第一个被比对的条目」随环境变化，报错点名不稳定——这也是为什么三连败都点名 hdf5，而本地 C locale 下第一个被比对的总是 HighFive。

## 三、修复清单（`fc2c7e7`）

`scripts/check_submodules_drift.sh`：

| # | 措施 | 位置 |
|---|---|---|
| 1 | `export LC_ALL=C` 固定排序，附带完整根因注释块 | 脚本头部（31 行） |
| 2 | gitlink 侧 `git ls-tree` 输出 `tr -d '\r'` | 63 行 |
| 3 | 清单侧 `tr -d '\r'` 后再排序 | 77 行 |
| 4 | `cur_sha` awk 取值后同样剥 `\r` | 85 行 |
| 5 | Python 侧改 `sys.stdout.buffer.write(...encode("utf-8"))` 写字节，不经文本模式换行转换 | 74 行 |
| 6 | 漂移 / MISSING / EXTRA 详情全部**前移至 `fail()` 之前**打印——原写法中 `fail()` 内部 `exit 1`，写在它后面的 echo 是死代码 | 87 行起 |

`scripts/build_windows.sh`（连带修复 strict 校验空转）：

- CMake 3.31.6 官方发布包 SHA256 钉入内置表（`d163cd3a…4f836`，与 Kitware 官方 `cmake-3.31.6-SHA-256.txt` 核对）；
- 期望值优先级：环境变量 `CMAKE_ZIP_SHA256` > 内置哈希表 > 空（**拒绝，失败关闭**）——此前 CI 未设该环境变量，strict 校验实际空转，遇 MSYS2 CMake 4.x 触发自动下载时会误报「下载被劫持」；
- `lookup_sha256` 补 `tr -d '\r'` 防护。

## 四、回归验证矩阵

| 场景 | 旧脚本 | 新脚本 |
|---|---|---|
| CRLF 模拟环境（正常清单） | ❌ 复现 CI 报错（点名 hdf5，exit 1） | ✅ exit 0 |
| 篡改 MANIFEST 中 sha（门禁有效性） | — | ❌→✅ 正确报漂移，exit 1（门禁未失效） |
| 还原 MANIFEST | — | ✅ exit 0 |
| 真实 Linux 环境 | ✅ | ✅ |
| 远程 Windows CI run #6（`fc2c7e7`） | — | ✅ **成功 19m53s**，产物 `IQmol-windows-x64-zh_CN` 54.9 MB |

修复后三工作流全绿：i18n TQA #61 / Ubuntu #177 / Windows #6。

## 五、教训（可迁移）

- **跨平台脚本三件套**：`LC_ALL=C` + 双侧剥 `\r` + 写字节，缺一不可；
- 「清单 sha != 仓库 sha 而肉眼相同」= 大概率是不可见字符（`\r` / BOM / NBSP），先 `xxd` 再谈逻辑；
- CI 注释被截断只剩半句时，优先怀疑消息里混入了 `\r`；
- shell 里 `fail()` 若内含 `exit`，其后的 echo 全是死代码——详情必须先打印后 fail。

---

> 维护者：@stone-Glitch ｜ 记录日期：2026-10-18
