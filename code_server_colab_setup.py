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
    ngrok = None
    conf = None
    PYNGROK_AVAILABLE = False

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

def _import_pyngrok():
    """Safely import pyngrok and update global variables."""
    global ngrok, conf, PYNGROK_AVAILABLE
    try:
        from pyngrok import ngrok, conf
        PYNGROK_AVAILABLE = True
        return True
    except ImportError:
        ngrok = None
        conf = None
        PYNGROK_AVAILABLE = False
        return False

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
        "custom": [],
        "microsoft_extensions": [
            "ms-python.python",
            "ms-python.vscode-pylance",
            "ms-toolsai.jupyter",
            "ms-vscode.vscode-json",
            "ms-vscode.theme-tomorrow-night-blue",
            "ms-vscode.vscode-typescript-next",
            "ms-vscode.cpptools",
            "ms-dotnettools.csharp",
            "ms-vscode.powershell"
        ],
        "fallback_registry": "https://open-vsx.org/vscode/gallery",
        "microsoft_marketplace": "https://marketplace.visualstudio.com/_apis/public/gallery"
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

class ExtensionManager:
    """Enhanced extension management with Microsoft Marketplace support."""

    def __init__(self, config_manager, logger):
        self.config = config_manager
        self.logger = logger
        self.microsoft_extensions = self.config.get("extensions.microsoft_extensions", [])
        self.fallback_registry = self.config.get("extensions.fallback_registry")
        self.microsoft_marketplace = self.config.get("extensions.microsoft_marketplace")

    def is_microsoft_extension(self, extension_id: str) -> bool:
        """Check if extension is from Microsoft."""
        return extension_id.startswith("ms-") or extension_id in self.microsoft_extensions

    def get_extension_info(self, extension_id: str) -> Optional[Dict]:
        """Get extension information from marketplace."""
        try:
            publisher, package = extension_id.split('.', 1)

            # Try Microsoft Marketplace first for Microsoft extensions
            if self.is_microsoft_extension(extension_id):
                return self._get_microsoft_extension_info(publisher, package)

            # Fallback to Open VSX for other extensions
            return self._get_openvsx_extension_info(extension_id)

        except Exception as e:
            self.logger.error(f"Failed to get extension info for {extension_id}: {e}")
            return None

    def _get_microsoft_extension_info(self, publisher: str, package: str) -> Optional[Dict]:
        """Get extension info from Microsoft Marketplace."""
        try:
            # Use the extensionquery API to get extension metadata
            query_url = f"{self.microsoft_marketplace}/extensionquery"

            payload = {
                "filters": [{
                    "criteria": [{
                        "filterType": 7,
                        "value": f"{publisher}.{package}"
                    }],
                    "pageNumber": 1,
                    "pageSize": 1,
                    "sortBy": 0,
                    "sortOrder": 0
                }],
                "assetTypes": [],
                "flags": 914
            }

            headers = {
                "Accept": "application/json;api-version=3.0-preview.1",
                "Content-Type": "application/json"
            }

            response = requests.post(query_url, json=payload, headers=headers, timeout=10)
            response.raise_for_status()

            data = response.json()
            if data.get("results") and data["results"][0].get("extensions"):
                extension = data["results"][0]["extensions"][0]
                versions = extension.get("versions", [])
                if versions:
                    latest_version = versions[0]
                    return {
                        "publisher": publisher,
                        "package": package,
                        "version": latest_version.get("version"),
                        "display_name": extension.get("displayName"),
                        "description": extension.get("shortDescription"),
                        "source": "microsoft"
                    }

            return None

        except Exception as e:
            self.logger.warning(f"Failed to get Microsoft extension info: {e}")
            return None

    def _get_openvsx_extension_info(self, extension_id: str) -> Optional[Dict]:
        """Get extension info from Open VSX Registry."""
        try:
            publisher, package = extension_id.split('.', 1)
            api_url = f"https://open-vsx.org/api/{publisher}/{package}"

            response = requests.get(api_url, timeout=10)
            response.raise_for_status()

            data = response.json()
            return {
                "publisher": publisher,
                "package": package,
                "version": data.get("version"),
                "display_name": data.get("displayName"),
                "description": data.get("description"),
                "source": "openvsx"
            }

        except Exception as e:
            self.logger.warning(f"Failed to get Open VSX extension info: {e}")
            return None

    def download_vsix(self, extension_id: str, target_dir: Path) -> Optional[Path]:
        """Download VSIX file for extension."""
        try:
            extension_info = self.get_extension_info(extension_id)
            if not extension_info:
                return None

            publisher = extension_info["publisher"]
            package = extension_info["package"]
            version = extension_info["version"]

            if extension_info["source"] == "microsoft":
                return self._download_microsoft_vsix(publisher, package, version, target_dir)
            else:
                return self._download_openvsx_vsix(publisher, package, version, target_dir)

        except Exception as e:
            self.logger.error(f"Failed to download VSIX for {extension_id}: {e}")
            return None

    def _download_microsoft_vsix(self, publisher: str, package: str, version: str, target_dir: Path) -> Optional[Path]:
        """Download VSIX from Microsoft Marketplace."""
        try:
            # Determine target platform
            import platform
            arch_map = {
                "x86_64": "win32-x64" if sys.platform == "win32" else "linux-x64",
                "aarch64": "linux-arm64",
                "armv7l": "linux-armhf"
            }
            target_platform = arch_map.get(platform.machine(), "universal")

            # Construct download URL
            base_url = f"{self.microsoft_marketplace}/publishers/{publisher}/vsextensions/{package}/{version}/vspackage"
            if target_platform != "universal":
                download_url = f"{base_url}?targetPlatform={target_platform}"
            else:
                download_url = base_url

            # Download VSIX file
            response = requests.get(download_url, stream=True, timeout=30)
            response.raise_for_status()

            # Save to file
            target_dir.mkdir(parents=True, exist_ok=True)
            vsix_path = target_dir / f"{publisher}.{package}-{version}.vsix"

            with open(vsix_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            self.logger.info(f"Downloaded VSIX: {vsix_path}")
            return vsix_path

        except Exception as e:
            self.logger.error(f"Failed to download Microsoft VSIX: {e}")
            return None

    def _download_openvsx_vsix(self, publisher: str, package: str, version: str, target_dir: Path) -> Optional[Path]:
        """Download VSIX from Open VSX Registry."""
        try:
            download_url = f"https://open-vsx.org/api/{publisher}/{package}/{version}/file/{publisher}.{package}-{version}.vsix"

            response = requests.get(download_url, stream=True, timeout=30)
            response.raise_for_status()

            target_dir.mkdir(parents=True, exist_ok=True)
            vsix_path = target_dir / f"{publisher}.{package}-{version}.vsix"

            with open(vsix_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            self.logger.info(f"Downloaded VSIX: {vsix_path}")
            return vsix_path

        except Exception as e:
            self.logger.error(f"Failed to download Open VSX VSIX: {e}")
            return None

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
        self.extension_manager = ExtensionManager(self.config, self.logger)

        # Ensure required directories exist
        INSTALL_DIR.mkdir(parents=True, exist_ok=True)
        BIN_DIR.mkdir(parents=True, exist_ok=True)

        # Create extensions cache directory
        self.extensions_cache_dir = Path.home() / ".cache" / "code-server-extensions"
        self.extensions_cache_dir.mkdir(parents=True, exist_ok=True)

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
                ("8", "� Extension Registry", self.configure_extension_registry),
                ("9", "�🌐 Setup Ngrok", self.setup_ngrok),
                ("10", "☁️ Setup Cloudflare Tunnel", self.setup_cloudflare_tunnel),
                ("11", "🔧 System Info", self.show_system_info),
                ("12", "📋 View Logs", self.view_logs),
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
            if self.ngrok_tunnel and ngrok is not None:
                print("🌐 Closing ngrok tunnel...")
                try:
                    ngrok.disconnect(self.ngrok_tunnel.public_url)
                except Exception as e:
                    self.logger.warning(f"Failed to disconnect ngrok tunnel: {e}")
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
                    if not _import_pyngrok():
                        print("❌ Failed to import pyngrok after installation")
                        return
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
                try:
                    ngrok.disconnect(test_tunnel.public_url)
                except Exception as disconnect_error:
                    self.logger.warning(f"Failed to disconnect test tunnel: {disconnect_error}")

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

            # Check if pyngrok is available
            if not PYNGROK_AVAILABLE or ngrok is None or conf is None:
                print("❌ Pyngrok not available. Please setup ngrok first.")
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
            print("💡 Try running 'Setup Ngrok' from the menu first.")

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
            print("6. Download Extension Info")
            print("7. Check Extension Compatibility")
            print("8. Clear Extension Cache")
            print("0. Back to Main Menu")

            choice = input("\n👉 Select option (0-8): ").strip()

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
            elif choice == "6":
                self._show_extension_info()
            elif choice == "7":
                self._check_extension_compatibility()
            elif choice == "8":
                self._clear_extension_cache()
            elif choice == "0":
                break
            else:
                print("❌ Invalid option")

    def _install_popular_extensions(self):
        """Install popular extensions with enhanced marketplace support."""
        print("\n📦 Installing Popular Extensions...")

        code_server_bin = BIN_DIR / "code-server"
        if not code_server_bin.exists():
            print("❌ Code Server not installed")
            return

        popular_extensions = self.config.get("extensions.popular", [])

        for ext in popular_extensions:
            print(f"📦 Installing {ext}...")

            # Try direct installation first
            success = self._install_extension_direct(ext)

            # If direct installation fails and it's a Microsoft extension, try VSIX
            if not success and self.extension_manager.is_microsoft_extension(ext):
                print(f"🔄 Direct installation failed, trying VSIX download for {ext}...")
                success = self._install_extension_via_vsix(ext)

            if success:
                print(f"✅ {ext} installed successfully")
            else:
                print(f"❌ Failed to install {ext}")

        print("✅ Popular extensions installation completed!")

    def _install_extension_direct(self, extension_id: str) -> bool:
        """Try to install extension directly via code-server."""
        try:
            code_server_bin = BIN_DIR / "code-server"
            success, output = SystemUtils.run_command([
                str(code_server_bin),
                "--install-extension", extension_id,
                "--force"
            ])
            return success
        except Exception as e:
            self.logger.warning(f"Direct installation failed for {extension_id}: {e}")
            return False

    def _install_extension_via_vsix(self, extension_id: str) -> bool:
        """Install extension via VSIX download."""
        try:
            # Download VSIX file
            vsix_path = self.extension_manager.download_vsix(extension_id, self.extensions_cache_dir)
            if not vsix_path or not vsix_path.exists():
                return False

            # Install from VSIX
            code_server_bin = BIN_DIR / "code-server"
            success, output = SystemUtils.run_command([
                str(code_server_bin),
                "--install-extension", str(vsix_path),
                "--force"
            ])

            if success:
                self.logger.info(f"Successfully installed {extension_id} from VSIX")
                # Clean up VSIX file after successful installation
                try:
                    vsix_path.unlink()
                except:
                    pass
                return True
            else:
                self.logger.error(f"Failed to install {extension_id} from VSIX: {output}")
                return False

        except Exception as e:
            self.logger.error(f"VSIX installation failed for {extension_id}: {e}")
            return False

    def _install_custom_extension(self):
        """Install a custom extension with enhanced support."""
        print("\n📦 Install Custom Extension")

        code_server_bin = BIN_DIR / "code-server"
        if not code_server_bin.exists():
            print("❌ Code Server not installed")
            return

        ext_id = input("Extension ID or VSIX path: ").strip()
        if not ext_id:
            return

        # Check if it's a file path (VSIX) or extension ID
        if ext_id.endswith('.vsix') and Path(ext_id).exists():
            # Direct VSIX installation
            print(f"📦 Installing from VSIX file: {ext_id}...")
            success, output = SystemUtils.run_command([
                str(code_server_bin),
                "--install-extension", ext_id,
                "--force"
            ])

            if success:
                print(f"✅ Extension installed successfully from VSIX!")
            else:
                print(f"❌ Failed to install from VSIX: {output}")
        else:
            # Extension ID - try enhanced installation
            print(f"📦 Installing {ext_id}...")

            # Show extension info if available
            ext_info = self.extension_manager.get_extension_info(ext_id)
            if ext_info:
                print(f"📋 Extension: {ext_info.get('display_name', ext_id)}")
                print(f"📝 Description: {ext_info.get('description', 'N/A')}")
                print(f"🏷️  Version: {ext_info.get('version', 'N/A')}")
                print(f"🏪 Source: {ext_info.get('source', 'N/A')}")
                print()

            # Try direct installation first
            success = self._install_extension_direct(ext_id)

            # If direct fails and it's Microsoft extension, try VSIX
            if not success and self.extension_manager.is_microsoft_extension(ext_id):
                print(f"🔄 Direct installation failed, trying VSIX download...")
                success = self._install_extension_via_vsix(ext_id)

            if success:
                print(f"✅ {ext_id} installed successfully!")
                # Add to custom extensions list
                custom = self.config.get("extensions.custom", [])
                if ext_id not in custom:
                    custom.append(ext_id)
                    self.config.set("extensions.custom", custom)
            else:
                print(f"❌ Failed to install {ext_id}")
                print("💡 Try downloading the VSIX file manually and install using the file path.")

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

    def _show_extension_info(self):
        """Show detailed information about an extension."""
        print("\n📋 Extension Information")

        ext_id = input("Extension ID: ").strip()
        if not ext_id:
            return

        print(f"🔍 Getting information for {ext_id}...")
        ext_info = self.extension_manager.get_extension_info(ext_id)

        if ext_info:
            print(f"\n📦 Extension Details:")
            print(f"  Name: {ext_info.get('display_name', 'N/A')}")
            print(f"  ID: {ext_info['publisher']}.{ext_info['package']}")
            print(f"  Version: {ext_info.get('version', 'N/A')}")
            print(f"  Description: {ext_info.get('description', 'N/A')}")
            print(f"  Source: {ext_info.get('source', 'N/A')}")

            if self.extension_manager.is_microsoft_extension(ext_id):
                print(f"  🏢 Microsoft Extension: Yes")
                print(f"  💡 Note: May require VSIX download for installation")
            else:
                print(f"  🏢 Microsoft Extension: No")
        else:
            print(f"❌ Could not find information for {ext_id}")
            print("💡 Extension may not exist or be available in the registries")

    def _check_extension_compatibility(self):
        """Check extension compatibility with current setup."""
        print("\n🔍 Extension Compatibility Check")

        ext_id = input("Extension ID: ").strip()
        if not ext_id:
            return

        print(f"🔍 Checking compatibility for {ext_id}...")

        # Check if extension info is available
        ext_info = self.extension_manager.get_extension_info(ext_id)
        if not ext_info:
            print(f"❌ Extension {ext_id} not found in registries")
            return

        print(f"✅ Extension found: {ext_info.get('display_name', ext_id)}")

        # Check source compatibility
        source = ext_info.get('source', 'unknown')
        if source == 'microsoft':
            print(f"🏢 Microsoft Extension - May require VSIX download")
            print(f"💡 Direct installation may fail, but VSIX fallback available")
        elif source == 'openvsx':
            print(f"🌐 Open VSX Extension - Should install directly")
        else:
            print(f"❓ Unknown source - Compatibility uncertain")

        # Check if already installed
        code_server_bin = BIN_DIR / "code-server"
        if code_server_bin.exists():
            success, output = SystemUtils.run_command([
                str(code_server_bin),
                "--list-extensions"
            ])

            if success and ext_id in output:
                print(f"✅ Extension is already installed")
            else:
                print(f"📦 Extension is not currently installed")
        else:
            print(f"❌ Code Server not installed - Cannot check installation status")

    def _clear_extension_cache(self):
        """Clear extension cache directory."""
        print("\n🧹 Clear Extension Cache")

        if not self.extensions_cache_dir.exists():
            print("ℹ️  No cache directory found")
            return

        try:
            cache_files = list(self.extensions_cache_dir.glob("*.vsix"))
            if not cache_files:
                print("ℹ️  Cache directory is already empty")
                return

            print(f"Found {len(cache_files)} cached VSIX files:")
            for file in cache_files:
                print(f"  - {file.name}")

            confirm = input("\nDelete all cached files? (y/N): ").strip().lower()
            if confirm == 'y':
                for file in cache_files:
                    file.unlink()
                print("✅ Extension cache cleared successfully!")
            else:
                print("❌ Cache clearing cancelled")

        except Exception as e:
            self.logger.error(f"Failed to clear cache: {e}")
            print(f"❌ Failed to clear cache: {e}")

    def configure_extension_registry(self):
        """Configure extension registry (Open VSX vs Microsoft Marketplace)."""
        print("\n🏪 Extension Registry Configuration")

        # Get current registry configuration
        current_registry = self._get_current_registry()
        print(f"📋 Current Registry: {current_registry}")

        print("\n📋 Available Registries:")
        print("1. Open VSX Registry (Default)")
        print("   - Open source extensions")
        print("   - Community maintained")
        print("   - No licensing restrictions")
        print()
        print("2. Microsoft Visual Studio Marketplace")
        print("   - Full Microsoft extension catalog")
        print("   - Includes proprietary extensions")
        print("   - May have licensing restrictions")
        print()
        print("3. Custom Registry")
        print("   - Use your own marketplace")
        print("   - Enterprise/private registries")
        print()
        print("4. Debug Current Configuration")
        print("   - Verify environment variables")
        print("   - Check Code Server process")
        print()
        print("5. Force Restart with Environment")
        print("   - Restart Code Server with current env vars")
        print("   - Fix registry not applying issue")
        print()
        print("0. Back to Main Menu")

        choice = input("\n👉 Select registry (0-5): ").strip()

        if choice == "1":
            self._configure_openvsx_registry()
        elif choice == "2":
            self._configure_microsoft_registry()
        elif choice == "3":
            self._configure_custom_registry()
        elif choice == "4":
            self._debug_registry_configuration()
        elif choice == "5":
            self._force_restart_with_env()
        elif choice == "0":
            return
        else:
            print("❌ Invalid option")

    def _get_current_registry(self) -> str:
        """Get current extension registry configuration."""
        try:
            extensions_gallery = os.environ.get('EXTENSIONS_GALLERY')
            if not extensions_gallery:
                return "Open VSX (Default)"

            import json
            config = json.loads(extensions_gallery)
            service_url = config.get('serviceUrl', '')

            if 'marketplace.visualstudio.com' in service_url:
                return "Microsoft Marketplace"
            elif 'open-vsx.org' in service_url:
                return "Open VSX"
            else:
                return f"Custom ({service_url})"

        except Exception:
            return "Open VSX (Default)"

    def _configure_openvsx_registry(self):
        """Configure Open VSX Registry."""
        print("\n🌐 Configuring Open VSX Registry...")

        # Remove EXTENSIONS_GALLERY environment variable to use default
        if 'EXTENSIONS_GALLERY' in os.environ:
            del os.environ['EXTENSIONS_GALLERY']

        # Update shell profile to remove EXTENSIONS_GALLERY
        self._update_shell_profile_registry(None)

        print("✅ Open VSX Registry configured successfully!")
        print("💡 This is the default registry - no special configuration needed")
        print("🔄 Code Server will use default Open VSX registry")

        restart = input("\n🔄 Restart Code Server now? (y/N): ").strip().lower()
        if restart == 'y':
            print("🔄 Restarting Code Server...")
            self._force_restart_with_env()

    def _configure_microsoft_registry(self):
        """Configure Microsoft Visual Studio Marketplace."""
        print("\n🏢 Configuring Microsoft Visual Studio Marketplace...")
        print("⚠️  Note: This may have licensing restrictions for commercial use")

        confirm = input("Continue? (y/N): ").strip().lower()
        if confirm != 'y':
            return

        # Microsoft Marketplace configuration
        extensions_gallery = {
            "serviceUrl": "https://marketplace.visualstudio.com/_apis/public/gallery",
            "itemUrl": "https://marketplace.visualstudio.com/items",
            "resourceUrlTemplate": "https://marketplace.visualstudio.com/_apis/public/gallery/publishers/{publisher}/vsextensions/{name}/{version}/vspackage"
        }

        import json
        gallery_json = json.dumps(extensions_gallery)

        # Set environment variable for current session
        os.environ['EXTENSIONS_GALLERY'] = gallery_json

        # Update shell profile for persistence
        self._update_shell_profile_registry(gallery_json)

        print("✅ Microsoft Marketplace configured successfully!")
        print("🔍 You can now search and install Microsoft extensions")
        print("🔄 Code Server needs restart with new environment variables")

        restart = input("\n🔄 Force restart Code Server now? (y/N): ").strip().lower()
        if restart == 'y':
            print("🔄 Using force restart to ensure environment variables are loaded...")
            self._force_restart_with_env()
        else:
            print("💡 Remember to use 'Force Restart with Environment' later!")
            print("   Menu: 8 → 5 (Force Restart with Environment)")

    def _configure_custom_registry(self):
        """Configure custom extension registry."""
        print("\n🔧 Configure Custom Registry")

        service_url = input("Service URL: ").strip()
        if not service_url:
            print("❌ Service URL is required")
            return

        item_url = input("Item URL: ").strip()
        if not item_url:
            print("❌ Item URL is required")
            return

        resource_template = input("Resource URL Template: ").strip()
        if not resource_template:
            print("❌ Resource URL Template is required")
            return

        # Custom registry configuration
        extensions_gallery = {
            "serviceUrl": service_url,
            "itemUrl": item_url,
            "resourceUrlTemplate": resource_template
        }

        import json
        gallery_json = json.dumps(extensions_gallery)

        # Set environment variable for current session
        os.environ['EXTENSIONS_GALLERY'] = gallery_json

        # Update shell profile for persistence
        self._update_shell_profile_registry(gallery_json)

        print("✅ Custom registry configured successfully!")
        print("🔄 Restart Code Server to apply changes")

        restart = input("\n🔄 Restart Code Server now? (y/N): ").strip().lower()
        if restart == 'y':
            self.restart_code_server()

    def _update_shell_profile_registry(self, gallery_json: str):
        """Update shell profile with EXTENSIONS_GALLERY configuration."""
        try:
            # Determine shell profile file
            shell_profile = None
            if os.path.exists(os.path.expanduser("~/.bashrc")):
                shell_profile = os.path.expanduser("~/.bashrc")
            elif os.path.exists(os.path.expanduser("~/.bash_profile")):
                shell_profile = os.path.expanduser("~/.bash_profile")
            elif os.path.exists(os.path.expanduser("~/.zshrc")):
                shell_profile = os.path.expanduser("~/.zshrc")

            if not shell_profile:
                self.logger.warning("No shell profile found")
                return

            # Read current profile
            with open(shell_profile, 'r') as f:
                lines = f.readlines()

            # Remove existing EXTENSIONS_GALLERY lines
            lines = [line for line in lines if 'EXTENSIONS_GALLERY' not in line]

            # Add new configuration if provided
            if gallery_json:
                lines.append(f'\nexport EXTENSIONS_GALLERY=\'{gallery_json}\'\n')

            # Write back to profile
            with open(shell_profile, 'w') as f:
                f.writelines(lines)

            self.logger.info(f"Updated shell profile: {shell_profile}")

        except Exception as e:
            self.logger.error(f"Failed to update shell profile: {e}")
            print(f"⚠️  Warning: Could not update shell profile: {e}")
            print("💡 You may need to set EXTENSIONS_GALLERY manually")

    def _debug_registry_configuration(self):
        """Debug extension registry configuration."""
        # Clear terminal to avoid control character issues
        self._clear_terminal()

        print("\n🔍 Debug Extension Registry Configuration")

        # Disable terminal control characters that might cause issues
        import sys
        sys.stdout.flush()
        sys.stderr.flush()

        # Check current environment variable
        print("📋 Environment Variable Check:")
        extensions_gallery = os.environ.get('EXTENSIONS_GALLERY')
        if extensions_gallery:
            print("✅ EXTENSIONS_GALLERY is set:")
            print(f"   {extensions_gallery}")

            try:
                import json
                config = json.loads(extensions_gallery)
                service_url = config.get('serviceUrl', '')
                if 'marketplace.visualstudio.com' in service_url:
                    print("✅ Microsoft Marketplace is configured")
                elif 'open-vsx.org' in service_url:
                    print("ℹ️  Open VSX Registry is configured")
                else:
                    print(f"ℹ️  Custom registry: {service_url}")
            except json.JSONDecodeError:
                print("❌ Invalid JSON in EXTENSIONS_GALLERY")
        else:
            print("❌ EXTENSIONS_GALLERY is not set (using default Open VSX)")

        # Check shell profile
        print("\n📋 Shell Profile Check:")
        shell_profiles = [
            os.path.expanduser("~/.bashrc"),
            os.path.expanduser("~/.bash_profile"),
            os.path.expanduser("~/.zshrc")
        ]

        found_in_profile = False
        for profile in shell_profiles:
            if os.path.exists(profile):
                try:
                    with open(profile, 'r') as f:
                        content = f.read()
                        if 'EXTENSIONS_GALLERY' in content:
                            print(f"✅ Found EXTENSIONS_GALLERY in {profile}")
                            # Extract the line
                            for line in content.split('\n'):
                                if 'EXTENSIONS_GALLERY' in line:
                                    print(f"   {line.strip()}")
                            found_in_profile = True
                        else:
                            print(f"ℹ️  {profile} exists but no EXTENSIONS_GALLERY found")
                except Exception as e:
                    print(f"❌ Error reading {profile}: {e}")
            else:
                print(f"ℹ️  {profile} does not exist")

        if not found_in_profile:
            print("❌ EXTENSIONS_GALLERY not found in any shell profile")

        # Check Code Server process
        print("\n📋 Code Server Process Check:")
        if self._is_code_server_running():
            print("✅ Code Server is running")

            # Try to get process environment
            try:
                import psutil
                code_server_proc = None
                for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                    if proc.info['name'] == 'code-server' or (
                        proc.info['cmdline'] and 'code-server' in ' '.join(proc.info['cmdline'])
                    ):
                        code_server_proc = proc
                        print(f"🆔 Process ID: {proc.info['pid']}")
                        try:
                            env = proc.environ()
                            if 'EXTENSIONS_GALLERY' in env:
                                proc_gallery = env['EXTENSIONS_GALLERY']
                                print("✅ Code Server process has EXTENSIONS_GALLERY:")
                                print(f"   {proc_gallery}")

                                # Check if it matches current environment
                                if proc_gallery != extensions_gallery:
                                    print("❌ MISMATCH DETECTED!")
                                    print("   Code Server process is using OLD environment variable")
                                    print("   Current environment has been updated but process hasn't")
                                    print("💡 SOLUTION: Code Server needs restart to pick up new environment")
                                else:
                                    print("✅ Environment variables match - configuration is correct")
                            else:
                                print("❌ Code Server process does NOT have EXTENSIONS_GALLERY")
                                print("💡 This is why Microsoft Marketplace is not working!")
                        except (psutil.AccessDenied, psutil.NoSuchProcess):
                            print("⚠️  Cannot access process environment (permission denied)")
                        break
                else:
                    print("❌ Code Server process not found")

                # If we found a mismatch, offer immediate fix
                if (code_server_proc and extensions_gallery and
                    'EXTENSIONS_GALLERY' in code_server_proc.environ() and
                    code_server_proc.environ()['EXTENSIONS_GALLERY'] != extensions_gallery):

                    print("\n🚨 IMMEDIATE FIX AVAILABLE!")
                    fix_now = input("🔄 Restart Code Server now to fix registry? (y/N): ").strip().lower()
                    if fix_now == 'y':
                        print("🔄 Restarting Code Server with correct environment...")
                        self._force_restart_with_env()
                        return

            except ImportError:
                print("⚠️  psutil not available - cannot check process environment")
        else:
            print("❌ Code Server is not running")

        # Provide solutions
        print("\n💡 Solutions:")
        if not extensions_gallery:
            print("1. Run option 2 (Microsoft Marketplace) to set EXTENSIONS_GALLERY")

        if not found_in_profile:
            print("2. EXTENSIONS_GALLERY not persistent - will be lost on restart")
            print("   Re-run option 2 to update shell profile")

        if self._is_code_server_running():
            print("3. Code Server needs restart to pick up new environment variables")
            print("   Use option 4 (Restart Code Server) after configuring registry")

        print("\n🔧 Quick Fix:")
        print("1. Stop Code Server (option 3)")
        print("2. Configure Microsoft Marketplace (option 8 → 2)")
        print("3. Start Code Server (option 2)")
        print("4. Verify extensions are now from Microsoft Marketplace")

    def _force_restart_with_env(self):
        """Force restart Code Server with current environment variables."""
        # Clear terminal to avoid control character issues
        self._clear_terminal()

        print("\n🔄 Force Restart with Environment Variables")

        # Get current EXTENSIONS_GALLERY before restart
        extensions_gallery = os.environ.get('EXTENSIONS_GALLERY')
        if not extensions_gallery:
            print("❌ No EXTENSIONS_GALLERY environment variable found!")
            print("💡 Please configure registry first (option 2 for Microsoft Marketplace)")
            return

        print(f"🏪 Target registry: {self._get_current_registry()}")
        print(f"📋 Environment variable: {extensions_gallery[:100]}...")

        if self._is_code_server_running():
            print("⏹️  Stopping Code Server...")
            self.stop_code_server()

            # Wait for complete shutdown
            import time
            print("⏳ Waiting for complete shutdown...")
            time.sleep(3)

            # Verify it's actually stopped
            if self._is_code_server_running():
                print("⚠️  Code Server still running, forcing kill...")
                self._force_kill_code_server()
                time.sleep(2)

        print("▶️  Starting Code Server with current environment...")

        # Get Code Server configuration
        port = self.config.get("code_server.port", 8080)
        password = self.config.get("code_server.password", "colab123")

        # Prepare environment with EXTENSIONS_GALLERY and PASSWORD
        env = os.environ.copy()
        env['EXTENSIONS_GALLERY'] = extensions_gallery
        env['PASSWORD'] = password  # Use environment variable instead of --password

        # Start Code Server with explicit environment
        try:
            # Use same approach as regular start_code_server but with custom environment
            code_server_bin = BIN_DIR / "code-server"

            print(f"🚀 Starting Code Server with Microsoft Marketplace environment...")

            # Start in background (similar to regular start_code_server)
            process = subprocess.Popen(
                [str(code_server_bin)],
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                start_new_session=True
            )

            # Store process info
            self.code_server_process = process

            # Wait a moment for startup
            import time
            time.sleep(5)

            # Verify it started successfully
            if self._is_code_server_running():
                print("✅ Code Server restarted successfully!")

                # Verify environment variable is loaded
                print("🔍 Verifying environment variable...")
                try:
                    import psutil
                    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                        if proc.info['name'] == 'code-server' or (
                            proc.info['cmdline'] and 'code-server' in ' '.join(proc.info['cmdline'])
                        ):
                            try:
                                proc_env = proc.environ()
                                if 'EXTENSIONS_GALLERY' in proc_env:
                                    if 'marketplace.visualstudio.com' in proc_env['EXTENSIONS_GALLERY']:
                                        print("✅ Microsoft Marketplace is active in Code Server process!")
                                    else:
                                        print("⚠️  Different registry detected in process")
                                else:
                                    print("❌ EXTENSIONS_GALLERY not found in process environment")
                                break
                            except (psutil.AccessDenied, psutil.NoSuchProcess):
                                print("⚠️  Cannot verify process environment")
                                break
                except ImportError:
                    print("⚠️  Cannot verify process environment (psutil not available)")

                print("\n🎯 Next Steps:")
                print("1. 🌐 Open Code Server in browser")
                print("2. 🔍 Go to Extensions tab (Ctrl+Shift+X)")
                print("3. 🔎 Search for 'augment.vscode-augment'")
                print("4. ✅ Extension should now appear from Microsoft Marketplace!")

            else:
                print("❌ Failed to start Code Server")
                if process.poll() is not None:
                    stdout, stderr = process.communicate()
                    print(f"Error: {stderr.decode()}")

        except Exception as e:
            print(f"❌ Failed to restart Code Server: {e}")

    def _force_kill_code_server(self):
        """Force kill Code Server process."""
        try:
            import psutil
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                if proc.info['name'] == 'code-server' or (
                    proc.info['cmdline'] and 'code-server' in ' '.join(proc.info['cmdline'])
                ):
                    print(f"🔪 Force killing process {proc.info['pid']}")
                    proc.kill()
                    break
        except ImportError:
            # Fallback to pkill
            import subprocess
            subprocess.run(["pkill", "-f", "code-server"], capture_output=True)

    def _clear_terminal(self):
        """Clear terminal and reset to avoid control character issues."""
        try:
            import os
            # Clear screen
            os.system('clear' if os.name == 'posix' else 'cls')
            # Reset terminal
            print('\033[0m', end='')  # Reset all formatting
            print('\033[2J', end='')  # Clear screen
            print('\033[H', end='')   # Move cursor to home
            import sys
            sys.stdout.flush()
        except Exception:
            # If clearing fails, just continue
            pass

    def setup_cloudflare_tunnel(self):
        """Setup Cloudflare Tunnel for Code Server."""
        print("\n☁️ Cloudflare Tunnel Setup")

        print("📋 Cloudflare Tunnel Options:")
        print("1. Install Cloudflared")
        print("2. Login to Cloudflare")
        print("3. Create New Tunnel")
        print("4. Configure Tunnel")
        print("5. Start Tunnel")
        print("6. Stop Tunnel")
        print("7. Quick Setup (TryCloudflare)")
        print("8. Verify Current Configuration")
        print("0. Back to Main Menu")

        choice = input("\n👉 Select option (0-8): ").strip()

        if choice == "1":
            self._install_cloudflared()
        elif choice == "2":
            self._cloudflare_login()
        elif choice == "3":
            self._create_cloudflare_tunnel()
        elif choice == "4":
            self._configure_cloudflare_tunnel()
        elif choice == "5":
            self._start_cloudflare_tunnel()
        elif choice == "6":
            self._stop_cloudflare_tunnel()
        elif choice == "7":
            self._quick_cloudflare_setup()
        elif choice == "8":
            self._verify_cloudflare_config()
        elif choice == "0":
            return
        else:
            print("❌ Invalid option")

    def _install_cloudflared(self):
        """Install Cloudflared binary."""
        print("\n📦 Installing Cloudflared...")

        try:
            # Check if already installed
            result = subprocess.run(["cloudflared", "--version"],
                                  capture_output=True, text=True)
            if result.returncode == 0:
                print(f"✅ Cloudflared already installed: {result.stdout.strip()}")
                return
        except FileNotFoundError:
            pass

        # Determine architecture and OS
        import platform
        system = platform.system().lower()
        machine = platform.machine().lower()

        arch_map = {
            "x86_64": "amd64",
            "aarch64": "arm64",
            "armv7l": "arm"
        }
        arch = arch_map.get(machine, "amd64")

        if system == "linux":
            # Download and install for Linux
            download_url = f"https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-{arch}"

            print(f"📥 Downloading cloudflared for {system}-{arch}...")
            success, output = SystemUtils.run_command([
                "curl", "-L", download_url, "-o", "/tmp/cloudflared"
            ])

            if not success:
                print(f"❌ Failed to download cloudflared: {output}")
                return

            # Make executable and move to bin
            SystemUtils.run_command(["chmod", "+x", "/tmp/cloudflared"])
            success, output = SystemUtils.run_command([
                "sudo", "mv", "/tmp/cloudflared", "/usr/local/bin/cloudflared"
            ])

            if success:
                print("✅ Cloudflared installed successfully!")
                # Verify installation
                result = subprocess.run(["cloudflared", "--version"],
                                      capture_output=True, text=True)
                if result.returncode == 0:
                    print(f"📋 Version: {result.stdout.strip()}")
            else:
                print(f"❌ Failed to install cloudflared: {output}")

        else:
            print(f"❌ Unsupported system: {system}")
            print("💡 Please install cloudflared manually from:")
            print("   https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/installation")

    def _cloudflare_login(self):
        """Login to Cloudflare account."""
        print("\n🔐 Cloudflare Login")

        print("📋 Login Options:")
        print("1. Browser Login (Recommended)")
        print("2. API Token Login")
        print("0. Back")

        choice = input("\n👉 Select option (0-2): ").strip()

        if choice == "1":
            print("🌐 Opening browser for Cloudflare login...")
            success, output = SystemUtils.run_command(["cloudflared", "tunnel", "login"])

            if success:
                print("✅ Login successful!")
                print("📋 Certificate saved to ~/.cloudflared/cert.pem")
            else:
                print(f"❌ Login failed: {output}")

        elif choice == "2":
            api_token = input("Enter your Cloudflare API Token: ").strip()
            if api_token:
                # Set environment variable
                os.environ['CLOUDFLARE_API_TOKEN'] = api_token
                print("✅ API Token configured!")
                print("💡 Token will be used for this session")
            else:
                print("❌ No API token provided")

    def _create_cloudflare_tunnel(self):
        """Create a new Cloudflare tunnel."""
        print("\n🚇 Create Cloudflare Tunnel")

        tunnel_name = input("Enter tunnel name: ").strip()
        if not tunnel_name:
            print("❌ Tunnel name is required")
            return

        print(f"🚇 Creating tunnel: {tunnel_name}...")
        success, output = SystemUtils.run_command([
            "cloudflared", "tunnel", "create", tunnel_name
        ])

        if success:
            print("✅ Tunnel created successfully!")
            print(f"📋 Output: {output}")

            # Extract tunnel ID from output
            import re
            tunnel_id_match = re.search(r'([a-f0-9-]{36})', output)
            if tunnel_id_match:
                tunnel_id = tunnel_id_match.group(1)
                print(f"🆔 Tunnel ID: {tunnel_id}")

                # Save tunnel info to config
                self.config.set("cloudflare.tunnel_name", tunnel_name)
                self.config.set("cloudflare.tunnel_id", tunnel_id)
        else:
            print(f"❌ Failed to create tunnel: {output}")

    def _configure_cloudflare_tunnel(self):
        """Configure Cloudflare tunnel."""
        print("\n⚙️ Configure Cloudflare Tunnel")

        tunnel_name = self.config.get("cloudflare.tunnel_name")
        tunnel_id = self.config.get("cloudflare.tunnel_id")

        if not tunnel_name or not tunnel_id:
            print("❌ No tunnel found. Please create a tunnel first.")
            return

        print(f"🚇 Configuring tunnel: {tunnel_name} ({tunnel_id})")

        # Get Code Server port
        port = self.config.get("code_server.port", 8080)

        # Create config file
        config_dir = Path.home() / ".cloudflared"
        config_dir.mkdir(exist_ok=True)
        config_file = config_dir / "config.yml"

        config_content = f"""tunnel: {tunnel_id}
credentials-file: {config_dir}/{tunnel_id}.json

ingress:
  - service: http://localhost:{port}
"""

        with open(config_file, 'w') as f:
            f.write(config_content)

        print(f"✅ Configuration saved to: {config_file}")
        print("📋 Configuration:")
        print(config_content)

    def _start_cloudflare_tunnel(self):
        """Start Cloudflare tunnel."""
        print("\n▶️ Start Cloudflare Tunnel")

        tunnel_name = self.config.get("cloudflare.tunnel_name")
        if not tunnel_name:
            print("❌ No tunnel configured. Please create and configure a tunnel first.")
            return

        print(f"🚇 Starting tunnel: {tunnel_name}...")

        # Start tunnel in background
        try:
            process = subprocess.Popen([
                "cloudflared", "tunnel", "run", tunnel_name
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            # Store process info
            self.config.set("cloudflare.process_pid", process.pid)

            print("✅ Tunnel started successfully!")
            print(f"🆔 Process ID: {process.pid}")
            print("💡 Tunnel is running in the background")

        except Exception as e:
            print(f"❌ Failed to start tunnel: {e}")

    def _stop_cloudflare_tunnel(self):
        """Stop Cloudflare tunnel."""
        print("\n⏹️ Stop Cloudflare Tunnel")

        pid = self.config.get("cloudflare.process_pid")
        if pid:
            try:
                import signal
                os.kill(pid, signal.SIGTERM)
                print("✅ Tunnel stopped successfully!")
                self.config.set("cloudflare.process_pid", None)
            except ProcessLookupError:
                print("ℹ️ Tunnel process not found (may already be stopped)")
                self.config.set("cloudflare.process_pid", None)
            except Exception as e:
                print(f"❌ Failed to stop tunnel: {e}")
        else:
            print("ℹ️ No tunnel process found")

    def _quick_cloudflare_setup(self):
        """Quick setup using TryCloudflare."""
        print("\n⚡ Quick Cloudflare Setup (TryCloudflare)")
        print("💡 This creates a temporary tunnel without requiring a Cloudflare account")

        # Get Code Server port
        port = self.config.get("code_server.port", 8080)

        print(f"🚇 Creating temporary tunnel for localhost:{port}...")

        try:
            # Start TryCloudflare tunnel
            process = subprocess.Popen([
                "cloudflared", "tunnel", "--url", f"http://localhost:{port}"
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

            # Wait a bit for tunnel to establish
            import time
            time.sleep(3)

            # Try to get the URL from output
            if process.poll() is None:  # Process is still running
                print("✅ Temporary tunnel started!")
                print(f"🆔 Process ID: {process.pid}")
                print("🌐 Check the terminal output for the tunnel URL")
                print("💡 The URL will be something like: https://xxx.trycloudflare.com")

                # Store process info
                self.config.set("cloudflare.temp_process_pid", process.pid)
            else:
                stdout, stderr = process.communicate()
                print(f"❌ Failed to start tunnel: {stderr}")

        except Exception as e:
            print(f"❌ Failed to start temporary tunnel: {e}")

    def _verify_cloudflare_config(self):
        """Verify Cloudflare configuration."""
        print("\n🔍 Verify Cloudflare Configuration")

        # Check if cloudflared is installed
        try:
            result = subprocess.run(["cloudflared", "--version"],
                                  capture_output=True, text=True)
            if result.returncode == 0:
                print(f"✅ Cloudflared installed: {result.stdout.strip()}")
            else:
                print("❌ Cloudflared not installed")
                return
        except FileNotFoundError:
            print("❌ Cloudflared not found")
            return

        # Check authentication
        cert_file = Path.home() / ".cloudflared" / "cert.pem"
        if cert_file.exists():
            print("✅ Cloudflare certificate found")
        else:
            print("❌ Cloudflare certificate not found (not logged in)")

        # Check tunnel configuration
        tunnel_name = self.config.get("cloudflare.tunnel_name")
        tunnel_id = self.config.get("cloudflare.tunnel_id")

        if tunnel_name and tunnel_id:
            print(f"✅ Tunnel configured: {tunnel_name} ({tunnel_id})")

            # Check config file
            config_file = Path.home() / ".cloudflared" / "config.yml"
            if config_file.exists():
                print(f"✅ Configuration file found: {config_file}")
            else:
                print("❌ Configuration file not found")
        else:
            print("❌ No tunnel configured")

        # Check if tunnel is running
        pid = self.config.get("cloudflare.process_pid")
        temp_pid = self.config.get("cloudflare.temp_process_pid")

        if pid:
            try:
                os.kill(pid, 0)  # Check if process exists
                print(f"✅ Tunnel running (PID: {pid})")
            except ProcessLookupError:
                print("❌ Tunnel process not found")
                self.config.set("cloudflare.process_pid", None)
        elif temp_pid:
            try:
                os.kill(temp_pid, 0)
                print(f"✅ Temporary tunnel running (PID: {temp_pid})")
            except ProcessLookupError:
                print("❌ Temporary tunnel process not found")
                self.config.set("cloudflare.temp_process_pid", None)
        else:
            print("ℹ️ No tunnel process running")

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
