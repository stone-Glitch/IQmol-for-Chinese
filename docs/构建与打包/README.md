> 🏠 [项目首页](../../README.md) › [文档中心](../README.md)

---

# 构建与打包（索引）

本目录收录 **从源码到分发包的完整构建、打包、发布流程**，面向构建者与维护者。

> 维护者：@stone-Glitch ｜ 最后整理：2026-11-14

---

## 一、构建

| 文件 | 内容 | 适用对象 |
|---|---|---|
| [`构建与部署指南.md`](构建与部署指南.md) | ★ 构建总入口：环境依赖、CMake 配置、编译、验证构建结果（第七章）、常见构建故障速查 | 所有人 |
| [`下载源码直接打包.md`](下载源码直接打包.md) | 从 `main` 分支下载源码后**零补丁**直接出包的最短路径（普通用户请走这条） | 打包者 |

## 二、分发包

| 文件 | 内容 | 适用对象 |
|---|---|---|
| [`Linux分发包.md`](Linux分发包.md) | Linux 分发包的目录布局、插件规划与瘦身策略 | 打包者 |
| [`release_notes.md`](release_notes.md) | ★ **v3.2.4.1-zh_CN-r2 发布说明**，同时是 [`release.yml`](../../.github/workflows/release.yml) 的 `--notes-file` 真源：10 个控制命令、版本与打包变化、已知限制 | 发布者 / 使用者 |
| [`SHA256SUMS.txt`](SHA256SUMS.txt) | **v3.2.4.1-zh_CN-r2 全资产校验和汇总**（Linux deb / tar.gz + Windows zip），本地维护副本，便于 `sha256sum -c` 核对 | 使用者 / 发布者 |

> ✅ **校验和口径（2026-11-14 修复）**：`release.yml` 与 `windows-mingw.yml` 曾都上传
> 名为 `SHA256SUMS.txt` 的附件，后完成的 Windows 工作流覆盖前者，导致
> `v3.2.4.1-zh_CN-r2` 的 Release 只剩 Windows 一行。现已改为
> `SHA256SUMS-linux.txt` / `SHA256SUMS-windows.txt` 两个独立文件，
> **下次打 tag 发版生效**。本目录的 `SHA256SUMS.txt` 仍是三资产人工汇总副本；
> 权威性以 Release 页附件为准。

## 三、CI 与发布

| 工作流 | 触发 | 产出 |
|---|---|---|
| [`release.yml`](../../.github/workflows/release.yml) | push tag `v*-zh_CN*` / 手动 | ubuntu-24.04 现场编译 → `package_linux.sh` + `package_linux_deb.sh` → `sha256sum` → `gh release create` 上传 deb、tar.gz、`SHA256SUMS-linux.txt` |
| [`windows-mingw.yml`](../../.github/workflows/windows-mingw.yml) | push main / tag `v*` / 手动 | Windows zip / 7z + `SHA256SUMS-windows.txt`，打 tag 时附加到同一 Release（分平台命名，避免覆盖 Linux 校验和） |
| [`ubuntu-2404.yml`](../../.github/workflows/ubuntu-2404.yml) | push / PR | x86_64、arm64 编译 + ctest |
| [`i18n-tqa.yml`](../../.github/workflows/i18n-tqa.yml) | push / PR | 译文六维质量门禁 |
| [`verify-replay.yml`](../../.github/workflows/verify-replay.yml) | push / PR | 干净上游树重放校验 |
| [`macos.yml`](../../.github/workflows/macos.yml) | push main / tag `v*` / 手动 | macOS 15 (arm64) 编译 + macdeployqt + zip，**草案待 runner 验证**（`macos-14` 镜像已于 2026-11-02 退役，见工作流头注释） |

发布只需打 tag 并推送，CI 完成编译、打包与 Release 创建（runner 自带
`GITHUB_TOKEN`，本机无需保存凭证）：

```bash
git tag -a v3.2.4.1-zh_CN-r3 -m "发布说明"
git push origin v3.2.4.1-zh_CN-r3
```

---

## 相关目录

- 构建故障的诊断记录见 [`../验证记录/README.md`](../验证记录/README.md)。
- 控制通道（10 个命令、冒烟脚本）见 [`../控制通道/控制通道集成说明.md`](../控制通道/控制通道集成说明.md)。
- 上游升级迁移流程见 [`../汉化工程/上游升级迁移指南.md`](../汉化工程/上游升级迁移指南.md)。

---

> 维护者：@stone-Glitch ｜ 最后整理：2026-11-14
