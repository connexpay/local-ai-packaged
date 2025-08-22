#!/usr/bin/env python3
"""
start_openwebui_only.py

This script starts only Open WebUI and its essential dependencies using the same
corporate network overrides as the full stack. Uses the same Docker Compose project
name ("localai") for consistency.

Dependencies started:
- open-webui (main interface)
- ollama-gpu (local LLM inference) 
- ollama-pull-llama-gpu (model initialization)
- qdrant (vector database for RAG)
- postgres (data persistence)
- redis (caching/sessions)

Optional services can be added via --include flag.
"""

import os
import subprocess
import argparse
import sys
import time

def run_command(cmd, cwd=None):
    """Run a shell command and print it."""
    print("Running:", " ".join(cmd))
    subprocess.run(cmd, cwd=cwd, check=True)

def check_corporate_overrides():
    """Check that the required ConnexPay override files exist."""
    print("Checking for ConnexPay corporate override files...")
    
    required_files = [
        "connexpay/ZscalerRootCertificate.crt",
        "connexpay/docker-compose.override.ai.local.cxp.yml"
    ]
    
    missing_files = []
    for file_path in required_files:
        if not os.path.exists(file_path):
            missing_files.append(file_path)
        else:
            print(f"✓ Found: {file_path}")
    
    if missing_files:
        print("ERROR: Missing required ConnexPay files:")
        for file_path in missing_files:
            print(f"  - {file_path}")
        print("\nPlease ensure all corporate override files are in place before running.")
        sys.exit(1)
    
    print("All required ConnexPay corporate override files found.")

def stop_openwebui_services():
    """Stop only the Open WebUI related services."""
    print("Stopping existing Open WebUI services...")
    
    services_to_stop = [
        "open-webui",
        "ollama-gpu", 
        "ollama-pull-llama-gpu",
        "qdrant",
        "postgres", 
        "redis"
    ]
    
    cmd = ["docker", "compose", "-p", "localai"]
    cmd.extend(["-f", "docker-compose.yml"])
    cmd.extend(["-f", "connexpay/docker-compose.override.ai.local.cxp.yml"])
    cmd.extend(["stop"] + services_to_stop)
    
    try:
        run_command(cmd)
    except subprocess.CalledProcessError:
        print("Some services may not have been running - continuing...")

def start_openwebui_stack(profile="gpu-nvidia", include_services=None):
    """Start Open WebUI and essential dependencies."""
    print("Starting Open WebUI stack with corporate overrides...")
    
    # Essential services for Open WebUI
    essential_services = [
        "postgres",        # Data persistence
        "redis",          # Caching/sessions
        "qdrant",         # Vector database for RAG
        "ollama-gpu",     # Local LLM inference
        "open-webui"      # Main interface
    ]
    
    # Add model pulling service
    model_services = ["ollama-pull-llama-gpu"]
    
    # Optional services that can be included
    optional_services = []
    if include_services:
        available_optional = {
            "searxng": "searxng",
            "langfuse": ["langfuse-web", "langfuse-worker"],
            "clickhouse": "clickhouse",
            "minio": "minio",
            "flowise": "flowise",
            "n8n": "n8n",
            "pagadmin": "pgadmin"
        }
        
        for service in include_services:
            if service in available_optional:
                if isinstance(available_optional[service], list):
                    optional_services.extend(available_optional[service])
                else:
                    optional_services.append(available_optional[service])
            else:
                print(f"Warning: Unknown optional service '{service}' ignored")
    
    # Combine all services
    all_services = essential_services + optional_services
    
    # Build docker-compose command
    cmd = ["docker", "compose", "-p", "localai"]
    cmd.extend(["--profile", profile])
    cmd.extend(["-f", "docker-compose.yml"])
    cmd.extend(["-f", "connexpay/docker-compose.override.ai.local.cxp.yml"])
    cmd.extend(["up", "-d"] + all_services)
    
    print(f"Starting services: {', '.join(all_services)}")
    run_command(cmd)
    
    # Start model pulling after core services are up
    if model_services:
        print("Waiting for Ollama to be ready...")
        time.sleep(5)
        
        print("Starting model initialization...")
        model_cmd = ["docker", "compose", "-p", "localai"]
        model_cmd.extend(["--profile", profile])
        model_cmd.extend(["-f", "docker-compose.yml"])
        model_cmd.extend(["-f", "connexpay/docker-compose.override.ai.local.cxp.yml"])
        model_cmd.extend(["up", "-d"] + model_services)
        
        try:
            run_command(model_cmd)
        except subprocess.CalledProcessError:
            print("Model pulling may have failed - Open WebUI will still work")

def show_status():
    """Show status of Open WebUI related services."""
    print("\nChecking service status...")
    
    cmd = ["docker", "compose", "-p", "localai", "ps"]
    try:
        run_command(cmd)
    except subprocess.CalledProcessError:
        print("Could not check service status")

def show_access_info():
    """Show how to access the services."""
    print("\n" + "="*60)
    print("Open WebUI Access Information:")
    print("="*60)
    print("🌐 Open WebUI:     http://localhost:8080")
    print("🤖 Ollama API:     http://localhost:11434") 
    print("🔍 Qdrant:         http://localhost:6333")
    print("🗄️  Postgres:       localhost:5432")
    print("📦 Redis:          localhost:6379")
    print("\nTo test Azure OpenAI connection:")
    print("1. Go to http://localhost:8080")
    print("2. Select your Azure model: cxp-playground-gpt-4.1") 
    print("3. Send a test message")
    print("="*60)

def main():
    parser = argparse.ArgumentParser(description='Start only Open WebUI and essential dependencies')
    parser.add_argument('--profile', choices=['cpu', 'gpu-nvidia', 'gpu-amd'], default='gpu-nvidia',
                      help='Profile to use for Docker Compose (default: gpu-nvidia)')
    parser.add_argument('--include', nargs='*', 
                      choices=['searxng', 'langfuse', 'clickhouse', 'minio', 'flowise', 'n8n'],
                      help='Optional services to include')
    parser.add_argument('--stop-only', action='store_true',
                      help='Only stop Open WebUI services, do not start')
    parser.add_argument('--status', action='store_true',
                      help='Show status of services')
    
    args = parser.parse_args()

    print("Starting Open WebUI Minimal Stack...")
    print("This includes corporate certificate injection for VPN connectivity.")
    print()

    if args.status:
        show_status()
        return

    # Check corporate overrides exist
    check_corporate_overrides()

    if args.stop_only:
        stop_openwebui_services()
        print("Open WebUI services stopped.")
        return

    # Stop existing services first
    stop_openwebui_services()
    
    # Start the minimal stack
    start_openwebui_stack(args.profile, args.include)
    
    print()
    print("✅ Open WebUI minimal stack startup complete!")
    
    # Show service status
    show_status()
    
    # Show access information  
    show_access_info()

if __name__ == "__main__":
    main()