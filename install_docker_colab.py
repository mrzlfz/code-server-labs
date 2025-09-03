#!/usr/bin/env python3
"""
Docker Installation for Google Colab
Specialized Docker setup for Google Colab environment using Docker-in-Docker approach
"""

import os
import sys
import subprocess
import logging
import time

class DockerColabInstaller:
    def __init__(self):
        self.setup_logging()
        
    def setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler('docker_colab_install.log')
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

    def install_docker_using_dind(self):
        """Install and run Docker using Docker-in-Docker container"""
        self.logger.info("Starting Docker-in-Docker approach...")
        
        # Start Docker daemon in a container
        dind_command = """
docker run -d \
  --name docker-daemon \
  --privileged \
  --restart unless-stopped \
  -p 2376:2376 \
  -v /var/lib/docker \
  docker:dind \
  dockerd \
    --host=tcp://0.0.0.0:2376 \
    --tls=false
"""
        
        try:
            # Check if docker command exists (from previous installation)
            result = self.run_command("which docker", check=False)
            if result.returncode != 0:
                self.logger.error("Docker binary not found. Please run the main installation script first.")
                return False
            
            # Remove existing docker-daemon container if exists
            self.run_command("docker rm -f docker-daemon", check=False)
            
            # Start Docker-in-Docker
            self.run_command(dind_command.strip())
            
            # Wait for daemon to start
            time.sleep(10)
            
            # Set DOCKER_HOST environment variable
            os.environ['DOCKER_HOST'] = 'tcp://localhost:2376'
            
            # Test the connection
            result = self.run_command("docker -H tcp://localhost:2376 info", check=False)
            if result.returncode == 0:
                self.logger.info("Docker-in-Docker started successfully!")
                return True
            else:
                self.logger.error("Failed to connect to Docker-in-Docker daemon")
                return False
                
        except Exception as e:
            self.logger.error(f"Docker-in-Docker setup failed: {e}")
            return False

    def create_docker_wrapper_script(self):
        """Create a wrapper script to use Docker with custom host"""
        self.logger.info("Creating Docker wrapper script...")
        
        wrapper_content = """#!/bin/bash
# Docker wrapper script for Colab
export DOCKER_HOST=tcp://localhost:2376
/usr/bin/docker "$@"
"""
        
        wrapper_path = "/usr/local/bin/docker-colab"
        
        with open(wrapper_path, 'w') as f:
            f.write(wrapper_content)
        
        os.chmod(wrapper_path, 0o755)
        
        self.logger.info(f"Docker wrapper created at {wrapper_path}")

    def setup_docker_compose(self):
        """Setup Docker Compose to work with custom Docker host"""
        self.logger.info("Setting up Docker Compose...")
        
        compose_wrapper = """#!/bin/bash
# Docker Compose wrapper script for Colab
export DOCKER_HOST=tcp://localhost:2376
/usr/local/bin/docker-compose "$@"
"""
        
        wrapper_path = "/usr/local/bin/docker-compose-colab"
        
        with open(wrapper_path, 'w') as f:
            f.write(compose_wrapper)
        
        os.chmod(wrapper_path, 0o755)
        
        self.logger.info(f"Docker Compose wrapper created at {wrapper_path}")

    def test_installation(self):
        """Test the Docker installation"""
        self.logger.info("Testing Docker installation...")
        
        # Set environment for testing
        os.environ['DOCKER_HOST'] = 'tcp://localhost:2376'
        
        try:
            # Test docker info
            self.run_command("docker info")
            
            # Test with hello-world
            self.run_command("docker run --rm hello-world")
            
            self.logger.info("✅ Docker test successful!")
            return True
            
        except Exception as e:
            self.logger.error(f"Docker test failed: {e}")
            return False

    def create_startup_script(self):
        """Create a startup script to automatically start Docker daemon"""
        startup_script = """#!/bin/bash
# Docker Colab Startup Script

echo "Starting Docker for Google Colab..."

# Check if docker daemon container is running
if ! docker ps | grep -q docker-daemon; then
    echo "Starting Docker daemon container..."
    docker run -d \\
      --name docker-daemon \\
      --privileged \\
      --restart unless-stopped \\
      -p 2376:2376 \\
      -v /var/lib/docker \\
      docker:dind \\
      dockerd \\
        --host=tcp://0.0.0.0:2376 \\
        --tls=false
    
    echo "Waiting for Docker daemon to start..."
    sleep 10
fi

# Set environment
export DOCKER_HOST=tcp://localhost:2376

echo "Docker is ready!"
echo "Use: export DOCKER_HOST=tcp://localhost:2376"
echo "Or use the wrapper scripts: docker-colab, docker-compose-colab"
"""
        
        script_path = "/usr/local/bin/start-docker-colab"
        
        with open(script_path, 'w') as f:
            f.write(startup_script)
        
        os.chmod(script_path, 0o755)
        
        self.logger.info(f"Startup script created at {script_path}")

    def install_all(self):
        """Run complete installation for Colab"""
        self.logger.info("Starting Docker installation for Google Colab...")
        
        # Install Docker-in-Docker
        if not self.install_docker_using_dind():
            return False
        
        # Create wrapper scripts
        self.create_docker_wrapper_script()
        self.setup_docker_compose()
        
        # Create startup script
        self.create_startup_script()
        
        # Test installation
        if not self.test_installation():
            return False
        
        return True

def main():
    if len(sys.argv) > 1 and sys.argv[1] in ['-h', '--help']:
        print("Docker Installation for Google Colab")
        print("Usage: sudo python3 install_docker_colab.py")
        print("This script sets up Docker using Docker-in-Docker for Colab")
        return

    installer = DockerColabInstaller()
    
    print("=" * 60)
    print("Docker Installation for Google Colab")
    print("=" * 60)
    
    success = installer.install_all()
    
    if success:
        print("\n" + "=" * 60)
        print("✅ Docker for Colab installed successfully!")
        print("=" * 60)
        print("Docker is now running in Docker-in-Docker mode.")
        print("\nUsage:")
        print("1. Set environment: export DOCKER_HOST=tcp://localhost:2376")
        print("2. Or use wrapper: docker-colab run hello-world")
        print("3. Start daemon: start-docker-colab")
        print("4. Docker Compose: docker-compose-colab up")
        print("\nTo restart Docker daemon:")
        print("start-docker-colab")
    else:
        print("\n" + "=" * 60)
        print("❌ Docker installation failed")
        print("=" * 60)
        print("Check the log file 'docker_colab_install.log' for details")
        sys.exit(1)

if __name__ == "__main__":
    main()