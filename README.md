# ProxyManager

[![](https://img.shields.io/docker/v/nstdata/proxy-manager-gateway?logo=docker&label=gateway)](https://hub.docker.com/r/nstdata/proxy-manager-gateway)
[![](https://img.shields.io/docker/v/nstdata/proxy-manager-router?logo=docker&label=gateway)](https://hub.docker.com/r/nstdata/proxy-manager-router)

[中文版](README_zh.md)

ProxyManager is a high-performance, visually-managed proxy and routing management system designed for developers. It seamlessly integrates a powerful underlying proxy gateway (Gateway) with a dynamic routing engine (Router).

To meet the needs of different business scenarios, we provide **two product forms**:

1. ☁️ **Pure Cloud-Hosted Version (Pay-As-You-Go)**: **Out of the box with no deployment required.** Traffic is fully and intelligently scheduled by the cloud, suitable for developers who want quick integration and zero O&M costs. For more details, please visit [nstproxy.com](http://nstproxy.com).
2. 🔒 **Private Node Deployment Version (Contents of this Repository)**: Suitable for enterprises that are extremely sensitive to data privacy, or wish to leverage their own servers' bandwidth and environment. The control plane is managed in the cloud, while the data plane flows entirely locally.

> **⚠️ Note**: The following documentation in this repository is exclusively for the **Private Node Deployment Version**. Before running this system, you must first obtain an `API-TOKEN` issued by the official team.

---

## 🏗️ Architecture and Privacy Protection (Private Node Version)

If you choose to deploy a private node, the system will adopt a secure architecture of **"Cloud Control Plane + Fully Private Data Plane"**:

1. **Cloud Console (Configuration Management Only)**: You can centrally configure proxy rules, routing distribution, TLS fingerprint spoofing, etc., through our user-friendly Web interface. The cloud system is only responsible for delivering configuration files to your nodes.
2. **Local Node Operation (Absolute Traffic Isolation)**: You deploy the Router & Gateway nodes on your own servers. The Router periodically synchronizes the latest policy configurations from the backend via API and instructs the Gateway to process actual traffic. **All business proxy traffic flows entirely within your local environment and will never pass through our cloud services!**

---

## 🌟 Core Capabilities

1. **Unified Access for Complex Protocols**: Automatically identifies and processes HTTP, SOCKS5, and HAProxy traffic on a **single listening port**.
2. **Anti-Scraping and Fingerprint Spoofing**: Automatically simulates real browser TLS/HTTP fingerprints, supporting blocking or caching in HTTPS Man-In-The-Middle (MITM) scenarios.
3. **Intelligent Routing Decisions**: Dynamically determines the flow of traffic (e.g., direct connection, headless browser, proxy pool) based on dimensions such as domain name, user identity, and task type.
4. **Full-Link Observability**: Based on the Router's powerful real-time traffic reporting, achieves 100% mastery of the status of every connection and request.

---

## 📦 Private Node Deployment Guide

Provides an out-of-the-box Docker Compose setup for rapid deployment.

### 1. Prerequisites (Obtaining Authorization)
**Before running, you must first obtain an `API-TOKEN`.**
Please visit our [official website (nstproxy.com)](http://nstproxy.com) or contact us via Issue to purchase and obtain your exclusive authorization key.

### 2. Environmental Dependencies
- Recommended OS: Linux x86_64
- Dependencies: Docker & Docker Compose

### 3. Docker Compose Configuration

Create a `compose.yaml` file, and fill in your `<API-TOKEN>` in the corresponding location:

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
      - CONFIG_API_URL=https://pm-api.nstdata.ai/api/router/snapshot
      - CONFIG_API_TOKEN=<REPLACE_WITH_YOUR_API_TOKEN>
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
      - nstdata-proxy-manager-router
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

### 4. Startup and Management
Execute the following command to start the services:
```bash
docker compose up -d
```
Once successfully started, the node will automatically connect to the cloud API and pull the configuration. You can log in to the **[Cloud Visual Console](http://nstproxy.com)** to manage your nodes and rules.

---

## 📊 Advanced Features: Event Reporting Mechanism (Fully Privately Managed)

To achieve 100% mastery of the lifecycle of every proxy request, ProxyManager features a built-in powerful event reporting engine.

> **🔒 Data Security Commitment**: The official team **absolutely does not collect** any of your reported data or logs! All audit records, connection statistics, and traffic events are handled by the `REPORT_SINK` you configure yourself, and the data flows and is stored entirely within your local intranet.

**Supported Reporting Channels (Configured by modifying environment variables in docker-compose):**
- `none` / `off`: Disable reporting.
- `stdout`: Write to standard logs.
- `webhook`: POST to a specified URL (Configure `REPORT_WEBHOOK_URL` and `REPORT_WEBHOOK_TOKEN`).
- `redis`: Batch RPUSH into your local Redis (Configure `REDIS_URL` and `REPORT_REDIS_KEY`).
- `kafka`: Write to your private Kafka cluster (Configure `REPORT_KAFKA_BROKERS` and `REPORT_KAFKA_TOPIC`).

*Tip: Webhook, Redis, and Kafka have batch processing enabled by default. This can be adjusted via `REPORT_BATCH_SIZE` (default 128) and `REPORT_BATCH_TIMEOUT` (default 100ms).*

**Reporting Structure Example:**
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

## 📞 Contact Us

If you encounter any issues during deployment and usage, or if you need to learn more about the **Pure Cloud-Hosted Version** and purchasing a **Commercial Authorization for the Private Version**, please contact us through the following channels:
- Official Website: [nstproxy.com](http://nstproxy.com)
- Submit a [GitHub Issue](https://github.com/nstdata-ai/proxy-manager/issues)
