# 汉化工具脚本集（`scripts/i18n/`）

本目录存放 IQmol 中文本地化过程中使用的**辅助工具脚本**。它们不是构建必需的
组件，而是用于加速 `tr()` 改造、译文填充、手册生成与翻译校验的一次性/可复用工具。

> 项目规范：所有产出应使用结构化 Markdown，并清晰包含原文、译文、修改理由、责任人。
> 这些脚本正是为把上述人工流程半自动化而编写。

---

## 工具清单

| 脚本 | 语言 | 用途 | 关键说明 |
|---|---|---|---|
| `wrap_tr.py` | Python | 行号驱动的 `MainWindow.C` `tr()` 包裹 | 精确、注释安全；跳过品牌名 / 力场名 / 注释块 / 内部标识符 |
| `translate_iqmol.py` | Python | 全量 UI 字符串中译（V2） | 匹配优先级：已知译文 > 短语 > 单词组合 > 排除/保留；特殊处理全大写缩写、HTML 富文本、元素/同位素/溶剂名；未命中转 `unfinished` 供人工复核 |
| `fill_translations.py` | Python | 按 `source` 原文匹配填充 `zh_CN.ts` 译文 | 与 `translate_iqmol.py` 互补，用于把已审定译文落盘到 `.ts` |
| `build_manual.py` | Python | 由 `.tex` 生成自包含中文用户手册 HTML | 图片以 base64 内嵌，单文件可直接分发 |
| `verify_qm.cpp` | C++/Qt | 验证 `zh_CN.qm` 能否被 `QTranslator` 正确加载 | 复现应用加载逻辑（非 zh 区域强制 zh_CN），输出加载结果 |
| `verify_ext.cpp` | C++/Qt | 全量核对译文 | 读取 `zh_CN.ts` 真实 `(context, source)`，用 `.qm` 加载后逐条比对译文 |
| `known_translations.json` | JSON | `translate_iqmol.py` 使用的已知译文词典 | 术语统一的核心数据源，新增译法优先在此登记 |

---

## 重要：硬编码路径需调整

为便于在本环境直接运行，下列脚本内写死了绝对路径（基于本机检出位置）：

| 脚本 | 硬编码路径示例 | 需改为 |
|---|---|---|
| `wrap_tr.py` | `/workspace/IQmol3/src/Main/MainWindow.C` | 你的 `MainWindow.C` 实际路径 |
| `translate_iqmol.py` | `/workspace/IQmol3/translations/zh_CN_full.ts`、`/workspace/IQmol3/translations/zh_CN_new.ts`、`/workspace/scripts/known_translations.json` | 对应 `.ts` 与词典路径 |
| `fill_translations.py` | `/workspace/IQmol3/translations/zh_CN.ts` | 目标 `.ts` 路径 |
| `build_manual.py` | `/workspace/IQmol3/doc`、`/workspace/docs/IQmol用户手册.html` | 源码 `doc/` 与输出路径 |

> **建议**：运行前用编辑器把脚本顶部的 `FILE` / `TS` / `OUT` / `DOC` 等常量改为你的检出路径。
> 后续若希望开箱即用，可改为基于脚本自身位置（`__file__`）推导相对路径，欢迎提 PR。

---

## 典型用法

### 1. 校验已生成的翻译（无需重新编译源码）

```bash
# 编译校验程序（需 Qt5 开发包）
g++ verify_qm.cpp  -o verify_qm  $(pkg-config --cflags --libs Qt5Widgets)
g++ verify_ext.cpp -o verify_ext $(pkg-config --cflags --libs Qt5Widgets)

# 验证 qm 可被加载
./verify_qm  /path/to/build/bin/translations

# 逐条核对译文（对照 zh_CN.ts）
./verify_ext /path/to/build/bin/translations /path/to/IQmol3/translations/zh_CN.ts
```

### 2. 重新生成自包含中文手册

```bash
python3 build_manual.py     # 读取 doc/IQmolUserGuide.tex，输出中文手册 HTML
```

### 3. 重新跑全量翻译（仅在更新源串后）

```bash
python3 translate_iqmol.py  # 产出 zh_CN_new.ts
python3 fill_translations.py
```

---

## 责任人

| 工具 | 责任人 |
|---|---|
| 全部脚本 | WorkBuddy（汉化工程） |

> 译法争议时，先更新 `known_translations.json` 并同步 `doc/汉化对照表/` 中的对照表，
> 再重跑脚本，确保术语全局一致。
