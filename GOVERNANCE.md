# GOVERNANCE — 项目治理

> 本文件回应外部审计报告 §16.2.1 的治理文件缺口。定位与上游关系以本仓实际为准。

## 1. 项目定位

**IQmol3 简体中文本地化与实验性分发项目**。

- 基于上游 **IQmol3**（`nutjunkie/IQmol3`）。
- 原作者：**Andrew Gilbert**。
- 当前项目 **不是** IQmol 官方项目，**不是** IQmol 官方中文版。
- 当前版本为本地化实验版本；功能兼容性、稳定性与安全性仍在验证中。
- 不建议使用「官方中文版」「完整汉化」「生产级稳定」「所有平台开箱即用」「已通过完整安全审计」等表述。

## 2. 与上游的关系

- 上游衍生关系由本仓自证（GitHub 未显示 Fork 关系）。
- 上游基线 commit 与版本见 `dependencies.lock` 与 `CMakeLists.txt` 的 `project(VERSION)`。
- 同步上游见 `scripts/sync_upstream.sh`（默认只读 `--status`，禁止直接合并未审查的 diff）。

## 3. 维护者与决策

| 角色 | 当前承担者 | 备注 |
|---|---|---|
| 维护者 | stone-Glitch | 仓库所有者 |
| Release 发布人 | stone-Glitch | 通过 `scripts/publish_release.sh`（需 `GITHUB_TOKEN`） |
| 回滚负责人 | stone-Glitch | 见 `RELEASING.md` 回滚流程 |
| 安全事件处理 | stone-Glitch | 见 `SECURITY.md` |

决策方式：当前为单人维护，重要发布/回滚在仓库 Issue 留痕。

## 4. 发布与回滚

见 [`RELEASING.md`](./RELEASING.md)。核心原则：**每个 Release 使用唯一资产文件名、不静默覆盖同名资产、必须随附 `SHA256SUMS.txt`**。

## 5. 安全事件

见 [`SECURITY.md`](./SECURITY.md)。
