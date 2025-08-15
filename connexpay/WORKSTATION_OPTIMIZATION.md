# ConnexPay AI Workstation Optimization Guide

This guide provides step-by-step instructions to optimize your Windows workstation for running the ConnexPay AI development environment with maximum performance and GPU acceleration.

## System Requirements

### Minimum Specifications

- **OS**: Windows 10/11 with WSL2 enabled
- **RAM**: 16GB (32GB+ recommended)
- **CPU**: 6+ cores recommended
- **GPU**: NVIDIA GPU with 4GB+ VRAM (optional but recommended)
- **Storage**: 50GB+ available space for Docker images and models

### Tested Configuration

This guide was tested and optimized on:

- **CPU**: Intel i7-10750H (6 cores, 12 threads)
- **RAM**: 32GB
- **GPU**: NVIDIA GeForce GTX 1650 Ti (4GB VRAM)
- **OS**: Windows 11 with WSL2

## Step 1: Configure WSL2 Resource Allocation

WSL2 needs adequate resources to run the AI stack efficiently. Configure resource limits to prevent system bottlenecks.

### Create .wslconfig File

1. **Create** or edit `C:\Users\[YourUsername]\.wslconfig`
2. **Add the following configuration**:

```ini
[wsl2]
memory=26GB
processors=10
swap=6GB
localhostForwarding=true
vmIdleTimeout=-1
nestedVirtualization=true
```

### Resource Allocation Guidelines

Adjust values based on your system specifications:

| System RAM | WSL Memory | System CPU Cores     | WSL Processors |
| ---------- | ---------- | -------------------- | -------------- |
| 16GB       | 12GB       | 4 cores              | 3              |
| 32GB       | 26GB       | 6 cores (12 threads) | 10             |
| 64GB       | 48GB       | 8+ cores             | 14+            |

### Apply Configuration

1. **Shutdown WSL completely**:

   ```powershell
   wsl --shutdown
   ```

2. **Wait 10 seconds**, then restart WSL:

   ```powershell
   wsl
   ```

3. **Verify new resources**:
   ```bash
   free -h    # Should show allocated memory
   nproc      # Should show allocated processors
   ```

## Step 2: Enable Docker Desktop GPU Integration

### Install/Update NVIDIA Drivers

1. **Check current driver version**:

   ```bash
   nvidia-smi
   ```

2. **Update to latest drivers**:

   - Go to [NVIDIA Driver Downloads](https://www.nvidia.com/drivers)
   - Select your GPU model (e.g., GeForce GTX 1650 Ti)
   - Download and install **Game Ready Driver** (recommended for AI workloads)
   - **Restart your computer**

3. **Verify driver update**:
   ```bash
   nvidia-smi
   ```
   Should show **Driver Version 580+** and **CUDA 13.0+**

### Configure Docker Desktop

1. **Open Docker Desktop Settings**
2. **Navigate to**: Settings → Beta features
3. **Enable these options**:
   - ✅ Enable Docker AI
   - ✅ Enable Docker Model Runner
   - ✅ **Enable GPU-backed inference**
4. **Apply & Restart Docker Desktop**

### Test GPU Integration

```bash
# Test Docker GPU access
docker run --rm --gpus all nvidia/cuda:13.0.0-cudnn-runtime-ubuntu22.04 nvidia-smi
```

**Expected output**: Should show your GPU information without errors.

## Step 3: Optimize Docker Compose for GPU

### Add GPU Configuration to Override File

Edit your `docker-compose.override.yml` to enable GPU acceleration:

```yaml
services:
  # Enable GPU for Ollama (local LLM inference)
  ollama-gpu:
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]
    environment:
      - NVIDIA_VISIBLE_DEVICES=all
      - NVIDIA_DRIVER_CAPABILITIES=compute,utility

  # Enable GPU for Open WebUI (UI optimizations)
  open-webui:
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]
    environment:
      - NVIDIA_VISIBLE_DEVICES=all

  # Optional: Enable GPU for Langfuse (LLM processing)
  langfuse-worker:
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]
    environment:
      - NVIDIA_VISIBLE_DEVICES=all

  langfuse-web:
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]
    environment:
      - NVIDIA_VISIBLE_DEVICES=all
```

## Step 4: Configure Azure OpenAI Integration

### Setup Azure OpenAI Resource

1. **Create Azure OpenAI resource** in your corporate Azure portal
2. **Deploy your desired model** (e.g., GPT-4)
3. **Note the exact deployment name** (this will be used as Model ID)
4. **Copy endpoint URL and API key**

### Configure Open WebUI Connection

1. **Access Open WebUI**: http://localhost:8080
2. **Go to Admin Panel** → Settings → Connections
3. **Add new connection**:
   - **URL**: `https://your-resource-name.openai.azure.com/`
   - **API Key**: Your Azure API key
   - **Model IDs**: Your exact deployment name (e.g., `cxp-playground-gpt-4.1`)

**Important**: Use the **exact deployment name** from Azure, not a display name with spaces.

### Test Azure Connection

1. **Select your Azure model** from the dropdown
2. **Send test message**: "Hello there"
3. **Verify successful response**

## Step 5: Quick Start Scripts

### Minimal Open WebUI Stack

Use the optimized startup script for development work:

```bash
# Start minimal Open WebUI stack with GPU acceleration
python3 cxp_start_openwebui_services.py

# Include optional services
python3 cxp_start_openwebui_services.py --include searxng langfuse

# Stop services only
python3 cxp_start_openwebui_services.py --stop-only

# Check service status
python3 cxp_start_openwebui_services.py --status
```

### Full AI Stack

For complete development environment:

```bash
# Start complete AI stack (includes Supabase)
python3 cxp_start_service.py --profile gpu-nvidia
```

## Monitoring and Troubleshooting

### Monitor GPU Usage

```bash
# Real-time GPU monitoring
watch -n 1 nvidia-smi

# Check Docker container resource usage
docker stats
```

### Monitor Docker Logs

```bash
# Follow Open WebUI logs
docker logs -f open-webui

# Check specific service logs
docker-compose -p localai logs -f [service-name]
```

### Common Issues and Solutions

#### High Resource Usage

- **Symptoms**: Slow performance, high CPU/memory usage
- **Solution**: Reduce number of running services or increase WSL allocation

#### GPU Not Detected

- **Symptoms**: Models running slowly, nvidia-smi shows low usage
- **Solution**: Verify Docker Desktop GPU settings, restart Docker

#### Azure OpenAI Connection Errors

- **Symptoms**: "DeploymentNotFound" or "Resource not found" errors
- **Solution**: Check model ID matches exact Azure deployment name

#### DNS Resolution Failures

- **Symptoms**: "Temporary failure in name resolution"
- **Solution**: Increase WSL resources, restart Docker Desktop

## Performance Optimization Tips

### GPU Optimization

- **Model Loading**: Keep frequently used models loaded in GPU memory
- **Batch Processing**: Use appropriate batch sizes for your GPU VRAM
- **Temperature Monitoring**: Normal operating range is 60-80°C

### Memory Optimization

- **WSL Allocation**: Reserve 75-80% of system RAM for WSL
- **Docker Limits**: Monitor container memory usage with `docker stats`
- **Model Selection**: Choose appropriate model sizes for available VRAM

### Network Optimization

- **Corporate VPN**: Ensure certificate injection is working for SSL
- **Endpoint Configuration**: Use exact deployment names for Azure models
- **Connection Pooling**: Keep connections alive for better performance

## Service Access URLs

After optimization, your services will be available at:

| Service    | URL                    | Purpose             |
| ---------- | ---------------------- | ------------------- |
| Open WebUI | http://localhost:8080  | Main AI interface   |
| Ollama API | http://localhost:11434 | Local LLM API       |
| Qdrant     | http://localhost:6333  | Vector database     |
| Langfuse   | http://localhost:3000  | LLM observability   |
| SearXNG    | http://localhost:8081  | Search engine       |
| Flowise    | http://localhost:3001  | Workflow automation |

## Verification Checklist

Before considering your workstation fully optimized, verify:

- [ ] WSL2 has adequate memory allocation (`free -h` shows 20GB+)
- [ ] GPU drivers updated (CUDA 13.0+, Driver 580+)
- [ ] Docker Desktop GPU integration enabled
- [ ] GPU test container runs successfully
- [ ] Local models use GPU acceleration (nvidia-smi shows activity)
- [ ] Azure OpenAI connection works without errors
- [ ] All corporate certificates properly injected
- [ ] Essential services start and run stably

## Support and Troubleshooting

For additional support:

1. **Check logs**: Use provided monitoring commands
2. **Verify configuration**: Ensure all settings match your system specs
3. **Test incrementally**: Start with minimal services, add complexity gradually
4. **Monitor resources**: Use `docker stats` and `nvidia-smi` regularly

---

**Note**: This optimization guide is tailored for ConnexPay's corporate network environment with SSL certificate injection and VPN requirements. Adjust configurations as needed for your specific network policies.
