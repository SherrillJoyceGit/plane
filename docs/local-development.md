# 本机 Development 调试

本文记录当前 macOS 开发机的固定运行拓扑和调试流程。后续应用代码更新默认复用现有服务，不清理基础设施或数据。

## 运行拓扑

| 服务       | 管理方式                                | 地址或端口                                  |
| ---------- | --------------------------------------- | ------------------------------------------- |
| Web        | `launchd`: `com.tc-plane.web`           | `http://10.1.109.63:3000`                   |
| Admin      | `launchd`: `com.tc-plane.admin`         | `http://10.1.109.63:3001/god-mode/`         |
| API        | Docker Compose: `api`                   | `http://10.1.109.63:8000`                   |
| PostgreSQL | Docker Compose: `plane-db`              | `127.0.0.1:15432`                           |
| Redis      | Docker Compose: `plane-redis`           | `127.0.0.1:16379`                           |
| RabbitMQ   | Docker Compose: `plane-mq`              | 容器网络                                    |
| MinIO      | Docker Compose: `plane-minio`           | `10.1.109.63:9000`；控制台 `127.0.0.1:9090` |
| Celery     | Docker Compose: `worker`、`beat-worker` | 容器网络                                    |

Compose 命令统一使用：

```bash
docker compose -f docker-compose-local.yml -f docker-compose-tc-local.yml
```

外置数据默认位于 `/Volumes/MacExt/docker-data/tc-plane-test`。不要执行 `down -v`，应用调试也不需要执行 `down`。

## 首次启动

首次初始化环境文件并构建 Docker 应用：

```bash
./setup.sh
docker compose -f docker-compose-local.yml -f docker-compose-tc-local.yml up --build -d
```

Web 和 Admin 必须交给 `launchd` 托管，不要另开终端运行重复的 dev server。先检查服务是否已经存在：

```bash
launchctl print gui/$(id -u)/com.tc-plane.web
launchctl print gui/$(id -u)/com.tc-plane.admin
```

服务不存在时，在仓库根目录提交给 `launchd`：

```bash
launchctl submit -l com.tc-plane.web -o /tmp/tc-plane-web.log -e /tmp/tc-plane-web.err -- \
  /usr/bin/env "PATH=$PATH" pnpm --dir="$PWD" turbo run dev --filter=web -- --host 10.1.109.63

launchctl submit -l com.tc-plane.admin -o /tmp/tc-plane-admin.log -e /tmp/tc-plane-admin.err -- \
  /usr/bin/env "PATH=$PATH" pnpm --dir="$PWD" turbo run dev --filter=admin -- --host 10.1.109.63
```

`launchctl submit` 创建的是当前登录会话内的用户服务。注销或重启 macOS 后服务不存在时，重新提交即可。

## 日常代码更新

更新前先保存容器基线：

```bash
docker compose -f docker-compose-local.yml -f docker-compose-tc-local.yml ps
```

`apps/api` 已 bind mount 到容器。只修改 Django 请求链路时，仅重启 API：

```bash
docker compose -f docker-compose-local.yml -f docker-compose-tc-local.yml restart api
```

修改 Celery 任务时，再重启对应进程：

```bash
docker compose -f docker-compose-local.yml -f docker-compose-tc-local.yml restart worker beat-worker
```

只有依赖文件或 Dockerfile 变化时才重新构建应用容器，并用 `--no-deps` 避免操作基础设施：

```bash
docker compose -f docker-compose-local.yml -f docker-compose-tc-local.yml up -d --build --no-deps api worker beat-worker
```

前端 dev server 虽支持热更新，覆盖更新或怀疑缓存时应通过原服务重载：

```bash
launchctl kickstart -k gui/$(id -u)/com.tc-plane.web
launchctl kickstart -k gui/$(id -u)/com.tc-plane.admin
```

## 验收与排错

重载后检查进程、日志和 HTTP 响应：

```bash
launchctl print gui/$(id -u)/com.tc-plane.web
launchctl print gui/$(id -u)/com.tc-plane.admin
tail -n 80 /tmp/tc-plane-web.err
tail -n 80 /tmp/tc-plane-admin.err

curl -sS --max-time 10 -o /dev/null -w 'web %{http_code}\n' http://10.1.109.63:3000/sign-up
curl -sS --max-time 10 -o /dev/null -w 'admin %{http_code}\n' http://10.1.109.63:3001/god-mode/
curl -sS --max-time 10 -o /dev/null -w 'api %{http_code}\n' http://10.1.109.63:8000/api/instances/

docker compose -f docker-compose-local.yml -f docker-compose-tc-local.yml logs --tail=80 api
docker compose -f docker-compose-local.yml -f docker-compose-tc-local.yml ps
```

预期 Web 和 API 返回 `200`；Admin 可返回 `200` 或正常登录重定向。对比更新前后的容器 ID 和运行时间，PostgreSQL、Redis、RabbitMQ、MinIO 不应发生变化。

实例配置默认启用 `SKIP_ENV_VAR=1`，数据库中的 `InstanceConfiguration` 优先于 `.env`。认证方式、workspace 创建限制等已有配置应在 [Admin Authentication](http://10.1.109.63:3001/god-mode/authentication) 和 [Admin Workspace](http://10.1.109.63:3001/god-mode/workspace) 中检查或修改。

## 单 Workspace 注册验证

1. 在 [Admin Workspace](http://10.1.109.63:3001/god-mode/workspace) 创建或确认目标 workspace，并开启 “Prevent anyone else from creating a workspace”。
2. 在 [Admin Authentication](http://10.1.109.63:3001/god-mode/authentication) 仅开启邮箱密码注册，关闭 Magic Link 和 OAuth。
3. 使用无痕窗口和新邮箱访问 [注册页](http://10.1.109.63:3000/sign-up)。
4. 未配置 `DEFAULT_WORKSPACE_SLUG` 且只有一个 workspace 时，应显示主动加入复选框；存在多个 workspace 时不显示，也不隐式选择。
5. 配置有效的 `DEFAULT_WORKSPACE_SLUG` 后，复选框应隐藏，新账号应以 Member 身份自动加入目标 workspace。
6. 普通用户不应看到创建入口；直接访问 [创建 Workspace](http://10.1.109.63:3000/create-workspace) 应提示创建已禁用，创建 API 应返回 `403`。
7. 邀请注册应保留邀请角色，不被默认 Member 角色覆盖。
8. 零 workspace 场景只在隔离空数据库验证，不通过删除当前实例数据来模拟。
