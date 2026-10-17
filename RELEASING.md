# RELEASING — 发布规范

> 回应审计报告 §3.1/§3.3/§16.2.3/§16.2.5。本文件定义发布闸门与资产治理，杜绝「同名资产静默替换」。

## 1. 版本字段

- 版本号单一来源：`CMakeLists.txt` 的 `project(... VERSION x.y.z)`。
- 发布标签格式：`v<上游版本>-zh_CN`（当前 `v3.2.4.1-zh_CN`）。
- `scripts/publish_release.sh` 已改为**从 CMakeLists 自动派生**版本，不再硬编码，避免标签/资产名与 CMake 矛盾。

## 2. 资产命名（唯一性）

- 每个 Release 的资产文件名**必须唯一**，禁止跨 Release 复用同名文件。
- 推荐带构建日期后缀：`IQmol-win64-<VER>-zh_CN-<YYYYMMDD>.zip`。
- `publish_release.sh` 在检测到同名资产已存在时**拒绝静默覆盖**，报错并提示改用唯一文件名。

## 3. 必附材料

每个 Release 目录固定包含：

1. `IQmol-*.zip` / `*.tar.gz`（构建产物）
2. `SHA256SUMS.txt`（对所有资产生成）
3. 构建来源 commit（`git rev-parse HEAD`）
4. 发布说明（`docs/构建与打包/release_notes.md`）

## 4. 签名与 provenance（规划中）

- 短期：Ed25519 对 `SHA256SUMS.txt` 签名，公钥固定到仓库，提供 `SHA256SUMS.txt.sig`。
- 中长期：引入 Cosign / Sigstore / SLSA（需托管密钥，私钥不进仓库）。

## 5. 发布闸门

发布前逐项确认：

- [ ] 版本字段与 CMakeLists 一致
- [ ] 资产文件名唯一（无跨 Release 同名）
- [ ] `SHA256SUMS.txt` 已生成且校验通过
- [ ] 构建来源 commit 已冻结并记录
- [ ] 子模块 commit 与 `dependencies.lock` 一致
- [ ] 翻译更新（如有）
- [ ] 文档与发布版本同步
- [ ] 回滚版本已确定

任一项失败 → 标记为 `Pre-release`。

## 6. 回滚

- 出现启动即崩溃、关键分子文件无法打开、密钥泄露、严重许可证/安全问题、同名资产被静默替换时，立即撤回当前 Release。
- 保留事故 Release 的哈希与日志，**禁止删除旧 Release**。
- 创建事故 Issue，发布修复版本后重测，更新 `SECURITY.md` 或事故说明。
