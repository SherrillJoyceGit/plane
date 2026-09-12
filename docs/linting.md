# 前端 Lint

前端工作区统一使用 OxLint，规则由根目录的 `.oxlintrc.json` 管理。Lint 不依赖 TypeScript 构建产物。

## 命令

在仓库根目录运行：

```bash
pnpm check:lint
pnpm fix:lint
```

只检查指定包或应用：

```bash
pnpm turbo run check:lint --filter=@plane/ui
```

## 范围与规则

- 检查 `apps/web`、`apps/admin`、`apps/space`、`apps/live` 和 `packages/*` 中的 TypeScript 与 JavaScript 文件。
- 忽略依赖、构建产物、缓存、覆盖率、公共资源和配置文件。
- 启用 React、TypeScript、JSX accessibility、import、promise、unicorn 和 oxc 相关规则。

| 分类          | 级别  | 作用                   |
| ------------- | ----- | ---------------------- |
| `correctness` | error | 检查可能导致错误的代码 |
| `suspicious`  | warn  | 检查可疑写法           |
| `perf`        | warn  | 检查性能问题           |

`react/prop-types` 已关闭；未使用变量默认警告，以 `_` 开头的变量除外。具体规则以 `.oxlintrc.json` 为准。

## 警告抑制

OxLint 兼容现有的 `eslint-disable` 注释。仅在确认警告不适用时使用：

```typescript
// eslint-disable-next-line no-unused-vars
const data = response;
```

## 提交检查

Husky 会对暂存文件运行 lint-staged：oxfmt 负责格式化，OxLint 自动修复可修复的问题并拒绝残留警告。提交失败时，应修复问题后重新提交。

相关配置：

- [.oxlintrc.json](../.oxlintrc.json)
- [package.json](../package.json)
