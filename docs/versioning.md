# 版本与分支管理

## 命名

- 版本分支使用 `version/tc-vX.Y.Z`，例如 `version/tc-v0.0.3`。
- 发布标签使用 `tc-plane-vX.Y.Z`，与部署变量 `APP_VERSION` 保持一致。

## 创建版本分支

1. 确认 `main` 是本次版本的基线且工作区干净。
2. 从 `main` 创建版本分支：`git switch -c version/tc-vX.Y.Z main`。
3. 立即推送并设置上游：`git push --set-upstream origin version/tc-vX.Y.Z`。
4. 在根 `package.json` 更新版本号，并更新社区部署中 `APP_VERSION` 的默认值。
5. 在路线图登记本版本尚未完成的功能。

## 版本内维护

- 功能开始、范围变化或负责人调整时更新路线图。
- 功能完成时，将条目从路线图移入功能归档，并附上完成日期和交付链接。
- 影响系统边界的改动更新架构文档；影响多个模块或存在明确权衡的改动新增 ADR。

## 发布与合并

1. 完成目标版本的检查，并核对版本元数据、路线图、归档和 ADR。
2. 切换至 `main` 并合并版本分支：`git merge --ff-only version/tc-vX.Y.Z`。
3. 创建发布标签：`git tag tc-plane-vX.Y.Z`。
4. 推送 `main`、版本分支和标签至 `origin`。

产品文案中的版本示例不属于发布元数据，不因创建版本分支而调整。
