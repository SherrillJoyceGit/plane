# 系统概览

Plane 是由多个前端应用、Django 后端和共享 TypeScript 包组成的 monorepo。根目录使用 `pnpm` workspace 和 Turborepo 编排 JavaScript/TypeScript 工作区；`apps/api` 是独立的 Python/Django 服务。

## 应用边界

| 区域        | 路径         | 职责                                       |
| ----------- | ------------ | ------------------------------------------ |
| 主 Web 应用 | `apps/web`   | 面向终端用户的 Plane 工作区和项目体验      |
| 管理应用    | `apps/admin` | 实例管理和初始化相关界面                   |
| Space 应用  | `apps/space` | 公共 Space 体验                            |
| 实时应用    | `apps/live`  | 实时协作与事件相关能力                     |
| API 服务    | `apps/api`   | Django API、领域模型、后台任务和数据库迁移 |
| 代理        | `apps/proxy` | 面向部署环境的反向代理配置                 |

## 共享与部署

| 区域     | 路径                                                | 职责                                                     |
| -------- | --------------------------------------------------- | -------------------------------------------------------- |
| 共享包   | `packages/*`                                        | UI、类型、状态、服务、国际化、常量和通用工具等可复用能力 |
| 部署配置 | `deployments/*`                                     | AIO、CLI、Kubernetes 和 Swarm 的社区部署入口             |
| 根工作区 | `package.json`、`pnpm-workspace.yaml`、`turbo.json` | 依赖目录、脚本和任务编排                                 |

## 依赖原则

- 前端应用通过 `packages/*` 复用通用能力，避免跨应用直接复制实现。
- API 的领域模型、迁移和服务端接口归属 `apps/api`；前端通过服务层访问 API。
- 部署变量的默认值归属对应部署入口；发布版本由 `APP_VERSION` 统一传递给服务。
- 影响以上边界的改动应更新本文。
