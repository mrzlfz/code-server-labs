#!/usr/bin/env python3
"""
Code Server Setup for Google Colab
==================================

A comprehensive Python script to set up VS Code Server on Google Colab
with ngrok tunneling, full features, and interactive menu system.

Features:
- Interactive CLI menu system
- Code Server installation without systemd
- Ngrok tunneling for web access
- VS Code extensions management
- Google Colab optimization
- Configuration persistence
- Process management

Author: AI Assistant
Version: 1.0.0
"""

import os
import sys
import json
import subprocess
import threading
import time
import logging
import argparse
import getpass
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse
import requests
import tarfile
import shutil

# Third-party imports (will be installed if needed)
try:
    from pyngrok import ngrok, conf
    PYNGROK_AVAILABLE = True
except ImportError:
    PYNGROK_AVAILABLE = False

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

# Configuration
CONFIG_DIR = Path.home() / ".config" / "code-server-colab"
CONFIG_FILE = CONFIG_DIR / "config.json"
LOG_FILE = CONFIG_DIR / "setup.log"
INSTALL_DIR = Path.home() / ".local" / "lib" / "code-server"
BIN_DIR = Path.home() / ".local" / "bin"

# Default configuration
DEFAULT_CONFIG = {
    "code_server": {
        "version": "4.23.1",
        "port": 8080,
        "auth": "password",
        "password": "",
        "bind_addr": "127.0.0.1",
        "extensions_dir": str(Path.home() / ".local" / "share" / "code-server" / "extensions"),
        "user_data_dir": str(Path.home() / ".local" / "share" / "code-server")
    },
    "ngrok": {
        "auth_token": "",
        "region": "us",
        "protocol": "http"
    },
    "extensions": {
        "popular": [
            "ms-python.python",
            "ms-python.vscode-pylance",
            "ms-toolsai.jupyter",
            "ms-vscode.vscode-json",
            "redhat.vscode-yaml",
            "ms-vscode.theme-tomorrow-night-blue",
            "PKief.material-icon-theme",
            "ms-vscode.vscode-typescript-next",
            "bradlc.vscode-tailwindcss",
            "esbenp.prettier-vscode"
        ],
        "custom": []
    },
    "colab": {
        "auto_detect": True,
        "optimize_resources": True,
        "persist_config": True
    }
}

class Logger:
    """Enhanced logging system with console and file output."""
    
    def __init__(self, log_file: Path):
        self.log_file = log_file
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def info(self, message: str):
        self.logger.info(message)
    
    def error(self, message: str):
        self.logger.error(message)
    
    def warning(self, message: str):
        self.logger.warning(message)
    
    def debug(self, message: str):
        self.logger.debug(message)

class ConfigManager:
    """Configuration management with persistence."""
    
    def __init__(self, config_file: Path):
        self.config_file = config_file
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        self.config = self.load_config()
    
    def load_config(self) -> Dict:
        """Load configuration from file or create default."""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                # Merge with defaults to ensure all keys exist
                return self._merge_config(DEFAULT_CONFIG, config)
            except Exception as e:
                print(f"Error loading config: {e}. Using defaults.")
                return DEFAULT_CONFIG.copy()
        else:
            return DEFAULT_CONFIG.copy()
    
    def save_config(self):
        """Save current configuration to file."""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            print(f"Error saving config: {e}")
    
    def _merge_config(self, default: Dict, user: Dict) -> Dict:
        """Recursively merge user config with defaults."""
        result = default.copy()
        for key, value in user.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_config(result[key], value)
            else:
                result[key] = value
        return result
    
    def get(self, key_path: str, default=None):
        """Get configuration value using dot notation."""
        keys = key_path.split('.')
        value = self.config
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        return value
    
    def set(self, key_path: str, value):
        """Set configuration value using dot notation."""
        keys = key_path.split('.')
        config = self.config
        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]
        config[keys[-1]] = value
        self.save_config()

class SystemUtils:
    """System utilities and environment detection."""
    
    @staticmethod
    def is_colab() -> bool:
        """Detect if running in Google Colab."""
        try:
            import google.colab
            return True
        except ImportError:
            return False
    
    @staticmethod
    def get_system_info() -> Dict:
        """Get system information."""
        info = {
            "platform": sys.platform,
            "python_version": sys.version,
            "is_colab": SystemUtils.is_colab(),
            "home_dir": str(Path.home()),
            "cwd": os.getcwd()
        }
        
        if PSUTIL_AVAILABLE:
            info.update({
                "cpu_count": psutil.cpu_count(),
                "memory_total": psutil.virtual_memory().total,
                "disk_free": psutil.disk_usage('/').free
            })
        
        return info
    
    @staticmethod
    def install_package(package: str) -> bool:
        """Install Python package using pip."""
        try:
            subprocess.check_call([
                sys.executable, "-m", "pip", "install", package, "--quiet"
            ])
            return True
        except subprocess.CalledProcessError:
            return False
    
    @staticmethod
    def run_command(command: List[str], capture_output: bool = True) -> Tuple[bool, str]:
        """Run system command and return success status and output."""
        try:
            if capture_output:
                result = subprocess.run(
                    command, 
                    capture_output=True, 
                    text=True, 
                    check=True
                )
                return True, result.stdout
            else:
                subprocess.run(command, check=True)
                return True, ""
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr if hasattr(e, 'stderr') and e.stderr else str(e)
            return False, error_msg

# Initialize global components
logger = Logger(LOG_FILE)
config_manager = ConfigManager(CONFIG_FILE)

def print_banner():
    """Print application banner."""
    banner = """
╔══════════════════════════════════════════════════════════════╗
║                    Code Server Colab Setup                   ║
║                                                              ║
║  🚀 VS Code in your browser with full features              ║
║  🌐 Ngrok tunneling for web access                          ║
║  📦 Extensions and workspace management                      ║
║  ⚡ Optimized for Google Colab                              ║
╚══════════════════════════════════════════════════════════════╝
    """
    print(banner)

class CodeServerSetup:
    """Main application class for Code Server setup and management."""

    def __init__(self):
        self.config = config_manager
        self.logger = logger
        self.system_info = SystemUtils.get_system_info()
        self.code_server_process = None
        self.ngrok_tunnel = None

        # Ensure required directories exist
        INSTALL_DIR.mkdir(parents=True, exist_ok=True)
        BIN_DIR.mkdir(parents=True, exist_ok=True)

        # Add bin directory to PATH if not already there
        bin_str = str(BIN_DIR)
        if bin_str not in os.environ.get("PATH", ""):
            os.environ["PATH"] = f"{bin_str}:{os.environ.get('PATH', '')}"

    def show_interactive_menu(self):
        """Display interactive menu and handle user choices."""
        while True:
            self._clear_screen()
            print_banner()

            # Show system info
            print(f"📊 System: {self.system_info['platform']} | Colab: {'Yes' if self.system_info['is_colab'] else 'No'}")
            print(f"📁 Install Dir: {INSTALL_DIR}")
            print()

            # Show current status
            status = self._get_status()
            print(f"🔧 Code Server: {status['code_server']}")
            print(f"🌐 Ngrok: {status['ngrok']}")
            if status['url']:
                print(f"🔗 Access URL: {status['url']}")
            print()

            # Menu options
            menu_options = [
                ("1", "🚀 Install Code Server", self.install_code_server),
                ("2", "▶️  Start Code Server", self.start_code_server),
                ("3", "⏹️  Stop Code Server", self.stop_code_server),
                ("4", "🔄 Restart Code Server", self.restart_code_server),
                ("5", "📊 Show Status", self.show_status),
                ("6", "⚙️  Configure Settings", self.configure_settings),
                ("7", "📦 Manage Extensions", self.manage_extensions),
                ("8", "🌐 Setup Ngrok", self.setup_ngrok),
                ("9", "🔧 System Info", self.show_system_info),
                ("10", "📋 View Logs", self.view_logs),
                ("0", "❌ Exit", self._exit_app)
            ]

            print("📋 Menu Options:")
            for key, description, _ in menu_options:
                print(f"  {key}. {description}")
            print()

            try:
                choice = input("👉 Select option (0-10): ").strip()

                # Find and execute the selected option
                for key, _, func in menu_options:
                    if choice == key:
                        print()
                        func()
                        break
                else:
                    print("❌ Invalid option. Please try again.")
                    time.sleep(1)

                if choice != "0":
                    input("\n⏸️  Press Enter to continue...")

            except KeyboardInterrupt:
                print("\n\n👋 Goodbye!")
                break
            except Exception as e:
                self.logger.error(f"Menu error: {e}")
                print(f"❌ Error: {e}")
                time.sleep(2)

    def _clear_screen(self):
        """Clear terminal screen."""
        os.system('clear' if os.name == 'posix' else 'cls')

    def _get_status(self) -> Dict:
        """Get current status of services."""
        status = {
            "code_server": "Not Installed",
            "ngrok": "Not Setup",
            "url": None
        }

        # Check Code Server installation
        code_server_bin = BIN_DIR / "code-server"
        if code_server_bin.exists():
            if self._is_code_server_running():
                status["code_server"] = "Running"
            else:
                status["code_server"] = "Stopped"

        # Check ngrok status
        if self.config.get("ngrok.auth_token"):
            status["ngrok"] = "Configured"
            if self.ngrok_tunnel:
                status["ngrok"] = "Active"
                status["url"] = self.ngrok_tunnel.public_url

        return status

    def _is_code_server_running(self) -> bool:
        """Check if Code Server is currently running."""
        if not PSUTIL_AVAILABLE:
            # Fallback method using ps command
            try:
                result = subprocess.run(
                    ["pgrep", "-f", "code-server"],
                    capture_output=True,
                    text=True
                )
                return result.returncode == 0
            except:
                return False

        # Use psutil if available
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if 'code-server' in ' '.join(proc.info['cmdline'] or []):
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return False

    def _exit_app(self):
        """Exit the application."""
        print("👋 Thank you for using Code Server Colab Setup!")
        sys.exit(0)

    def install_code_server(self):
        """Install Code Server with all dependencies."""
        print("🚀 Installing Code Server...")

        try:
            # Check if already installed
            code_server_bin = BIN_DIR / "code-server"
            if code_server_bin.exists():
                print("ℹ️  Code Server is already installed.")
                choice = input("🔄 Reinstall? (y/N): ").strip().lower()
                if choice != 'y':
                    return

            # Install required Python packages
            print("📦 Installing Python dependencies...")
            required_packages = ["pyngrok", "psutil", "requests"]
            for package in required_packages:
                print(f"  Installing {package}...")
                if not SystemUtils.install_package(package):
                    self.logger.warning(f"Failed to install {package}")

            # Download and install Code Server
            version = self.config.get("code_server.version", "4.23.1")
            print(f"⬇️  Downloading Code Server v{version}...")

            if not self._download_code_server(version):
                print("❌ Failed to download Code Server")
                return

            print("📁 Extracting Code Server...")
            if not self._extract_code_server(version):
                print("❌ Failed to extract Code Server")
                return

            print("🔗 Creating symlinks...")
            if not self._create_symlinks(version):
                print("❌ Failed to create symlinks")
                return

            # Generate default password if not set
            if not self.config.get("code_server.password"):
                import secrets
                import string
                password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(12))
                self.config.set("code_server.password", password)
                print(f"🔑 Generated password: {password}")

            # Create Code Server config
            self._create_code_server_config()

            print("✅ Code Server installed successfully!")

        except Exception as e:
            self.logger.error(f"Installation failed: {e}")
            print(f"❌ Installation failed: {e}")

    def _download_code_server(self, version: str) -> bool:
        """Download Code Server binary."""
        try:
            # Determine architecture
            import platform
            arch_map = {
                "x86_64": "amd64",
                "aarch64": "arm64",
                "armv7l": "armv7"
            }
            arch = arch_map.get(platform.machine(), "amd64")

            # Download URL
            filename = f"code-server-{version}-linux-{arch}.tar.gz"
            url = f"https://github.com/coder/code-server/releases/download/v{version}/{filename}"

            # Download file
            response = requests.get(url, stream=True)
            response.raise_for_status()

            download_path = INSTALL_DIR / filename
            with open(download_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            self.download_path = download_path
            return True

        except Exception as e:
            self.logger.error(f"Download failed: {e}")
            return False

    def _extract_code_server(self, version: str) -> bool:
        """Extract Code Server archive."""
        try:
            with tarfile.open(self.download_path, 'r:gz') as tar:
                tar.extractall(INSTALL_DIR)

            # Remove download file
            self.download_path.unlink()

            return True

        except Exception as e:
            self.logger.error(f"Extraction failed: {e}")
            return False

    def _create_symlinks(self, version: str) -> bool:
        """Create symlinks for Code Server binary."""
        try:
            import platform
            arch_map = {
                "x86_64": "amd64",
                "aarch64": "arm64",
                "armv7l": "armv7"
            }
            arch = arch_map.get(platform.machine(), "amd64")

            source_dir = INSTALL_DIR / f"code-server-{version}-linux-{arch}"
            target_dir = INSTALL_DIR / "current"

            # Remove existing symlink
            if target_dir.exists():
                if target_dir.is_symlink():
                    target_dir.unlink()
                else:
                    shutil.rmtree(target_dir)

            # Create new symlink
            target_dir.symlink_to(source_dir)

            # Create binary symlink
            bin_source = target_dir / "bin" / "code-server"
            bin_target = BIN_DIR / "code-server"

            if bin_target.exists():
                bin_target.unlink()

            bin_target.symlink_to(bin_source)

            # Make executable
            bin_target.chmod(0o755)

            return True

        except Exception as e:
            self.logger.error(f"Symlink creation failed: {e}")
            return False

    def _create_code_server_config(self):
        """Create Code Server configuration file."""
        try:
            config_dir = Path.home() / ".config" / "code-server"
            config_dir.mkdir(parents=True, exist_ok=True)

            config_file = config_dir / "config.yaml"

            config_content = f"""bind-addr: {self.config.get('code_server.bind_addr')}:{self.config.get('code_server.port')}
auth: {self.config.get('code_server.auth')}
password: {self.config.get('code_server.password')}
cert: false
extensions-dir: {self.config.get('code_server.extensions_dir')}
user-data-dir: {self.config.get('code_server.user_data_dir')}
"""

            with open(config_file, 'w') as f:
                f.write(config_content)

            self.logger.info("Code Server config created")

        except Exception as e:
            self.logger.error(f"Config creation failed: {e}")

    def start_code_server(self):
        """Start Code Server process."""
        print("▶️  Starting Code Server...")

        try:
            # Check if already running
            if self._is_code_server_running():
                print("ℹ️  Code Server is already running.")
                return

            # Check if installed
            code_server_bin = BIN_DIR / "code-server"
            if not code_server_bin.exists():
                print("❌ Code Server is not installed. Please install it first.")
                return

            # Start Code Server in background
            print("🚀 Starting Code Server process...")

            # Prepare environment
            env = os.environ.copy()
            env["EXTENSIONS_GALLERY"] = '{"serviceUrl": "https://open-vsx.org/vscode/gallery", "itemUrl": "https://open-vsx.org/vscode/item"}'

            # Start process
            self.code_server_process = subprocess.Popen(
                [str(code_server_bin)],
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                start_new_session=True
            )

            # Wait a moment for startup
            time.sleep(3)

            if self._is_code_server_running():
                print("✅ Code Server started successfully!")

                # Setup ngrok tunnel if configured
                if self.config.get("ngrok.auth_token"):
                    self._start_ngrok_tunnel()
                else:
                    print("🌐 Access Code Server at: http://127.0.0.1:8080")
                    print("🔑 Password:", self.config.get("code_server.password"))
            else:
                print("❌ Failed to start Code Server")

        except Exception as e:
            self.logger.error(f"Failed to start Code Server: {e}")
            print(f"❌ Failed to start Code Server: {e}")

    def stop_code_server(self):
        """Stop Code Server process."""
        print("⏹️  Stopping Code Server...")

        try:
            # Stop ngrok tunnel first
            if self.ngrok_tunnel:
                print("🌐 Closing ngrok tunnel...")
                ngrok.disconnect(self.ngrok_tunnel.public_url)
                self.ngrok_tunnel = None

            # Find and kill Code Server processes
            killed = False

            if PSUTIL_AVAILABLE:
                for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                    try:
                        if 'code-server' in ' '.join(proc.info['cmdline'] or []):
                            proc.terminate()
                            killed = True
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue
            else:
                # Fallback method
                try:
                    subprocess.run(["pkill", "-f", "code-server"], check=False)
                    killed = True
                except:
                    pass

            if killed:
                print("✅ Code Server stopped successfully!")
            else:
                print("ℹ️  Code Server was not running.")

        except Exception as e:
            self.logger.error(f"Failed to stop Code Server: {e}")
            print(f"❌ Failed to stop Code Server: {e}")

    def restart_code_server(self):
        """Restart Code Server."""
        print("🔄 Restarting Code Server...")
        self.stop_code_server()
        time.sleep(2)
        self.start_code_server()

    def show_status(self):
        """Show detailed status information."""
        print("📊 System Status")
        print("=" * 50)

        status = self._get_status()

        print(f"🔧 Code Server: {status['code_server']}")
        print(f"🌐 Ngrok: {status['ngrok']}")

        if status['url']:
            print(f"🔗 Access URL: {status['url']}")
        else:
            port = self.config.get('code_server.port', 8080)
            print(f"🔗 Local URL: http://127.0.0.1:{port}")

        print(f"🔑 Password: {self.config.get('code_server.password', 'Not set')}")

        # System info
        print("\n💻 System Information:")
        print(f"  Platform: {self.system_info['platform']}")
        print(f"  Python: {self.system_info['python_version'].split()[0]}")
        print(f"  Google Colab: {'Yes' if self.system_info['is_colab'] else 'No'}")
        print(f"  Home Directory: {self.system_info['home_dir']}")

        if PSUTIL_AVAILABLE:
            print(f"  CPU Cores: {self.system_info.get('cpu_count', 'Unknown')}")
            print(f"  Memory: {self.system_info.get('memory_total', 0) // (1024**3)} GB")
            print(f"  Disk Free: {self.system_info.get('disk_free', 0) // (1024**3)} GB")

    def setup_ngrok(self):
        """Setup ngrok authentication and configuration."""
        print("🌐 Setting up Ngrok...")

        try:
            # Install pyngrok if not available
            if not PYNGROK_AVAILABLE:
                print("📦 Installing pyngrok...")
                if SystemUtils.install_package("pyngrok"):
                    print("✅ pyngrok installed successfully!")
                    # Re-import after installation
                    global ngrok, conf
                    from pyngrok import ngrok, conf
                else:
                    print("❌ Failed to install pyngrok")
                    return

            # Get auth token
            current_token = self.config.get("ngrok.auth_token", "")
            if current_token:
                print(f"🔑 Current token: {current_token[:8]}...")
                use_current = input("Use current token? (Y/n): ").strip().lower()
                if use_current != 'n':
                    auth_token = current_token
                else:
                    auth_token = self._get_ngrok_token()
            else:
                auth_token = self._get_ngrok_token()

            if not auth_token:
                print("❌ No auth token provided")
                return

            # Configure ngrok
            print("⚙️  Configuring ngrok...")
            conf.get_default().auth_token = auth_token

            # Save configuration
            self.config.set("ngrok.auth_token", auth_token)

            # Test connection
            print("🧪 Testing ngrok connection...")
            try:
                # Create a temporary tunnel to test
                test_tunnel = ngrok.connect(8080, "http")
                print(f"✅ Ngrok configured successfully!")
                print(f"🔗 Test URL: {test_tunnel.public_url}")

                # Close test tunnel
                ngrok.disconnect(test_tunnel.public_url)

            except Exception as e:
                print(f"❌ Ngrok test failed: {e}")

        except Exception as e:
            self.logger.error(f"Ngrok setup failed: {e}")
            print(f"❌ Ngrok setup failed: {e}")

    def _get_ngrok_token(self) -> str:
        """Get ngrok auth token from user."""
        print("\n🔑 Ngrok Authentication Required")
        print("1. Go to https://dashboard.ngrok.com/get-started/your-authtoken")
        print("2. Sign up/login to get your auth token")
        print("3. Copy and paste the token below")
        print()

        token = getpass.getpass("Enter your ngrok auth token: ").strip()
        return token

    def _start_ngrok_tunnel(self):
        """Start ngrok tunnel for Code Server."""
        try:
            if not self.config.get("ngrok.auth_token"):
                print("❌ Ngrok not configured. Please setup ngrok first.")
                return

            print("🌐 Starting ngrok tunnel...")

            # Configure ngrok
            conf.get_default().auth_token = self.config.get("ngrok.auth_token")

            # Create tunnel
            port = self.config.get("code_server.port", 8080)
            self.ngrok_tunnel = ngrok.connect(port, "http")

            print(f"✅ Ngrok tunnel active!")
            print(f"🔗 Access URL: {self.ngrok_tunnel.public_url}")
            print(f"🔑 Password: {self.config.get('code_server.password')}")

        except Exception as e:
            self.logger.error(f"Ngrok tunnel failed: {e}")
            print(f"❌ Ngrok tunnel failed: {e}")

    def configure_settings(self):
        """Configure application settings."""
        print("⚙️  Configuration Settings")
        print("=" * 30)

        while True:
            print("\n📋 Configuration Options:")
            print("1. Code Server Settings")
            print("2. Ngrok Settings")
            print("3. Extension Settings")
            print("4. System Settings")
            print("5. Reset to Defaults")
            print("0. Back to Main Menu")

            choice = input("\n👉 Select option (0-5): ").strip()

            if choice == "1":
                self._configure_code_server()
            elif choice == "2":
                self._configure_ngrok()
            elif choice == "3":
                self._configure_extensions()
            elif choice == "4":
                self._configure_system()
            elif choice == "5":
                self._reset_config()
            elif choice == "0":
                break
            else:
                print("❌ Invalid option")

    def _configure_code_server(self):
        """Configure Code Server specific settings."""
        print("\n🔧 Code Server Configuration")

        # Port
        current_port = self.config.get("code_server.port", 8080)
        new_port = input(f"Port [{current_port}]: ").strip()
        if new_port and new_port.isdigit():
            self.config.set("code_server.port", int(new_port))

        # Password
        current_password = self.config.get("code_server.password", "")
        print(f"Current password: {'*' * len(current_password) if current_password else 'Not set'}")
        change_password = input("Change password? (y/N): ").strip().lower()
        if change_password == 'y':
            new_password = getpass.getpass("New password: ").strip()
            if new_password:
                self.config.set("code_server.password", new_password)

        # Auth method
        current_auth = self.config.get("code_server.auth", "password")
        print(f"Current auth method: {current_auth}")
        print("Available: password, none")
        new_auth = input(f"Auth method [{current_auth}]: ").strip()
        if new_auth in ["password", "none"]:
            self.config.set("code_server.auth", new_auth)

        print("✅ Code Server configuration updated!")

    def _configure_ngrok(self):
        """Configure ngrok specific settings."""
        print("\n🌐 Ngrok Configuration")

        # Auth token
        current_token = self.config.get("ngrok.auth_token", "")
        if current_token:
            print(f"Current token: {current_token[:8]}...")
            change_token = input("Change token? (y/N): ").strip().lower()
            if change_token == 'y':
                new_token = self._get_ngrok_token()
                if new_token:
                    self.config.set("ngrok.auth_token", new_token)
        else:
            new_token = self._get_ngrok_token()
            if new_token:
                self.config.set("ngrok.auth_token", new_token)

        # Region
        current_region = self.config.get("ngrok.region", "us")
        print(f"Current region: {current_region}")
        print("Available: us, eu, ap, au, sa, jp, in")
        new_region = input(f"Region [{current_region}]: ").strip()
        if new_region in ["us", "eu", "ap", "au", "sa", "jp", "in"]:
            self.config.set("ngrok.region", new_region)

        print("✅ Ngrok configuration updated!")

    def _configure_extensions(self):
        """Configure extension settings."""
        print("\n📦 Extension Configuration")

        # Show current popular extensions
        popular = self.config.get("extensions.popular", [])
        print(f"Popular extensions ({len(popular)}):")
        for i, ext in enumerate(popular[:5], 1):
            print(f"  {i}. {ext}")
        if len(popular) > 5:
            print(f"  ... and {len(popular) - 5} more")

        # Show custom extensions
        custom = self.config.get("extensions.custom", [])
        if custom:
            print(f"\nCustom extensions ({len(custom)}):")
            for i, ext in enumerate(custom[:3], 1):
                print(f"  {i}. {ext}")
            if len(custom) > 3:
                print(f"  ... and {len(custom) - 3} more")

        print("\n📋 Extension Options:")
        print("1. Add custom extension")
        print("2. Remove custom extension")
        print("3. Reset popular extensions")
        print("0. Back")

        choice = input("\n👉 Select option: ").strip()

        if choice == "1":
            ext_id = input("Extension ID (e.g., ms-python.python): ").strip()
            if ext_id:
                custom.append(ext_id)
                self.config.set("extensions.custom", custom)
                print(f"✅ Added {ext_id}")

        elif choice == "2":
            if custom:
                print("Custom extensions:")
                for i, ext in enumerate(custom, 1):
                    print(f"  {i}. {ext}")
                try:
                    idx = int(input("Remove extension number: ")) - 1
                    if 0 <= idx < len(custom):
                        removed = custom.pop(idx)
                        self.config.set("extensions.custom", custom)
                        print(f"✅ Removed {removed}")
                except ValueError:
                    print("❌ Invalid number")
            else:
                print("No custom extensions to remove")

        elif choice == "3":
            self.config.set("extensions.popular", DEFAULT_CONFIG["extensions"]["popular"])
            print("✅ Popular extensions reset to defaults")

    def _configure_system(self):
        """Configure system settings."""
        print("\n💻 System Configuration")

        # Colab optimization
        current_optimize = self.config.get("colab.optimize_resources", True)
        print(f"Resource optimization: {'Enabled' if current_optimize else 'Disabled'}")
        toggle = input("Toggle optimization? (y/N): ").strip().lower()
        if toggle == 'y':
            self.config.set("colab.optimize_resources", not current_optimize)

        # Config persistence
        current_persist = self.config.get("colab.persist_config", True)
        print(f"Config persistence: {'Enabled' if current_persist else 'Disabled'}")
        toggle = input("Toggle persistence? (y/N): ").strip().lower()
        if toggle == 'y':
            self.config.set("colab.persist_config", not current_persist)

        print("✅ System configuration updated!")

    def _reset_config(self):
        """Reset configuration to defaults."""
        print("\n🔄 Reset Configuration")
        print("⚠️  This will reset ALL settings to defaults!")
        confirm = input("Are you sure? (type 'yes' to confirm): ").strip()

        if confirm.lower() == 'yes':
            self.config.config = DEFAULT_CONFIG.copy()
            self.config.save_config()
            print("✅ Configuration reset to defaults!")
        else:
            print("❌ Reset cancelled")

    def manage_extensions(self):
        """Manage VS Code extensions."""
        print("📦 Extension Management")
        print("=" * 25)

        while True:
            print("\n📋 Extension Options:")
            print("1. Install Popular Extensions")
            print("2. Install Custom Extension")
            print("3. List Installed Extensions")
            print("4. Uninstall Extension")
            print("5. Update All Extensions")
            print("0. Back to Main Menu")

            choice = input("\n👉 Select option (0-5): ").strip()

            if choice == "1":
                self._install_popular_extensions()
            elif choice == "2":
                self._install_custom_extension()
            elif choice == "3":
                self._list_extensions()
            elif choice == "4":
                self._uninstall_extension()
            elif choice == "5":
                self._update_extensions()
            elif choice == "0":
                break
            else:
                print("❌ Invalid option")

    def _install_popular_extensions(self):
        """Install popular extensions."""
        print("\n📦 Installing Popular Extensions...")

        code_server_bin = BIN_DIR / "code-server"
        if not code_server_bin.exists():
            print("❌ Code Server not installed")
            return

        popular_extensions = self.config.get("extensions.popular", [])

        for ext in popular_extensions:
            print(f"📦 Installing {ext}...")
            success, output = SystemUtils.run_command([
                str(code_server_bin),
                "--install-extension", ext,
                "--force"
            ])

            if success:
                print(f"✅ {ext} installed")
            else:
                print(f"❌ Failed to install {ext}: {output}")

        print("✅ Popular extensions installation completed!")

    def _install_custom_extension(self):
        """Install a custom extension."""
        print("\n📦 Install Custom Extension")

        code_server_bin = BIN_DIR / "code-server"
        if not code_server_bin.exists():
            print("❌ Code Server not installed")
            return

        ext_id = input("Extension ID or VSIX path: ").strip()
        if not ext_id:
            return

        print(f"📦 Installing {ext_id}...")
        success, output = SystemUtils.run_command([
            str(code_server_bin),
            "--install-extension", ext_id,
            "--force"
        ])

        if success:
            print(f"✅ {ext_id} installed successfully!")
            # Add to custom extensions list
            custom = self.config.get("extensions.custom", [])
            if ext_id not in custom:
                custom.append(ext_id)
                self.config.set("extensions.custom", custom)
        else:
            print(f"❌ Failed to install {ext_id}: {output}")

    def _list_extensions(self):
        """List installed extensions."""
        print("\n📋 Installed Extensions")

        code_server_bin = BIN_DIR / "code-server"
        if not code_server_bin.exists():
            print("❌ Code Server not installed")
            return

        success, output = SystemUtils.run_command([
            str(code_server_bin),
            "--list-extensions"
        ])

        if success:
            extensions = output.strip().split('\n') if output.strip() else []
            if extensions:
                print(f"Found {len(extensions)} extensions:")
                for i, ext in enumerate(extensions, 1):
                    print(f"  {i}. {ext}")
            else:
                print("No extensions installed")
        else:
            print(f"❌ Failed to list extensions: {output}")

    def _uninstall_extension(self):
        """Uninstall an extension."""
        print("\n🗑️  Uninstall Extension")

        code_server_bin = BIN_DIR / "code-server"
        if not code_server_bin.exists():
            print("❌ Code Server not installed")
            return

        ext_id = input("Extension ID to uninstall: ").strip()
        if not ext_id:
            return

        print(f"🗑️  Uninstalling {ext_id}...")
        success, output = SystemUtils.run_command([
            str(code_server_bin),
            "--uninstall-extension", ext_id
        ])

        if success:
            print(f"✅ {ext_id} uninstalled successfully!")
            # Remove from custom extensions list
            custom = self.config.get("extensions.custom", [])
            if ext_id in custom:
                custom.remove(ext_id)
                self.config.set("extensions.custom", custom)
        else:
            print(f"❌ Failed to uninstall {ext_id}: {output}")

    def _update_extensions(self):
        """Update all extensions."""
        print("\n🔄 Updating All Extensions...")

        code_server_bin = BIN_DIR / "code-server"
        if not code_server_bin.exists():
            print("❌ Code Server not installed")
            return

        # Get list of installed extensions
        success, output = SystemUtils.run_command([
            str(code_server_bin),
            "--list-extensions"
        ])

        if not success:
            print(f"❌ Failed to get extension list: {output}")
            return

        extensions = output.strip().split('\n') if output.strip() else []
        if not extensions:
            print("No extensions to update")
            return

        print(f"Updating {len(extensions)} extensions...")
        for ext in extensions:
            print(f"🔄 Updating {ext}...")
            success, _ = SystemUtils.run_command([
                str(code_server_bin),
                "--install-extension", ext,
                "--force"
            ])

            if success:
                print(f"✅ {ext} updated")
            else:
                print(f"❌ Failed to update {ext}")

        print("✅ Extension updates completed!")

    def show_system_info(self):
        """Show detailed system information."""
        print("💻 System Information")
        print("=" * 30)

        info = self.system_info

        print(f"🖥️  Platform: {info['platform']}")
        print(f"🐍 Python: {info['python_version'].split()[0]}")
        print(f"📱 Google Colab: {'Yes' if info['is_colab'] else 'No'}")
        print(f"🏠 Home Directory: {info['home_dir']}")
        print(f"📁 Current Directory: {info['cwd']}")

        if PSUTIL_AVAILABLE:
            print(f"⚡ CPU Cores: {info.get('cpu_count', 'Unknown')}")
            memory_gb = info.get('memory_total', 0) // (1024**3)
            print(f"💾 Memory: {memory_gb} GB")
            disk_gb = info.get('disk_free', 0) // (1024**3)
            print(f"💿 Disk Free: {disk_gb} GB")

        # Installation paths
        print(f"\n📂 Installation Paths:")
        print(f"  Install Dir: {INSTALL_DIR}")
        print(f"  Binary Dir: {BIN_DIR}")
        print(f"  Config Dir: {CONFIG_DIR}")

        # Check dependencies
        print(f"\n📦 Dependencies:")
        deps = {
            "pyngrok": PYNGROK_AVAILABLE,
            "psutil": PSUTIL_AVAILABLE,
            "requests": True  # Always available as we import it
        }

        for dep, available in deps.items():
            status = "✅ Available" if available else "❌ Missing"
            print(f"  {dep}: {status}")

        # Environment variables
        print(f"\n🌍 Environment:")
        env_vars = ["PATH", "HOME", "USER", "SHELL"]
        for var in env_vars:
            value = os.environ.get(var, "Not set")
            if var == "PATH":
                # Show only relevant parts of PATH
                paths = value.split(":")
                relevant_paths = [p for p in paths if any(x in p for x in ["local", "bin", "code"])]
                if relevant_paths:
                    print(f"  {var}: {':'.join(relevant_paths[:3])}...")
                else:
                    print(f"  {var}: {paths[0]}...")
            else:
                print(f"  {var}: {value}")

    def view_logs(self):
        """View application logs."""
        print("📋 Application Logs")
        print("=" * 20)

        if not LOG_FILE.exists():
            print("No logs found")
            return

        try:
            with open(LOG_FILE, 'r') as f:
                lines = f.readlines()

            # Show last 50 lines
            recent_lines = lines[-50:] if len(lines) > 50 else lines

            print(f"Showing last {len(recent_lines)} log entries:")
            print("-" * 50)

            for line in recent_lines:
                print(line.rstrip())

            print("-" * 50)
            print(f"Full log file: {LOG_FILE}")

        except Exception as e:
            print(f"❌ Error reading logs: {e}")

def main():
    """Main application entry point."""
    print_banner()

    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Code Server Setup for Google Colab")
    parser.add_argument("--install", action="store_true", help="Install Code Server")
    parser.add_argument("--start", action="store_true", help="Start Code Server")
    parser.add_argument("--stop", action="store_true", help="Stop Code Server")
    parser.add_argument("--status", action="store_true", help="Show status")
    parser.add_argument("--config", action="store_true", help="Configure settings")
    parser.add_argument("--menu", action="store_true", default=True, help="Show interactive menu")

    args = parser.parse_args()

    # Initialize application
    app = CodeServerSetup()

    # Handle command line arguments
    if args.install:
        app.install_code_server()
    elif args.start:
        app.start_code_server()
    elif args.stop:
        app.stop_code_server()
    elif args.status:
        app.show_status()
    elif args.config:
        app.configure_settings()
    else:
        app.show_interactive_menu()

if __name__ == "__main__":
    main()

def main():
    """Main application entry point."""
    print_banner()
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Code Server Setup for Google Colab")
    parser.add_argument("--install", action="store_true", help="Install Code Server")
    parser.add_argument("--start", action="store_true", help="Start Code Server")
    parser.add_argument("--stop", action="store_true", help="Stop Code Server")
    parser.add_argument("--status", action="store_true", help="Show status")
    parser.add_argument("--config", action="store_true", help="Configure settings")
    parser.add_argument("--menu", action="store_true", default=True, help="Show interactive menu")
    
    args = parser.parse_args()
    
    # Initialize application
    app = CodeServerSetup()
    
    # Handle command line arguments
    if args.install:
        app.install_code_server()
    elif args.start:
        app.start_code_server()
    elif args.stop:
        app.stop_code_server()
    elif args.status:
        app.show_status()
    elif args.config:
        app.configure_settings()
    else:
        app.show_interactive_menu()

if __name__ == "__main__":
    main()
