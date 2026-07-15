# ProxyManager

[![](https://img.shields.io/docker/v/nstdata/proxy-manager-gateway?logo=docker&label=gateway)](https://hub.docker.com/r/nstdata/proxy-manager-gateway)
[![](https://img.shields.io/docker/v/nstdata/proxy-manager-router?logo=docker&label=gateway)](https://hub.docker.com/r/nstdata/proxy-manager-router)

[English](README.md)

ProxyManager 是一款面向开发者的高性能、可视化的代理与路由管理系统。它将底层强大的代理网关（Gateway）与动态路由引擎（Router）完美整合。

为满足不同业务场景的需求，我们提供**两种产品形态**：

1. ☁️ **纯云端托管版（按量付费）**：**无需任何部署，开箱即用。** 流量完全由云端智能调度，适合希望快速集成、免除运维成本的开发者。详情请见 [nstproxy.com](http://nstproxy.com)。
2. 🔒 **私有节点部署版（本仓库内容）**：适合对数据隐私极度敏感、或希望利用自有服务器带宽及环境的企业。控制面在云端管理，数据面完全在本地流转。

> **⚠️ 注意**：本仓库以下文档专为**私有节点部署版**提供。运行本系统前，您需要先获取官方下发的 `API-TOKEN`。

---

## 🏗️ 架构与隐私保护 (私有节点版)

如果您选择部署私有节点，系统将采用 **“控制面云端化 + 数据面完全私有化”** 的安全架构：

1. **云端控制台（仅负责配置管理）**：您可以通过我们友好的 Web 界面集中配置代理规则、路由分发、TLS 指纹模拟等。云端系统仅负责将配置文件下发给您的节点。
2. **本地节点运行（流量绝对隔离）**：您在自己的服务器上部署 Router & Gateway 节点。Router 会定期通过 API 从后端同步最新的策略配置，并指挥 Gateway 处理实际流量。**所有的业务代理流量均在您的本地环境流转，完全不会经过我们的云端服务！**

---

## 🌟 核心能力

1. **复杂协议统一接入**：在**单一监听端口**上自动识别并处理 HTTP、SOCKS5 及 HAProxy 流量。
2. **反爬对抗与指纹模拟**：自动模拟真实浏览器 TLS/HTTP 指纹，支持 HTTPS 中间人（MITM）场景下的阻断或缓存。
3. **智能路由决策**：基于域名、用户身份、任务类型等维度，动态决定流量走向（如直连、无头浏览器、代理池）。
4. **全链路可观测性**：基于 Router 强大的实时流量上报，实现对每个连接和请求状态的 100% 掌握。

---

## 📦 私有节点部署教程

提供开箱即用的 Docker Compose 进行快速拉起。

### 1. 前置准备（获取授权）
**在运行之前，您必须先获取 `API-TOKEN`。**
请访问我们的[官方网站 (nstproxy.com)](http://nstproxy.com) 或通过 Issue 与我们联系，购买并获取您的专属授权密钥。

### 2. 环境依赖
- 推荐系统：Linux x86_64
- 依赖项：Docker & Docker Compose

### 3. Docker Compose 配置

创建一个 `compose.yaml` 文件，并将您的 `<API-TOKEN>` 填入对应位置：

```yaml
services:
  redis:
    image: redis:latest
    container_name: proxy-manager-redis
    ports:
      - "6379:6379"
    restart: always
    command: redis-server --requirepass "your_secure_password"

  proxy-manager-router:
    image: nstdata/proxy-manager-router:latest
    container_name: proxy-manager-router
    environment:
      - CONFIG_API_TOKEN=<此处替换为您的 API-TOKEN>
      - REPORT_SINK=redis
      - REPORT_REDIS_KEY=proxyManager
      - REDIS_URL=redis://:your_secure_password@redis:6379/0
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

### 4. 启动与管理
执行以下命令启动服务：
```bash
docker compose up -d
```
启动成功后，节点将自动连接云端 API 并拉取配置。您可登录 **[云端可视化控制台](http://nstproxy.com)** 管理您的节点和规则。

---

## 📊 高级特性：事件上报机制 (完全由您私有掌握)

为了实现对每一个代理请求生命周期的 100% 掌握，ProxyManager 内置了强大的事件上报引擎。

> **🔒 数据安全承诺**：官方**完全不收集**您的任何上报数据和日志！所有的审计记录、连接统计、流量事件，均交由您自己配置的 `REPORT_SINK` 处理，数据在您的本地内网中流转和存储。

**支持的上报通道（通过修改 docker-compose 中的环境变量实现）：**
- `none` / `off`：关闭上报。
- `stdout`：写入标准日志。
- `webhook`：POST 到指定 URL（配置 `REPORT_WEBHOOK_URL` 及 `REPORT_WEBHOOK_TOKEN`）。
- `redis`：批量 RPUSH 写入您的本地 Redis（配置 `REDIS_URL` 和 `REPORT_REDIS_KEY`）。
- `kafka`：写入您的私有 Kafka 集群（配置 `REPORT_KAFKA_BROKERS` 与 `REPORT_KAFKA_TOPIC`）。

*提示：webhook、redis 和 kafka 默认开启批处理。可通过 `REPORT_BATCH_SIZE` (默认 128) 和 `REPORT_BATCH_TIMEOUT` (默认 100ms) 调整。*

**上报结构示例：**
```json
[
  {
    "type": "stats",
    "trace_id": "tr-001",
    "gateway": "router-a",
    "time": 1710000005000,
    "payload": {
      "router": "r1",
      "connect_id": "tr-001",
      "owner_id": "user-001",
      "host": "example.com",
      "port": 443,
      "protocol": "tcp",
      "incoming_bytes": 2048,
      "outgoing_bytes": 4096,
      "status": "SUCCESS"
    }
  }
]
```

---

## 📞 联系我们

如在部署和使用中遇到问题，或需要了解**纯云端版本**及购买**私有版商业授权**，请通过以下方式联系：
- 官方网站：[nstproxy.com](http://nstproxy.com)
- 提交 [GitHub Issue](https://github.com/nstdata-ai/proxy-manager/issues)
