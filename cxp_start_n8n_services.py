#!/usr/bin/env python3
"""
cxp_start_n8n_services.py

This script starts N8N workflow automation and its essential dependencies using the same
corporate network overrides as the full stack. Uses the same Docker Compose project
name ("localai") for consistency.

Dependencies started:
- Supabase stack (database backend for n8n)
- n8n-import (initial workflow/credential imports)
- n8n (main workflow automation interface)
- postgres (data persistence - part of core services)
- redis (caching/sessions)
- qdrant (vector database for RAG workflows)
- neo4j (graph database for complex workflows)

Optional services can be added via --include flag.
"""

import os
import subprocess
import shutil
import time
import argparse
import platform
import sys

def run_command(cmd, cwd=None):
    """Run a shell command and print it."""
    print("Running:", " ".join(cmd))
    subprocess.run(cmd, cwd=cwd, check=True)

def clone_supabase_repo():
    """Clone the Supabase repository using sparse checkout if not already present."""
    if not os.path.exists("supabase"):
        print("Cloning the Supabase repository...")
        run_command([
            "git", "clone", "--filter=blob:none", "--no-checkout",
            "https://github.com/supabase/supabase.git"
        ])
        os.chdir("supabase")
        run_command(["git", "sparse-checkout", "init", "--cone"])
        run_command(["git", "sparse-checkout", "set", "docker"])
        run_command(["git", "checkout", "master"])
        os.chdir("..")
    else:
        print("Supabase repository already exists, updating...")
        os.chdir("supabase")
        try:
            # Try to pull from the tracked branch first
            run_command(["git", "pull"])
        except subprocess.CalledProcessError:
            # If that fails, explicitly pull from origin master
            print("Standard pull failed, trying explicit pull from origin master...")
            try:
                run_command(["git", "pull", "origin", "master"])
            except subprocess.CalledProcessError as e:
                print(f"Warning: Could not update Supabase repository: {e}")
                print("Continuing with existing Supabase files...")
        os.chdir("..")

def prepare_supabase_env():
    """Copy .env to .env in supabase/docker."""
    env_path = os.path.join("supabase", "docker", ".env")
    env_example_path = os.path.join(".env")
    print("Copying .env in root to .env in supabase/docker...")
    shutil.copyfile(env_example_path, env_path)

def check_corporate_overrides():
    """Check that the required ConnexPay override files exist."""
    print("Checking for ConnexPay corporate override files...")
    
    required_files = [
        "connexpay/ZscalerRootCertificate.crt",
        "connexpay/docker-compose.override.ai.local.cxp.yml",
        "connexpay/docker-compose.override.supabase.local.cxp.yml"
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

def generate_searxng_secret_key():
    """Generate a secret key for SearXNG based on the current platform."""
    print("Checking SearXNG settings...")

    # For ConnexPay version, use the corporate settings file
    settings_path = os.path.join("connexpay", "searxng", "settings.yml")
    settings_base_path = os.path.join("connexpay", "searxng", "settings-base.yml")
    
    # Fallback to root directory if connexpay version doesn't exist
    if not os.path.exists(settings_path):
        print("ConnexPay SearXNG settings not found, checking root directory...")
        settings_path = os.path.join("searxng", "settings.yml")
        settings_base_path = os.path.join("searxng", "settings-base.yml")

    print(f"Using SearXNG settings at: {settings_path}")

    # Check if settings-base.yml exists
    if not os.path.exists(settings_base_path):
        print(f"Warning: SearXNG base settings file not found at {settings_base_path}")
        return

    # Check if settings.yml exists, if not create it from settings-base.yml
    if not os.path.exists(settings_path):
        print(f"SearXNG settings.yml not found. Creating from {settings_base_path}...")
        try:
            # Ensure the directory exists
            os.makedirs(os.path.dirname(settings_path), exist_ok=True)
            shutil.copyfile(settings_base_path, settings_path)
            print(f"Created {settings_path} from {settings_base_path}")
        except Exception as e:
            print(f"Error creating settings.yml: {e}")
            return
    else:
        print(f"SearXNG settings.yml already exists at {settings_path}")

    print("Generating SearXNG secret key...")

    # Detect the platform and run the appropriate command
    system = platform.system()

    try:
        if system == "Windows":
            print("Detected Windows platform, using PowerShell to generate secret key...")
            # PowerShell command to generate a random key and replace in the settings file
            ps_command = [
                "powershell", "-Command",
                "$randomBytes = New-Object byte[] 32; " +
                "(New-Object Security.Cryptography.RNGCryptoServiceProvider).GetBytes($randomBytes); " +
                "$secretKey = -join ($randomBytes | ForEach-Object { \"{0:x2}\" -f $_ }); " +
                f"(Get-Content {settings_path}) -replace 'ultrasecretkey', $secretKey | Set-Content {settings_path}"
            ]
            subprocess.run(ps_command, check=True)

        elif system == "Darwin":  # macOS
            print("Detected macOS platform, using sed command with empty string parameter...")
            # macOS sed command requires an empty string for the -i parameter
            openssl_cmd = ["openssl", "rand", "-hex", "32"]
            random_key = subprocess.check_output(openssl_cmd).decode('utf-8').strip()
            sed_cmd = ["sed", "-i", "", f"s|ultrasecretkey|{random_key}|g", settings_path]
            subprocess.run(sed_cmd, check=True)

        else:  # Linux and other Unix-like systems
            print("Detected Linux/Unix platform, using standard sed command...")
            # Standard sed command for Linux
            openssl_cmd = ["openssl", "rand", "-hex", "32"]
            random_key = subprocess.check_output(openssl_cmd).decode('utf-8').strip()
            sed_cmd = ["sed", "-i", f"s|ultrasecretkey|{random_key}|g", settings_path]
            subprocess.run(sed_cmd, check=True)

        print("SearXNG secret key generated successfully.")

    except Exception as e:
        print(f"Error generating SearXNG secret key: {e}")
        print("You may need to manually generate the secret key using the commands:")
        print(f"  - Linux: sed -i \"s|ultrasecretkey|$(openssl rand -hex 32)|g\" {settings_path}")
        print(f"  - macOS: sed -i '' \"s|ultrasecretkey|$(openssl rand -hex 32)|g\" {settings_path}")
        print("  - Windows (PowerShell):")
        print("    $randomBytes = New-Object byte[] 32")
        print("    (New-Object Security.Cryptography.RNGCryptoServiceProvider).GetBytes($randomBytes)")
        print("    $secretKey = -join ($randomBytes | ForEach-Object { \"{0:x2}\" -f $_ })")
        print(f"    (Get-Content {settings_path}) -replace 'ultrasecretkey', $secretKey | Set-Content {settings_path}")

def stop_n8n_services(profile=None):
    """Stop N8N and related services."""
    print("Stopping existing N8N and Supabase services...")
    
    # Core services to stop
    services_to_stop = [
        "n8n",
        "n8n-import",
        "postgres",
        "redis",
        "qdrant",
        "neo4j"
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
    
    # Also stop Supabase services
    print("Stopping Supabase services...")
    supabase_cmd = ["docker", "compose", "-p", "localai"]
    supabase_cmd.extend(["-f", "supabase/docker/docker-compose.yml"])
    supabase_cmd.extend(["-f", "connexpay/docker-compose.override.supabase.local.cxp.yml"])
    supabase_cmd.extend(["down"])
    
    try:
        run_command(supabase_cmd)
    except subprocess.CalledProcessError:
        print("Some Supabase services may not have been running - continuing...")

def start_supabase():
    """Start the Supabase services with corporate overrides."""
    print("Starting Supabase services with ConnexPay corporate overrides...")
    cmd = ["docker", "compose", "-p", "localai", "-f", "supabase/docker/docker-compose.yml"]
    
    # Add the corporate override for Supabase
    cmd.extend(["-f", "connexpay/docker-compose.override.supabase.local.cxp.yml"])
        
    cmd.extend(["up", "-d"])
    run_command(cmd)

def start_n8n_stack(profile="gpu-nvidia", include_services=None):
    """Start N8N and essential dependencies."""
    print("Starting N8N stack with corporate overrides...")
    
    # Essential services for N8N
    essential_services = [
        "postgres",        # Data persistence (required by n8n)
        "redis",          # Caching/sessions
        "qdrant",         # Vector database for RAG workflows
        "neo4j",          # Graph database for complex workflows
        "n8n-import",     # Import initial workflows/credentials
        "n8n"             # Main workflow automation interface
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
    print("🚀 Supabase:       http://localhost:8000")
    
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
    parser.add_argument('--skip-searxng', action='store_true',
                      help='Skip SearXNG secret key generation')
    
    args = parser.parse_args()

    print("Starting N8N Minimal Stack...")
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

    # Clone Supabase if needed
    clone_supabase_repo()
    prepare_supabase_env()
    
    # Generate SearXNG secret key if searxng is included
    if args.include and 'searxng' in args.include and not args.skip_searxng:
        generate_searxng_secret_key()
    
    # Stop existing services first
    stop_n8n_services(args.profile)
    
    # Start Supabase first (database backend for n8n)
    start_supabase()
    
    # Give Supabase some time to initialize
    print("Waiting for Supabase to initialize...")
    time.sleep(10)
    
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