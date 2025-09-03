#!/usr/bin/env python3
"""
Docker and Docker Compose Installation Script
Installs Docker Engine and Docker Compose on Linux systems and starts the Docker daemon.
"""

import os
import sys
import subprocess
import platform
import urllib.request
import json
import logging
from pathlib import Path

class DockerInstaller:
    def __init__(self):
        self.setup_logging()
        self.system = platform.system().lower()
        self.arch = self.get_architecture()
        
    def setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler('docker_install.log')
            ]
        )
        self.logger = logging.getLogger(__name__)

    def get_architecture(self):
        arch = platform.machine().lower()
        arch_map = {
            'x86_64': 'x86_64',
            'amd64': 'x86_64', 
            'aarch64': 'aarch64',
            'arm64': 'aarch64'
        }
        return arch_map.get(arch, arch)

    def run_command(self, command, check=True, shell=True):
        try:
            self.logger.info(f"Running: {command}")
            result = subprocess.run(
                command, 
                shell=shell, 
                check=check, 
                capture_output=True, 
                text=True
            )
            if result.stdout:
                self.logger.info(f"Output: {result.stdout.strip()}")
            return result
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Command failed: {command}")
            self.logger.error(f"Error: {e.stderr}")
            if check:
                raise
            return e

    def check_root_privileges(self):
        if os.geteuid() != 0:
            self.logger.warning("This script requires root privileges for Docker installation")
            return False
        return True

    def is_docker_installed(self):
        try:
            result = subprocess.run(['docker', '--version'], capture_output=True)
            return result.returncode == 0
        except FileNotFoundError:
            return False

    def is_docker_compose_installed(self):
        try:
            result = subprocess.run(['docker-compose', '--version'], capture_output=True)
            if result.returncode == 0:
                return True
            result = subprocess.run(['docker', 'compose', 'version'], capture_output=True)
            return result.returncode == 0
        except FileNotFoundError:
            return False

    def install_dependencies(self):
        self.logger.info("Installing system dependencies...")
        
        # Detect package manager
        if os.path.exists('/usr/bin/apt'):
            # Ubuntu/Debian
            self.run_command("apt-get update")
            self.run_command("apt-get install -y ca-certificates curl gnupg lsb-release")
        elif os.path.exists('/usr/bin/yum'):
            # RHEL/CentOS
            self.run_command("yum install -y yum-utils device-mapper-persistent-data lvm2")
        elif os.path.exists('/usr/bin/dnf'):
            # Fedora
            self.run_command("dnf install -y dnf-plugins-core")

    def install_docker_ubuntu(self):
        self.logger.info("Installing Docker on Ubuntu/Debian...")
        
        # Remove old Docker packages
        self.run_command("apt-get remove -y docker docker-engine docker.io containerd runc", check=False)
        
        # Add Docker's official GPG key
        self.run_command("mkdir -p /etc/apt/keyrings")
        self.run_command("curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg")
        
        # Set proper permissions for GPG key
        self.run_command("chmod a+r /etc/apt/keyrings/docker.gpg")
        
        # Add Docker repository with proper format
        lsb_release = self.run_command("lsb_release -cs").stdout.strip()
        
        # Use proper architecture detection
        dpkg_arch = self.run_command("dpkg --print-architecture").stdout.strip()
        
        repo_content = f'deb [arch={dpkg_arch} signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu {lsb_release} stable'
        
        # Write repository file
        with open('/etc/apt/sources.list.d/docker.list', 'w') as f:
            f.write(repo_content + '\n')
        
        self.logger.info(f"Added repository: {repo_content}")
        
        # Update package list
        self.run_command("apt-get update")
        
        # Install Docker
        self.run_command("apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin")

    def install_docker_rhel(self):
        self.logger.info("Installing Docker on RHEL/CentOS...")
        
        # Add Docker repository
        self.run_command("yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo")
        
        # Install Docker
        self.run_command("yum install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin")

    def install_docker_fedora(self):
        self.logger.info("Installing Docker on Fedora...")
        
        # Add Docker repository
        self.run_command("dnf config-manager --add-repo https://download.docker.com/linux/fedora/docker-ce.repo")
        
        # Install Docker
        self.run_command("dnf install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin")

    def install_docker_convenience_script(self):
        """Fallback installation using Docker's convenience script"""
        self.logger.info("Using Docker convenience script...")
        self.run_command("curl -fsSL https://get.docker.com -o get-docker.sh")
        self.run_command("sh get-docker.sh")
        self.run_command("rm get-docker.sh")

    def install_docker(self):
        if self.is_docker_installed():
            self.logger.info("Docker is already installed")
            return True

        if not self.check_root_privileges():
            self.logger.error("Root privileges required for Docker installation")
            return False

        try:
            self.install_dependencies()
            
            # Try official repository first
            if os.path.exists('/etc/ubuntu-release') or os.path.exists('/etc/debian_version'):
                try:
                    self.install_docker_ubuntu()
                except Exception as e:
                    self.logger.warning(f"Official repo failed: {e}")
                    self.logger.info("Falling back to convenience script...")
                    self.install_docker_convenience_script()
            elif os.path.exists('/etc/redhat-release'):
                try:
                    self.install_docker_rhel()
                except Exception as e:
                    self.logger.warning(f"Official repo failed: {e}")
                    self.install_docker_convenience_script()
            elif os.path.exists('/etc/fedora-release'):
                try:
                    self.install_docker_fedora()
                except Exception as e:
                    self.logger.warning(f"Official repo failed: {e}")
                    self.install_docker_convenience_script()
            else:
                # Generic installation via convenience script
                self.install_docker_convenience_script()

            self.logger.info("Docker installation completed successfully")
            return True

        except Exception as e:
            self.logger.error(f"Docker installation failed: {e}")
            return False

    def get_latest_compose_version(self):
        try:
            url = "https://api.github.com/repos/docker/compose/releases/latest"
            with urllib.request.urlopen(url) as response:
                data = json.loads(response.read())
                return data['tag_name']
        except Exception as e:
            self.logger.warning(f"Could not fetch latest Docker Compose version: {e}")
            return "v2.21.0"  # Fallback version

    def install_docker_compose(self):
        if self.is_docker_compose_installed():
            self.logger.info("Docker Compose is already installed")
            return True

        try:
            # Try installing Docker Compose plugin first (modern approach)
            if self.check_root_privileges():
                if os.path.exists('/usr/bin/apt'):
                    self.run_command("apt-get install -y docker-compose-plugin")
                    return True
                elif os.path.exists('/usr/bin/yum'):
                    self.run_command("yum install -y docker-compose-plugin")
                    return True
                elif os.path.exists('/usr/bin/dnf'):
                    self.run_command("dnf install -y docker-compose-plugin")
                    return True

            # Fallback to standalone installation
            self.logger.info("Installing Docker Compose standalone...")
            version = self.get_latest_compose_version()
            
            # Create local bin directory if it doesn't exist
            local_bin = os.path.expanduser("~/.local/bin")
            os.makedirs(local_bin, exist_ok=True)
            
            compose_url = f"https://github.com/docker/compose/releases/download/{version}/docker-compose-linux-{self.arch}"
            compose_path = f"{local_bin}/docker-compose"
            
            self.logger.info(f"Downloading Docker Compose {version}...")
            urllib.request.urlretrieve(compose_url, compose_path)
            
            # Make executable
            os.chmod(compose_path, 0o755)
            
            # Add to PATH if not already there
            bashrc_path = os.path.expanduser("~/.bashrc")
            path_export = f'export PATH="$HOME/.local/bin:$PATH"'
            
            try:
                with open(bashrc_path, 'r') as f:
                    if path_export not in f.read():
                        with open(bashrc_path, 'a') as f:
                            f.write(f'\n{path_export}\n')
            except FileNotFoundError:
                with open(bashrc_path, 'w') as f:
                    f.write(f'{path_export}\n')

            self.logger.info("Docker Compose installation completed successfully")
            return True

        except Exception as e:
            self.logger.error(f"Docker Compose installation failed: {e}")
            return False

    def start_docker_daemon(self):
        try:
            # Check if Docker daemon is already running
            result = self.run_command("docker info", check=False)
            if result.returncode == 0:
                self.logger.info("Docker daemon is already running")
                return True

            self.logger.info("Starting Docker daemon...")
            
            if self.check_root_privileges():
                # Try systemctl first
                try:
                    self.run_command("systemctl start docker")
                    self.run_command("systemctl enable docker")
                    self.logger.info("Docker daemon started via systemctl")
                    return True
                except:
                    pass

                # Fallback to service command
                try:
                    self.run_command("service docker start")
                    self.logger.info("Docker daemon started via service command")
                    return True
                except:
                    pass

                # Manual daemon start
                try:
                    self.run_command("dockerd &", check=False)
                    import time
                    time.sleep(5)  # Wait for daemon to start
                    result = self.run_command("docker info", check=False)
                    if result.returncode == 0:
                        self.logger.info("Docker daemon started manually")
                        return True
                except:
                    pass

            else:
                self.logger.error("Root privileges required to start Docker daemon")
                self.logger.info("Try running: sudo systemctl start docker")
                return False

        except Exception as e:
            self.logger.error(f"Failed to start Docker daemon: {e}")
            return False

        self.logger.error("Could not start Docker daemon")
        return False

    def add_user_to_docker_group(self):
        if not self.check_root_privileges():
            self.logger.info("Skipping user group addition (requires root)")
            return

        try:
            username = os.environ.get('SUDO_USER', os.environ.get('USER'))
            if username:
                self.run_command(f"usermod -aG docker {username}")
                self.logger.info(f"Added user {username} to docker group")
                self.logger.info("Please log out and back in for group changes to take effect")
        except Exception as e:
            self.logger.warning(f"Could not add user to docker group: {e}")

    def verify_installation(self):
        self.logger.info("Verifying Docker installation...")
        
        # Check Docker
        if not self.is_docker_installed():
            self.logger.error("Docker verification failed")
            return False
            
        # Check Docker daemon
        result = self.run_command("docker info", check=False)
        if result.returncode != 0:
            self.logger.error("Docker daemon is not running")
            return False

        # Check Docker Compose
        if not self.is_docker_compose_installed():
            self.logger.warning("Docker Compose verification failed")
        
        # Test with hello-world
        try:
            self.run_command("docker run --rm hello-world")
            self.logger.info("Docker installation verified successfully!")
            return True
        except Exception as e:
            self.logger.error(f"Docker test failed: {e}")
            return False

    def install_all(self):
        self.logger.info("Starting Docker and Docker Compose installation...")
        
        # Install Docker
        if not self.install_docker():
            return False
            
        # Install Docker Compose
        self.install_docker_compose()
        
        # Start Docker daemon
        if not self.start_docker_daemon():
            return False
            
        # Add user to docker group
        self.add_user_to_docker_group()
        
        # Verify installation
        return self.verify_installation()

def main():
    if len(sys.argv) > 1 and sys.argv[1] in ['-h', '--help']:
        print("Docker Installation Script")
        print("Usage: python3 install_docker.py")
        print("This script will install Docker and Docker Compose, then start the Docker daemon")
        return

    installer = DockerInstaller()
    
    print("=" * 60)
    print("Docker and Docker Compose Installation Script")
    print("=" * 60)
    
    success = installer.install_all()
    
    if success:
        print("\n" + "=" * 60)
        print("✅ Installation completed successfully!")
        print("=" * 60)
        print("Docker and Docker Compose are now installed and running.")
        print("\nNext steps:")
        print("1. If you're not root, log out and back in for group permissions")
        print("2. Test with: docker run hello-world")
        print("3. Check versions with: docker --version && docker-compose --version")
    else:
        print("\n" + "=" * 60)
        print("❌ Installation encountered errors")
        print("=" * 60)
        print("Check the log file 'docker_install.log' for details")
        sys.exit(1)

if __name__ == "__main__":
    main()