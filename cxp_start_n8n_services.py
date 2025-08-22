#!/usr/bin/env python3
"""
cxp_start_n8n_services.py

This script starts N8N workflow automation and its essential dependencies using the same
corporate network overrides as the full stack. Uses the same Docker Compose project
name ("localai") for consistency.

Dependencies started:
- postgres (data persistence - required by n8n)
- redis (caching/sessions)
- qdrant (vector database for RAG workflows)
- neo4j (graph database for complex workflows)
- n8n-import (initial workflow/credential imports)
- n8n (main workflow automation interface)

Optional services can be added via --include flag.

Note: This version does NOT use Supabase - it uses standalone Postgres from the main docker-compose.yml
"""

import os
import subprocess
import time
import argparse
import sys

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

def stop_n8n_services(profile=None):
    """Stop N8N and related services."""
    print("Stopping existing N8N services...")
    
    # Core services to stop
    services_to_stop = [
        "n8n",
        "n8n-import",
        "postgres",
        "redis",
        "qdrant",
        "neo4j",
        "pgadmin"
    ]
    
    # Build command for stopping services
    cmd = ["docker", "compose", "-p", "localai"]
    if profile and profile != "none":
        cmd.extend(["--profile", profile])
    cmd.extend(["-f", "docker-compose.yml"])
    cmd.extend(["-f", "connexpay/docker-compose.override.ai.local.cxp.yml"])
    cmd.extend(["stop"] + services_to_stop)
    
    try:
        run_command(cmd)
    except subprocess.CalledProcessError:
        print("Some services may not have been running - continuing...")
    
    # Do a clean down to remove orphans
    print("Cleaning up any orphaned containers...")
    cleanup_cmd = ["docker", "compose", "-p", "localai"]
    if profile and profile != "none":
        cleanup_cmd.extend(["--profile", profile])
    cleanup_cmd.extend(["-f", "docker-compose.yml"])
    cleanup_cmd.extend(["-f", "connexpay/docker-compose.override.ai.local.cxp.yml"])
    cleanup_cmd.extend(["down", "--remove-orphans"])
    
    try:
        run_command(cleanup_cmd)
    except subprocess.CalledProcessError:
        print("Cleanup completed with some warnings - continuing...")

def start_n8n_stack(profile="gpu-nvidia", include_services=None):
    """Start N8N and essential dependencies."""
    print("Starting N8N stack with corporate overrides...")
    
    # Start Postgres first (critical for n8n)
    print("Starting Postgres database...")
    postgres_cmd = ["docker", "compose", "-p", "localai"]
    if profile and profile != "none":
        postgres_cmd.extend(["--profile", profile])
    postgres_cmd.extend(["-f", "docker-compose.yml"])
    postgres_cmd.extend(["-f", "connexpay/docker-compose.override.ai.local.cxp.yml"])
    postgres_cmd.extend(["up", "-d", "postgres"])
    
    run_command(postgres_cmd)
    
    # Wait for Postgres to be ready
    print("Waiting for Postgres to be ready...")
    for i in range(30):
        check_cmd = ["docker", "exec", "postgres", "pg_isready", "-U", "postgres"]
        try:
            result = subprocess.run(check_cmd, capture_output=True, text=True)
            if result.returncode == 0:
                print("Postgres is ready!")
                break
        except:
            pass
        time.sleep(1)
        if i == 29:
            print("Warning: Postgres may not be fully ready, continuing anyway...")
    
    # Essential services for N8N (excluding postgres which is already started)
    essential_services = [
        "redis",          # Caching/sessions
        "qdrant",         # Vector database for RAG workflows
        "neo4j",          # Graph database for complex workflows
        "n8n-import",     # Import initial workflows/credentials
        "n8n",            # Main workflow automation interface
        "pgadmin"         # Database management interface   
    ]
    
    # Optional services that can be included
    optional_services = []
    if include_services:
        available_optional = {
            "ollama": "ollama-gpu",
            "open-webui": "open-webui",
            "searxng": "searxng",
            "langfuse": ["langfuse-web", "langfuse-worker", "clickhouse", "minio"],
            "flowise": "flowise",
            "caddy": "caddy"
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
    if profile and profile != "none":
        cmd.extend(["--profile", profile])
    cmd.extend(["-f", "docker-compose.yml"])
    cmd.extend(["-f", "connexpay/docker-compose.override.ai.local.cxp.yml"])
    cmd.extend(["up", "-d"] + all_services)
    
    print(f"Starting services: {', '.join(all_services)}")
    run_command(cmd)

def show_status():
    """Show status of N8N related services."""
    print("\nChecking service status...")
    
    cmd = ["docker", "compose", "-p", "localai", "ps"]
    try:
        run_command(cmd)
    except subprocess.CalledProcessError:
        print("Could not check service status")

def show_access_info(include_services=None):
    """Show how to access the services."""
    print("\n" + "="*60)
    print("N8N Access Information:")
    print("="*60)
    print("🔧 N8N Workflow:   http://localhost:5678")
    print("🔍 Qdrant:         http://localhost:6333")
    print("🔗 Neo4j:          http://localhost:7474")
    print("🗄️  Postgres:       localhost:5432")
    print("📦 Redis:          localhost:6379")
    
    if include_services:
        print("\nOptional Services:")
        if "ollama" in include_services:
            print("🤖 Ollama API:     http://localhost:11434")
        if "open-webui" in include_services:
            print("🌐 Open WebUI:     http://localhost:8080")
        if "searxng" in include_services:
            print("🔎 SearXNG:        http://localhost:8081")
        if "langfuse" in include_services:
            print("📊 Langfuse:       http://localhost:3000")
        if "flowise" in include_services:
            print("🌊 Flowise:        http://localhost:3001")
        if "caddy" in include_services:
            print("🌐 Caddy:          http://localhost:18080")
    
    print("\nTo access N8N:")
    print("1. Go to http://localhost:5678")
    print("2. Login with credentials from your .env file")
    print("3. Imported workflows should be available")
    print("="*60)

def main():
    parser = argparse.ArgumentParser(description='Start N8N workflow automation and essential dependencies')
    parser.add_argument('--profile', choices=['cpu', 'gpu-nvidia', 'gpu-amd', 'none'], default='gpu-nvidia',
                      help='Profile to use for Docker Compose (default: gpu-nvidia)')
    parser.add_argument('--include', nargs='*', 
                      choices=['ollama', 'open-webui', 'searxng', 'langfuse', 'flowise', 'caddy'],
                      help='Optional services to include for N8N integrations')
    parser.add_argument('--stop-only', action='store_true',
                      help='Only stop N8N services, do not start')
    parser.add_argument('--status', action='store_true',
                      help='Show status of services')
    
    args = parser.parse_args()

    print("Starting N8N Minimal Stack (No Supabase)...")
    print("This includes corporate certificate injection for VPN connectivity.")
    print()

    if args.status:
        show_status()
        return

    # Check corporate overrides exist
    check_corporate_overrides()

    if args.stop_only:
        stop_n8n_services(args.profile)
        print("N8N and related services stopped.")
        return
    
    # Stop existing services first
    stop_n8n_services(args.profile)
    
    # Start the N8N stack with optional services
    start_n8n_stack(args.profile, args.include)
    
    print()
    print("✅ N8N minimal stack startup complete!")
    print("All services should now be running with corporate certificate injection.")
    
    # Show service status
    show_status()
    
    # Show access information  
    show_access_info(args.include)

if __name__ == "__main__":
    main()