# Agent 开发指南

## 语言与语境

- 默认使用中文进行沟通、分析、说明和文档编写。
- 代码标识符、命令、路径、API 名称和专有技术术语保持原文；必要时补充简洁的中文解释。
- 除非用户明确要求使用其他语言，否则所有面向用户的输出均使用中文。

## 常用命令

- `pnpm dev`：启动所有开发服务器（web:3000、admin:3001）
- `pnpm build`：构建所有包和应用
- `pnpm check`：运行全部检查（格式、lint、类型）
- `pnpm check:lint`：对所有包运行 OxLint
- `pnpm check:types`：运行 TypeScript 类型检查
- `pnpm fix`：自动修复格式和 lint 问题
- `pnpm turbo run <command> --filter=<package>`：针对指定包或应用运行命令
- `pnpm --filter=@plane/ui storybook`：在 6006 端口启动 Storybook

## 代码规范

- **依赖导入**：内部包使用 `workspace:*`，外部依赖使用 `catalog:`
- **TypeScript**：启用严格模式，所有文件必须具有完整类型
- **格式化**：使用 oxfmt，并运行 `pnpm fix:format`
- **Lint**：使用共享 `.oxlintrc.json` 配置运行 OxLint
- **命名**：变量和函数使用 camelCase，组件和类型使用 PascalCase
- **错误处理**：使用 try-catch 和正确的错误类型，并妥善记录错误
- **状态管理**：在 `packages/shared-state` 中使用 MobX store 和响应式模式
- **测试**：所有功能都必须有单元测试，并使用对应包现有的测试框架
- **组件**：在 `@plane/ui` 中构建组件，并使用 Storybook 进行隔离开发

## 后端测试（Docker）

`apps/api` 的 Django/pytest 测试套件在仓库根目录 `docker-compose-test.yml` 定义的隔离环境中运行。

首次运行前执行 `./setup.sh`，它会根据 `.env.example` 生成 `apps/api/.env`。

- 完整测试：`docker compose -f docker-compose-test.yml up --build --abort-on-container-exit --exit-code-from api-tests`
- 运行子集：`docker compose -f docker-compose-test.yml run --rm api-tests pytest -m unit`
- 清理环境：`docker compose -f docker-compose-test.yml down -v`

完整操作流程和故障排查请参阅 `apps/api/tests/RUNNING_TESTS.md`；测试约定和 fixture 说明请参阅 `apps/api/tests/TESTING_GUIDE.md`。
