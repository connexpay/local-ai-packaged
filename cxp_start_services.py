#!/usr/bin/env python3
"""
cxp_start_service.py

This script starts the Supabase stack first, waits for it to initialize, and then starts
the local AI stack with ConnexPay corporate network overrides. Both stacks use the same 
Docker Compose project name ("localai") so they appear together in Docker Desktop.

This version includes corporate certificate injection for SSL connectivity within VPN.
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
    
    print("All ConnexPay corporate override files found.")

def stop_existing_containers(profile=None):
    print("Stopping and removing existing containers for the unified project 'localai'...")
    cmd = ["docker", "compose", "-p", "localai"]
    if profile and profile != "none":
        cmd.extend(["--profile", profile])
    cmd.extend(["-f", "docker-compose.yml"])
    # Include the corporate overrides when stopping to ensure all services are stopped
    cmd.extend(["-f", "connexpay/docker-compose.override.ai.local.cxp.yml"])
    cmd.extend(["-f", "supabase/docker/docker-compose.yml"])  
    cmd.extend(["-f", "connexpay/docker-compose.override.supabase.local.cxp.yml"])
    cmd.extend(["down"])
    
    # Run with error handling since some containers might not exist
    try:
        run_command(cmd)
    except subprocess.CalledProcessError:
        print("Some containers may not have existed - continuing...")

def start_supabase(environment=None):
    """Start the Supabase services with corporate overrides."""
    print("Starting Supabase services with ConnexPay corporate overrides...")
    cmd = ["docker", "compose", "-p", "localai", "-f", "supabase/docker/docker-compose.yml"]
    
    # Add the corporate override for Supabase
    cmd.extend(["-f", "connexpay/docker-compose.override.supabase.local.cxp.yml"])
        
    cmd.extend(["up", "-d"])
    run_command(cmd)

def start_local_ai(profile=None, environment=None):
    """Start the local AI services with corporate overrides."""
    print("Starting local AI services with ConnexPay corporate overrides...")
    cmd = ["docker", "compose", "-p", "localai"]
    
    if profile and profile != "none":
        cmd.extend(["--profile", profile])
    
    cmd.extend(["-f", "docker-compose.yml"])
        
    # Add the corporate override LAST so it takes precedence
    cmd.extend(["-f", "connexpay/docker-compose.override.ai.local.cxp.yml"])
    
    cmd.extend(["up", "-d"])
    run_command(cmd)

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

def check_and_fix_docker_compose_for_searxng():
    """Check and modify docker-compose.yml for SearXNG first run."""
    docker_compose_path = "docker-compose.yml"
    if not os.path.exists(docker_compose_path):
        print(f"Warning: Docker Compose file not found at {docker_compose_path}")
        return

    try:
        # Read the docker-compose.yml file
        with open(docker_compose_path, 'r') as file:
            content = file.read()

        # Default to first run
        is_first_run = True

        # Check if Docker is running and if the SearXNG container exists
        try:
            # Check if the SearXNG container is running
            container_check = subprocess.run(
                ["docker", "ps", "--filter", "name=searxng", "--format", "{{.Names}}"],
                capture_output=True, text=True, check=True
            )
            searxng_containers = container_check.stdout.strip().split('\n')

            # If SearXNG container is running, check inside for uwsgi.ini
            if any(container for container in searxng_containers if container):
                container_name = next(container for container in searxng_containers if container)
                print(f"Found running SearXNG container: {container_name}")

                # Check if uwsgi.ini exists inside the container
                container_check = subprocess.run(
                    ["docker", "exec", container_name, "sh", "-c", "[ -f /etc/searxng/uwsgi.ini ] && echo 'found' || echo 'not_found'"],
                    capture_output=True, text=True, check=False
                )

                if "found" in container_check.stdout:
                    print("Found uwsgi.ini inside the SearXNG container - not first run")
                    is_first_run = False
                else:
                    print("uwsgi.ini not found inside the SearXNG container - first run")
                    is_first_run = True
            else:
                print("No running SearXNG container found - assuming first run")
        except Exception as e:
            print(f"Error checking Docker container: {e} - assuming first run")

        if is_first_run and "cap_drop: - ALL" in content:
            print("First run detected for SearXNG. Temporarily removing 'cap_drop: - ALL' directive...")
            # Temporarily comment out the cap_drop line
            modified_content = content.replace("cap_drop: - ALL", "# cap_drop: - ALL  # Temporarily commented out for first run")

            # Write the modified content back
            with open(docker_compose_path, 'w') as file:
                file.write(modified_content)

            print("Note: After the first run completes successfully, you should re-add 'cap_drop: - ALL' to docker-compose.yml for security reasons.")
        elif not is_first_run and "# cap_drop: - ALL  # Temporarily commented out for first run" in content:
            print("SearXNG has been initialized. Re-enabling 'cap_drop: - ALL' directive for security...")
            # Uncomment the cap_drop line
            modified_content = content.replace("# cap_drop: - ALL  # Temporarily commented out for first run", "cap_drop: - ALL")

            # Write the modified content back
            with open(docker_compose_path, 'w') as file:
                file.write(modified_content)

    except Exception as e:
        print(f"Error checking/modifying docker-compose.yml for SearXNG: {e}")

def main():
    parser = argparse.ArgumentParser(description='Start the local AI and Supabase services with ConnexPay corporate network support.')
    parser.add_argument('--profile', choices=['cpu', 'gpu-nvidia', 'gpu-amd', 'none'], default='gpu-nvidia',
                      help='Profile to use for Docker Compose (default: gpu-nvidia)')
    parser.add_argument('--environment', choices=['private', 'public'], default='private',
                      help='Environment to use for Docker Compose (default: private)')
    args = parser.parse_args()

    print("Starting ConnexPay Local AI Environment...")
    print("This version includes corporate certificate injection for VPN connectivity.")
    print()

    # Check that all required corporate override files exist
    check_corporate_overrides()

    clone_supabase_repo()
    prepare_supabase_env()

    # Generate SearXNG secret key and check docker-compose.yml
    generate_searxng_secret_key()
    check_and_fix_docker_compose_for_searxng()

    stop_existing_containers(args.profile)

    # Start Supabase first with corporate overrides
    start_supabase(args.environment)

    # Give Supabase some time to initialize
    print("Waiting for Supabase to initialize...")
    time.sleep(10)

    # Then start the local AI services with corporate overrides
    start_local_ai(args.profile, args.environment)

    print()
    print("ConnexPay Local AI Environment startup complete!")
    print("All services should now be running with corporate certificate injection.")

if __name__ == "__main__":
    main()