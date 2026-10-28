# Nstdata Proxy Manager 部署

[English](README.md)

通过 Docker Compose 配置 Nstdata Router、Gateway 和 Redis。Router 从 Nstdata 控制面获取配置；本仓库提供部署材料，不包含 Router／Gateway 源码。

## 前置条件

- Docker Engine 及支持内联 `configs.content` 的 Docker Compose。
- 获准使用的 `CONFIG_API_TOKEN` 和对应 Router／Gateway 镜像访问权限。
- 已与服务维护者确认镜像版本及流量、上报行为。模板使用 `latest`；生产部署前须将所有镜像替换为审核过的版本或 digest。

## 配置

使用仓库中的 [compose.yaml](compose.yaml)，通过受保护的本地环境设置 `CONFIG_API_TOKEN`。生成一次 `REDIS_PASSWORD`，并保存供后续启动使用：

```bash
export REDIS_PASSWORD="$(openssl rand -hex 32)"
```

Redis URL 要求密码为64位十六进制字符。Redis 不发布宿主机端口，Router 通过 Compose 网络访问它。

```yaml
services:
  redis:
    image: redis:latest
    container_name: proxy-manager-redis
    restart: always
    command: ["redis-server", "--requirepass", "${REDIS_PASSWORD:?Set REDIS_PASSWORD}"]

  proxy-manager-router:
    image: nstdata/proxy-manager-router:latest
    container_name: proxy-manager-router
    environment:
      - CONFIG_API_TOKEN=${CONFIG_API_TOKEN:?Set CONFIG_API_TOKEN}
      - REPORT_SINK=redis
      - REPORT_REDIS_KEY=proxyManager
      - REDIS_URL=redis://:${REDIS_PASSWORD:?Set REDIS_PASSWORD}@redis:6379/0
    depends_on:
      - redis
    restart: always

  proxy-manager-gateway:
    image: nstdata/proxy-manager-gateway:latest
    container_name: proxy-manager-gateway
    ports:
      - "24125:24125"
    configs:
      - source: gateway_config
        target: /app/config.yaml
    depends_on:
      - proxy-manager-router
    restart: always

configs:
  gateway_config:
    content: |
      server:
        bind: "0.0.0.0:24125"
      logs:
        level: "info"
        format: "compact"
        file_enabled: false
        console_enabled: true
      backend:
        version: "grpc_v2"
        address: "grpc://proxy-manager-router:3050"
```

## 校验与启动

以下命令会启动容器；须先选定获准使用的镜像，并配置 Token 和密码：

```bash
case "${REDIS_PASSWORD:-}" in
  ''|*[!0-9a-fA-F]*) printf '%s\n' 'REDIS_PASSWORD must be 64 hexadecimal characters' >&2; exit 1 ;;
esac
[ "${#REDIS_PASSWORD}" -eq 64 ] || {
  printf '%s\n' 'REDIS_PASSWORD must be 64 hexadecimal characters' >&2
  exit 1
}

docker compose config --quiet
docker compose up -d
```

Gateway 将 `24125` 端口发布到宿主机全部网络接口，须按部署环境配置访问控制。Router 会连接控制面，不能据此模板认定全部流量或遥测仅留在本地。

## 运行维护

- Token 和 Redis 密码不得提交到版本控制；重启时使用原密码。
- 模板将报告写入自身 Redis。可用上报方式、字段和保留策略取决于镜像版本，处理敏感流量前须取得对应契约。
- 升级前备份所需 Redis 数据和配置，记录原镜像 digest；回退时恢复匹配的镜像和配置。
- `docker compose down` 会停止并删除容器。本模板未显式配置 Redis 持久化卷，不保证更换容器后保留报告；需要保留时，应配置并验证持久化方案。

## 本地配置检查

安装 Python 3 和 Docker Compose 后执行：

```sh
python3 -B -m unittest discover -s tests -v
```

检查使用合成凭据解析 Compose 并验证密码规则，不拉取镜像、不启动服务。配置检查通过不证明镜像可用、服务就绪或代理路由正确。

镜像访问及部署问题通过 [GitHub Issues](https://github.com/nstdata-ai/proxy-manager/issues)联系维护者，不提交 Token 或流量记录。
