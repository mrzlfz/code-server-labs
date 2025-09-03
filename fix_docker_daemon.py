#!/usr/bin/env python3
"""
Docker Daemon Fix Script
Fixes common Docker daemon issues including iptables, permissions, and networking
"""

import os
import sys
import subprocess
import logging
import time

class DockerDaemonFixer:
    def __init__(self):
        self.setup_logging()
        
    def setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler('docker_fix.log')
            ]
        )
        self.logger = logging.getLogger(__name__)

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
            self.logger.error("This script requires root privileges")
            return False
        return True

    def stop_docker(self):
        """Stop Docker daemon and related services"""
        self.logger.info("Stopping Docker services...")
        
        # Kill existing Docker processes
        self.run_command("pkill -f dockerd", check=False)
        self.run_command("pkill -f containerd", check=False)
        
        # Stop via service
        self.run_command("service docker stop", check=False)
        
        time.sleep(2)

    def fix_iptables_permissions(self):
        """Fix iptables permissions and rules"""
        self.logger.info("Fixing iptables configuration...")
        
        # Clean up existing Docker iptables rules
        self.run_command("iptables -t nat -F DOCKER", check=False)
        self.run_command("iptables -t nat -X DOCKER", check=False)
        self.run_command("iptables -t filter -F DOCKER", check=False)
        self.run_command("iptables -t filter -X DOCKER", check=False)
        self.run_command("iptables -t filter -F DOCKER-ISOLATION-STAGE-1", check=False)
        self.run_command("iptables -t filter -X DOCKER-ISOLATION-STAGE-1", check=False)
        self.run_command("iptables -t filter -F DOCKER-ISOLATION-STAGE-2", check=False)
        self.run_command("iptables -t filter -X DOCKER-ISOLATION-STAGE-2", check=False)
        
        # Allow Docker to manage iptables
        self.run_command("sysctl -w net.ipv4.ip_forward=1", check=False)

    def fix_docker_socket_permissions(self):
        """Fix Docker socket permissions"""
        self.logger.info("Fixing Docker socket permissions...")
        
        # Remove old socket
        self.run_command("rm -f /var/run/docker.sock", check=False)
        
        # Ensure docker group exists
        self.run_command("groupadd -f docker", check=False)

    def create_docker_service_config(self):
        """Create Docker service configuration"""
        self.logger.info("Creating Docker service configuration...")
        
        daemon_json = {
            "hosts": ["unix:///var/run/docker.sock"],
            "iptables": True,
            "bridge": "none",
            "storage-driver": "overlay2"
        }
        
        # Create docker config directory
        os.makedirs('/etc/docker', exist_ok=True)
        
        # Write daemon.json
        import json
        with open('/etc/docker/daemon.json', 'w') as f:
            json.dump(daemon_json, f, indent=2)

    def start_docker_manually(self):
        """Start Docker daemon with custom parameters"""
        self.logger.info("Starting Docker daemon manually...")
        
        # Start dockerd in background with specific options
        cmd = [
            'dockerd',
            '--host=unix:///var/run/docker.sock',
            '--storage-driver=overlay2',
            '--iptables=false',
            '--bridge=none'
        ]
        
        try:
            # Start daemon in background
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.logger.info(f"Docker daemon started with PID: {proc.pid}")
            
            # Wait for daemon to be ready
            for i in range(30):  # Wait up to 30 seconds
                time.sleep(1)
                result = self.run_command("docker info", check=False)
                if result.returncode == 0:
                    self.logger.info("Docker daemon is ready!")
                    return True
                    
            self.logger.error("Docker daemon failed to start properly")
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to start Docker daemon: {e}")
            return False

    def test_docker(self):
        """Test Docker installation"""
        self.logger.info("Testing Docker...")
        
        try:
            # Test docker info
            result = self.run_command("docker info", check=False)
            if result.returncode != 0:
                return False
                
            # Test with simple container
            self.run_command("docker run --rm hello-world")
            self.logger.info("✅ Docker test successful!")
            return True
            
        except Exception as e:
            self.logger.error(f"Docker test failed: {e}")
            return False

    def install_missing_dependencies(self):
        """Install missing dependencies"""
        self.logger.info("Installing missing dependencies...")
        
        # Install fuse-overlayfs for overlay storage driver
        self.run_command("apt-get update", check=False)
        self.run_command("apt-get install -y fuse-overlayfs iptables", check=False)

    def fix_all(self):
        """Run all fixes"""
        if not self.check_root_privileges():
            return False
            
        self.logger.info("Starting Docker daemon fixes...")
        
        # Install missing dependencies
        self.install_missing_dependencies()
        
        # Stop existing Docker
        self.stop_docker()
        
        # Fix permissions and iptables
        self.fix_iptables_permissions()
        self.fix_docker_socket_permissions()
        
        # Create service config
        self.create_docker_service_config()
        
        # Try to start via service first
        self.logger.info("Trying to start Docker via service...")
        result = self.run_command("service docker start", check=False)
        
        if result.returncode == 0:
            time.sleep(5)
            if self.test_docker():
                return True
        
        # If service failed, try manual start
        self.logger.info("Service start failed, trying manual start...")
        if self.start_docker_manually():
            return self.test_docker()
        
        return False

def main():
    if len(sys.argv) > 1 and sys.argv[1] in ['-h', '--help']:
        print("Docker Daemon Fix Script")
        print("Usage: sudo python3 fix_docker_daemon.py")
        print("This script fixes common Docker daemon issues")
        return

    fixer = DockerDaemonFixer()
    
    print("=" * 60)
    print("Docker Daemon Fix Script")
    print("=" * 60)
    
    success = fixer.fix_all()
    
    if success:
        print("\n" + "=" * 60)
        print("✅ Docker daemon fixed successfully!")
        print("=" * 60)
        print("Docker is now running properly.")
        print("Test with: docker run hello-world")
    else:
        print("\n" + "=" * 60)
        print("❌ Docker daemon fix failed")
        print("=" * 60)
        print("Check the log file 'docker_fix.log' for details")
        print("You may need to restart the system or use Docker rootless mode")
        sys.exit(1)

if __name__ == "__main__":
    main()