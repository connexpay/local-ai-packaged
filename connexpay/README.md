# ConnexPay Corporate Local AI Environment

This directory contains the corporate-specific configurations needed to run the **Self-hosted AI Package** within ConnexPay's corporate network and VPN environment.

## What's Different from the Base Project

The base [local-ai-packaged](https://github.com/coleam00/local-ai-packaged) project doesn't work out-of-the-box in corporate environments due to:

- **SSL certificate verification failures** (Zscaler proxy)
- **Port conflicts** with corporate security tools (9000-9999 range blocked)
- **Privileged port restrictions** (80, 443 blocked)

This ConnexPay directory provides the necessary overrides to solve these issues.

## What's in This Directory

This `connexpay/` directory contains all the corporate-specific configurations needed to run the Local AI stack within ConnexPay's network:

- **ZscalerRootCertificate.crt** - Corporate SSL certificate
- **docker-compose.override.\*.yml** - Port and configuration overrides
- **services/** - Custom Dockerfiles with certificate injection (one per service)
- **searxng/** - SearXNG configuration with corporate settings

## Corporate Network Adaptations

### 1. **SSL Certificate Injection**

Every service Dockerfile includes:

```dockerfile
# Copy corporate certificate
COPY ZscalerRootCertificate.crt /usr/local/share/ca-certificates/
# Update system certificate store
RUN update-ca-certificates
# Set Python SSL environment variables
ENV REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt
ENV SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt
```

### 2. **Corporate-Safe Port Mappings**

- **Standard ports** → **Corporate-safe ports**
- Port 80 → 18080 (Caddy HTTP)
- Port 443 → 18443 (Caddy HTTPS)
- 9000-9999 range → 19000-19999 range (避开 Zscaler)

### 3. **Environment Variable Fixes**

Services that reference internal ports have updated environment variables:

```yaml
CLICKHOUSE_MIGRATION_URL: clickhouse://clickhouse:9000 # Internal port
LANGFUSE_S3_BATCH_EXPORT_ENDPOINT: http://minio:9000 # Internal port
```

## Quick Start

### Prerequisites

- Python 3.x installed (`python3 --version`)
- Docker Desktop running
- Corporate VPN connected
- WSL2 (if on Windows)

### Installation Steps

1. **Clone the repository** (if not already done):

   ```bash
   git clone https://github.com/connexpay/local-ai-packaged.git
   cd local-ai-packaged
   ```

2. **Set up environment variables** by copying `.env.example` to `.env` and filling in required values (see main README)

3. **Start the corporate environment**:

   ```bash
   python3 cxp_start_services.py --profile gpu-nvidia
   ```

4. **Access your services** on corporate-safe ports:
   - **N8N**: http://localhost:5678
   - **Open WebUI**: http://localhost:8080
   - **SearXNG**: http://localhost:8081
   - **Caddy (reverse proxy)**: http://localhost:18080
   - **Flowise**: http://localhost:3001
   - **Langfuse**: http://localhost:3000

## Available Profiles

Choose the profile that matches your hardware:

```bash
# For NVIDIA GPU (recommended for corporate laptops)
python3 cxp_start_services.py --profile gpu-nvidia

# For CPU only (if no GPU available)
python3 cxp_start_services.py --profile cpu

# For AMD GPU (Linux only)
python3 cxp_start_services.py --profile gpu-amd
```

## Differences from Standard Setup

### **Corporate Startup Script**

- **File**: `cxp_start_services.py` (in project root)
- **Skips**: Private/public environment overrides that conflict with corporate ports
- **Includes**: Certificate injection verification and SearXNG secret key generation

### **Docker Compose Override Strategy**

The corporate setup uses a **clean override approach**:

- Base `docker-compose.yml` defines services
- Corporate overrides **completely replace** conflicting configurations
- **No array merging issues** with ports

### **Disabled Services**

- **Supabase Edge Functions**: Disabled due to Deno SSL complexity (not needed for local AI development)

## Troubleshooting

### Common Issues

**Port Conflicts**: If you see port binding errors, check if corporate tools are using those ports:

```powershell
# From Windows PowerShell
netstat -ano | findstr :9000
```

**SSL Certificate Errors**: If services can't connect to external APIs:

1. Verify certificate is present: `ls -la connexpay/ZscalerRootCertificate.crt`
2. Check service logs: `docker logs <service-name>`
3. Rebuild with certificate injection: `docker compose ... up -d --build --force-recreate <service-name>`

**Permission Issues with SearXNG**:

```bash
chmod 664 searxng/settings.yml
chmod 664 connexpay/searxng/settings.yml
```

### Stopping Services

```bash
# Stop all services
docker compose -p localai down --remove-orphans

# Or use the corporate stop command
docker compose -p localai --profile gpu-nvidia -f docker-compose.yml -f connexpay/docker-compose.override.ai.local.cxp.yml down
```

### Checking Service Health

```bash
# View all running services
docker ps

# Check specific service logs
docker logs <container-name>

# Monitor resource usage
docker stats --no-stream
```

## Resource Optimization

The corporate environment includes resource optimizations for heavy services:

- **Supabase Analytics**: Memory usage reduced from 6GB to ~1GB
- **Clickhouse**: CPU usage reduced from 85% to ~4%, memory capped at 2GB

## Corporate Network Notes

- **Zscaler**: Blocks ports 9000-9999, handled by remapping to 19000-19999
- **WSL2**: Works perfectly with corporate network via Docker Desktop
- **VPN**: All services work through corporate VPN with certificate injection
- **Certificate Management**: Zscaler root certificate automatically injected into all containers

## Support

For corporate-specific issues:

1. Check the main project [troubleshooting section](../README.md#troubleshooting)
2. Verify your `.env` file has all required values
3. Ensure Docker Desktop has sufficient resources allocated
4. Contact the team member who set up this configuration

## Security Notes

- **Internal Use Only**: This setup is designed for internal corporate development
- **Certificate Injection**: Required for corporate proxy connectivity
- **Port Remapping**: Ensures compatibility with corporate security tools
- **No External Exposure**: All services bind to localhost only (127.0.0.1)

---

**This corporate adaptation maintains all the functionality of the original project while ensuring compatibility with ConnexPay's corporate network infrastructure.**
