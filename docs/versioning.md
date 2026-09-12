# 版本与分支管理

## 命名

- 版本分支使用 `version/tc-vX.Y.Z`，例如 `version/tc-v0.0.3`。
- 发布标签使用 `tc-plane-vX.Y.Z`，与部署变量 `APP_VERSION` 保持一致。

## 创建版本分支

1. 确认 `main` 是本次版本的基线且工作区干净。
2. 从 `main` 创建版本分支：`git switch -c version/tc-vX.Y.Z main`。
3. 立即推送并设置上游：`git push --set-upstream origin version/tc-vX.Y.Z`。
4. 在根 `package.json` 更新版本号，并更新社区部署中 `APP_VERSION` 的默认值。
5. 在路线图登记本次计划但尚未完成的定制功能。

## 版本内维护

- 功能开始、范围变化或目标发布调整时更新路线图。
- 功能完成时，将条目从路线图移入功能归档，记录发布版本和完成日期。
- 应用、共享包或部署边界变化时更新系统概览。

## 发布与合并

1. 完成目标版本的检查，并核对版本元数据、路线图和功能归档。
2. 切换至 `main` 并合并版本分支：`git merge --ff-only version/tc-vX.Y.Z`。
3. 创建发布标签：`git tag tc-plane-vX.Y.Z`。
4. 推送 `main`、版本分支和标签至 `origin`。

界面中的产品版本（代码/API 中为 `Module`）及其示例不属于发布元数据，不因创建发布分支而调整。
