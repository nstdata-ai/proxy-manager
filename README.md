# Nstdata Proxy Manager deployment

[中文](README_zh.md)

Docker Compose configuration for running Nstdata Router, Gateway and Redis. Router obtains configuration from the Nstdata control plane; this repository contains deployment materials, not the Router/Gateway source.

## Prerequisites

- Docker Engine and Docker Compose supporting inline `configs.content`.
- An authorized `CONFIG_API_TOKEN` and access to the selected Router/Gateway images.
- Image versions and traffic/reporting behavior confirmed with the service maintainer. The template uses `latest`; replace every image with reviewed version tags or digests before production use.

## Configure

Use the checked-in [compose.yaml](compose.yaml). Set `CONFIG_API_TOKEN` through a protected local environment. Generate `REDIS_PASSWORD` once and retain it for restarts:

```bash
export REDIS_PASSWORD="$(openssl rand -hex 32)"
```

The password must be 64 hexadecimal characters for the Redis URL. Redis has no published host port; Router reaches it through the Compose network.

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

## Validate and start

The following commands start containers. Run them only after selecting authorized images and configuring the token and password:

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

Gateway publishes port `24125` on all host interfaces. Apply host/network access controls appropriate to the deployment. Router connects to the control plane; this template does not establish that all traffic or telemetry stays local.

## Operations

- Keep the token and Redis password outside version control; retain the same password across restarts.
- The template sends reports to its Redis instance. Supported reporting sinks, fields and retention depend on the selected image version; obtain that contract before handling sensitive traffic.
- Back up required Redis data and configuration before upgrading. Record previous image digests and restore them with the matching configuration when rolling back.
- `docker compose down` stops and removes containers. This template defines no persistent Redis volume and does not provide a report-retention guarantee across container replacement. Configure and verify persistence if reports must survive replacement.

## Local configuration checks

With Python 3 and Docker Compose installed:

```sh
python3 -B -m unittest discover -s tests -v
```

These checks render Compose with synthetic credentials and validate the password guard; they do not pull images or start services. A successful configuration check does not prove image availability, readiness or proxy routing.

For image access and deployment support, contact the maintainer through [GitHub Issues](https://github.com/nstdata-ai/proxy-manager/issues). Do not include tokens or traffic records.
