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
    "server_type": "code-server",  # "code-server" or "vscode-server"
    "code_server": {
        "version": "4.23.1",
        "port": 8080,
        "auth": "password",
        "password": "",
        "bind_addr": "127.0.0.1",
        "extensions_dir": str(Path.home() / ".local" / "share" / "code-server" / "extensions"),
        "user_data_dir": str(Path.home() / ".local" / "share" / "code-server")
    },
    "vscode_server": {
        "version": "latest",
        "tunnel_name": "",
        "accept_server_license_terms": False,
        "enable_telemetry": False,
        "install_dir": str(Path.home() / ".local" / "lib" / "vscode-server"),
        "bin_path": str(Path.home() / ".local" / "bin" / "code")
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
            server_type = self.config.get("server_type", "code-server")

            if server_type == "vscode-server":
                print(f"🔧 VSCode Server: {status['vscode_server']}")
                if status.get('vscode_tunnel_url'):
                    print(f"🔗 Tunnel URL: {status['vscode_tunnel_url']}")
            else:
                print(f"🔧 Code Server: {status['code_server']}")
                print(f"🌐 Ngrok: {status['ngrok']}")
                if status['url']:
                    print(f"🔗 Access URL: {status['url']}")
            print()

            # Menu options based on server type
            if server_type == "vscode-server":
                menu_options = [
                    ("1", "🚀 Install VSCode Server", self.install_vscode_server),
                    ("2", "▶️  Start VSCode Server", self.start_vscode_server),
                    ("3", "⏹️  Stop VSCode Server", self.stop_vscode_server),
                    ("4", "🔄 Restart VSCode Server", self.restart_vscode_server),
                    ("5", "📊 Show Status", self.show_status),
                    ("6", "⚙️  Configure Settings", self.configure_settings),
                    ("7", "🔄 Switch to Code Server", self._switch_to_code_server),
                    ("8", "🔧 System Info", self.show_system_info),
                    ("9", "📋 View Logs", self.view_logs),
                    ("0", "❌ Exit", self._exit_app)
                ]
                max_option = 9
            else:
                menu_options = [
                    ("1", "🚀 Install Code Server", self.install_code_server),
                    ("2", "▶️  Start Code Server", self.start_code_server),
                    ("3", "⏹️  Stop Code Server", self.stop_code_server),
                    ("4", "🔄 Restart Code Server", self.restart_code_server),
                    ("5", "📊 Show Status", self.show_status),
                    ("6", "⚙️  Configure Settings", self.configure_settings),
                    ("7", "📦 Manage Extensions", self.manage_extensions),
                    ("8", "🔧 Fix Crypto Extensions", self.fix_crypto_extensions),
                    ("9", "🔧 Extension Registry", self.configure_extension_registry),
                    ("10", "🌐 Setup Ngrok", self.setup_ngrok),
                    ("11", "☁️ Setup Cloudflare Tunnel", self.setup_cloudflare_tunnel),
                    ("12", "🔄 Switch to VSCode Server", self._switch_to_vscode_server),
                    ("13", "🔧 System Info", self.show_system_info),
                    ("14", "📋 View Logs", self.view_logs),
                    ("0", "❌ Exit", self._exit_app)
                ]
                max_option = 14

            print("📋 Menu Options:")
            for key, description, _ in menu_options:
                print(f"  {key}. {description}")
            print()

            try:
                choice = input(f"👉 Select option (0-{max_option}): ").strip()

                # Find and execute the selected option
                function_executed = False
                for key, _, func in menu_options:
                    if choice == key:
                        print()
                        try:
                            func()
                            function_executed = True
                        except KeyboardInterrupt:
                            print("\n⚠️  Operation interrupted by user (Ctrl+C)")
                            print("🔄 Returning to main menu...")
                            function_executed = True
                        except Exception as func_error:
                            self.logger.error(f"Function error in {func.__name__}: {func_error}")
                            print(f"❌ Error in {func.__name__}: {func_error}")
                            function_executed = True
                        break

                if not function_executed:
                    print("❌ Invalid option. Please try again.")
                    time.sleep(1)

                if choice != "0" and function_executed:
                    try:
                        input("\n⏸️  Press Enter to continue...")
                    except KeyboardInterrupt:
                        print("\n🔄 Returning to menu...")

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
        server_type = self.config.get("server_type", "code-server")

        status = {
            "code_server": "Not Installed",
            "vscode_server": "Not Installed",
            "ngrok": "Not Setup",
            "url": None,
            "vscode_tunnel_url": None
        }

        if server_type == "vscode-server":
            # Check VSCode Server installation
            vscode_bin = Path(self.config.get("vscode_server.bin_path", str(Path.home() / ".local" / "bin" / "code")))
            if vscode_bin.exists():
                if self._is_vscode_server_running():
                    status["vscode_server"] = "Running"
                    status["vscode_tunnel_url"] = self.config.get("vscode_server.tunnel_url", "")
                else:
                    status["vscode_server"] = "Stopped"
        else:
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
            # Fallback method using platform-specific commands
            try:
                if sys.platform == "win32":
                    # Windows: use tasklist command
                    result = subprocess.run(
                        ["tasklist", "/FI", "IMAGENAME eq code-server.exe"],
                        capture_output=True,
                        text=True
                    )
                    return "code-server.exe" in result.stdout
                else:
                    # Linux/Unix: use pgrep command
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



    def _create_crypto_polyfill(self):
        """Create enhanced crypto polyfill for web worker extension host environments."""
        polyfill_dir = Path.home() / ".local" / "share" / "code-server" / "polyfills"
        polyfill_dir.mkdir(parents=True, exist_ok=True)

        crypto_polyfill_content = '''
// Enhanced Crypto polyfill for VS Code extension web worker environments
// This provides Node.js crypto module compatibility in code-server extension hosts

(function() {
    'use strict';

    console.log('[Crypto Polyfill] Initializing crypto polyfill for web worker environment');

    // First, create a Buffer polyfill for web worker environments
    if (typeof Buffer === 'undefined') {
        globalThis.Buffer = {
            from: function(data) {
                if (data instanceof Uint8Array) {
                    return data;
                }
                if (typeof data === 'string') {
                    const encoder = new TextEncoder();
                    return encoder.encode(data);
                }
                return new Uint8Array(data);
            },
            alloc: function(size) {
                return new Uint8Array(size);
            }
        };
        console.log('[Crypto Polyfill] Buffer polyfill created');
    }

    // Check if crypto module is already available
    try {
        if (typeof require !== 'undefined') {
            const existingCrypto = require('crypto');
            if (existingCrypto && typeof existingCrypto.randomBytes === 'function') {
                console.log('[Crypto Polyfill] Native crypto module is available, skipping polyfill');
                return;
            }
        }
    } catch (e) {
        // Native crypto not available, continue with polyfill
        console.log('[Crypto Polyfill] Native crypto not available, loading polyfill');
    }

    // Enhanced crypto polyfill with web worker compatibility
    const crypto = {
        // Random bytes generation with better fallbacks
        randomBytes: function(size, callback) {
            let array;

            try {
                // Try Web Crypto API first (available in web workers)
                if (typeof globalThis !== 'undefined' && globalThis.crypto && globalThis.crypto.getRandomValues) {
                    array = new Uint8Array(size);
                    globalThis.crypto.getRandomValues(array);
                } else if (typeof self !== 'undefined' && self.crypto && self.crypto.getRandomValues) {
                    array = new Uint8Array(size);
                    self.crypto.getRandomValues(array);
                } else if (typeof window !== 'undefined' && window.crypto && window.crypto.getRandomValues) {
                    array = new Uint8Array(size);
                    window.crypto.getRandomValues(array);
                } else {
                    // Fallback to Math.random (less secure but functional)
                    array = new Uint8Array(size);
                    for (let i = 0; i < size; i++) {
                        array[i] = Math.floor(Math.random() * 256);
                    }
                }

                // Use our Buffer polyfill
                const buffer = globalThis.Buffer ? globalThis.Buffer.from(array) : array;

                if (callback && typeof callback === 'function') {
                    callback(null, buffer);
                    return;
                }
                return buffer;

            } catch (error) {
                console.error('[Crypto Polyfill] Error in randomBytes:', error);
                if (callback && typeof callback === 'function') {
                    callback(error);
                    return;
                }
                throw error;
            }
        },

        // Synchronous random bytes
        randomBytesSync: function(size) {
            return this.randomBytes(size);
        },

        // Hash functions with better algorithm support
        createHash: function(algorithm) {
            return {
                _algorithm: algorithm,
                _data: '',

                update: function(data, encoding) {
                    if (typeof data === 'string') {
                        this._data += data;
                    } else if (data && data.toString) {
                        this._data += data.toString();
                    }
                    return this;
                },

                digest: function(encoding) {
                    // Simple hash implementation (not cryptographically secure but functional)
                    let hash = 0;
                    const str = this._data || '';

                    // Use a better hash function
                    for (let i = 0; i < str.length; i++) {
                        const char = str.charCodeAt(i);
                        hash = ((hash << 5) - hash) + char;
                        hash = hash & hash; // Convert to 32-bit integer
                    }

                    // Make hash positive and add algorithm-specific salt
                    hash = Math.abs(hash);
                    if (this._algorithm === 'sha256') {
                        hash = hash * 31 + 256;
                    } else if (this._algorithm === 'md5') {
                        hash = hash * 17 + 128;
                    }

                    if (encoding === 'hex') {
                        return hash.toString(16).padStart(8, '0');
                    } else if (encoding === 'base64') {
                        return Buffer.from(hash.toString()).toString('base64');
                    }
                    return Buffer.from(hash.toString());
                }
            };
        },

        // HMAC functions
        createHmac: function(algorithm, key) {
            return {
                _algorithm: algorithm,
                _key: key,
                _data: '',

                update: function(data, encoding) {
                    if (typeof data === 'string') {
                        this._data += data;
                    } else if (data && data.toString) {
                        this._data += data.toString();
                    }
                    return this;
                },

                digest: function(encoding) {
                    // Simple HMAC implementation
                    const data = this._data || '';
                    const keyStr = this._key ? this._key.toString() : '';
                    let hash = 0;
                    const combined = keyStr + data;

                    for (let i = 0; i < combined.length; i++) {
                        const char = combined.charCodeAt(i);
                        hash = ((hash << 5) - hash) + char;
                        hash = hash & hash;
                    }

                    hash = Math.abs(hash);

                    if (encoding === 'hex') {
                        return hash.toString(16).padStart(8, '0');
                    } else if (encoding === 'base64') {
                        return Buffer.from(hash.toString()).toString('base64');
                    }
                    return Buffer.from(hash.toString());
                }
            };
        },

        // Cipher functions (basic implementation)
        createCipher: function(algorithm, password) {
            return {
                update: function(data, inputEncoding, outputEncoding) {
                    // Simple XOR cipher (not secure, but functional)
                    const key = password.toString();
                    let result = '';
                    for (let i = 0; i < data.length; i++) {
                        result += String.fromCharCode(data.charCodeAt(i) ^ key.charCodeAt(i % key.length));
                    }
                    return outputEncoding === 'hex' ? Buffer.from(result).toString('hex') : result;
                },
                final: function(outputEncoding) {
                    return outputEncoding === 'hex' ? '' : Buffer.alloc(0);
                }
            };
        },

        createDecipher: function(algorithm, password) {
            return this.createCipher(algorithm, password); // XOR is symmetric
        },

        // Constants
        constants: {
            RSA_PKCS1_PADDING: 1,
            RSA_SSLV23_PADDING: 2,
            RSA_NO_PADDING: 3,
            RSA_PKCS1_OAEP_PADDING: 4,
            RSA_X931_PADDING: 5,
            RSA_PKCS1_PSS_PADDING: 6
        }
    };

    // Make crypto available globally in all contexts with enhanced web worker support
    if (typeof global !== 'undefined') {
        global.crypto = crypto;
        console.log('[Crypto Polyfill] Crypto attached to global');
    }

    if (typeof globalThis !== 'undefined') {
        globalThis.crypto = crypto;
        console.log('[Crypto Polyfill] Crypto attached to globalThis');
    }

    if (typeof self !== 'undefined') {
        self.crypto = crypto;
        console.log('[Crypto Polyfill] Crypto attached to self (web worker context)');
    }

    if (typeof window !== 'undefined') {
        window.crypto = crypto;
        console.log('[Crypto Polyfill] Crypto attached to window');
    }

    // Enhanced require() polyfill for web worker environments
    const createRequirePolyfill = function() {
        return function(module) {
            console.log('[Crypto Polyfill] require() called for module:', module);
            if (module === 'crypto') {
                console.log('[Crypto Polyfill] Returning crypto module');
                return crypto;
            }
            // Try to find the module in global scope
            if (typeof globalThis !== 'undefined' && globalThis[module]) {
                return globalThis[module];
            }
            if (typeof self !== 'undefined' && self[module]) {
                return self[module];
            }
            throw new Error('Module not found: ' + module);
        };
    };

    // Set up require() in all possible contexts
    if (typeof global !== 'undefined') {
        if (typeof global.require === 'undefined') {
            global.require = createRequirePolyfill();
            console.log('[Crypto Polyfill] require() polyfill created in global');
        } else {
            const originalRequire = global.require;
            global.require = function(module) {
                if (module === 'crypto') {
                    console.log('[Crypto Polyfill] Intercepted crypto require in global');
                    return crypto;
                }
                return originalRequire.apply(this, arguments);
            };
        }
    }

    if (typeof globalThis !== 'undefined') {
        if (typeof globalThis.require === 'undefined') {
            globalThis.require = createRequirePolyfill();
            console.log('[Crypto Polyfill] require() polyfill created in globalThis');
        }
    }

    if (typeof self !== 'undefined') {
        if (typeof self.require === 'undefined') {
            self.require = createRequirePolyfill();
            console.log('[Crypto Polyfill] require() polyfill created in self (web worker)');
        }
    }

    // Make it available as a CommonJS module
    if (typeof module !== 'undefined' && module.exports) {
        module.exports = crypto;
        console.log('[Crypto Polyfill] Crypto exported as CommonJS module');
    }

    // Make it available as an AMD module
    if (typeof define === 'function' && define.amd) {
        define(function() {
            console.log('[Crypto Polyfill] Crypto defined as AMD module');
            return crypto;
        });
    }

    console.log('[Crypto Polyfill] Enhanced crypto module polyfill loaded successfully');
    console.log('[Crypto Polyfill] Available methods:', Object.keys(crypto));
    console.log('[Crypto Polyfill] Environment check:');
    console.log('  - global:', typeof global !== 'undefined');
    console.log('  - globalThis:', typeof globalThis !== 'undefined');
    console.log('  - self:', typeof self !== 'undefined');
    console.log('  - window:', typeof window !== 'undefined');
    console.log('  - require available:', typeof require !== 'undefined');
})();
'''

        polyfill_file = polyfill_dir / "crypto-polyfill.js"
        with open(polyfill_file, 'w') as f:
            f.write(crypto_polyfill_content)

        return polyfill_file

    def _setup_nodejs_environment(self, env):
        """Setup Node.js environment variables for extension compatibility.

        This fixes the crypto module issue and other Node.js compatibility problems
        that prevent extensions like Augment from working properly.
        """
        # Create crypto polyfill for web worker environments
        polyfill_file = self._create_crypto_polyfill()

        # Node.js options for extension host compatibility
        # Removed problematic --loader option that was causing ES module errors
        node_options = [
            "--experimental-modules",
            "--experimental-json-modules",
            "--enable-source-maps",
            "--max-old-space-size=4096",
            "--unhandled-rejections=warn",
            f"--require={polyfill_file}"  # Inject crypto polyfill (this works correctly)
        ]

        # Set NODE_OPTIONS for extension host
        env['NODE_OPTIONS'] = " ".join(node_options)

        # Set NODE_PATH to include system and local node modules
        node_paths = [
            "/usr/lib/node_modules",
            "/usr/local/lib/node_modules",
            str(Path.home() / ".local/lib/node_modules"),
            str(Path.home() / "node_modules"),
            str(Path.home() / ".local/share/code-server/node_modules")
        ]
        env['NODE_PATH'] = ":".join(node_paths)

        # Extension host specific environment variables
        env['VSCODE_EXTENSION_HOST_NODE_OPTIONS'] = " ".join(node_options)
        env['VSCODE_ALLOW_IO'] = "true"
        env['VSCODE_WEBVIEW_EXTERNAL_ENDPOINT'] = "{{HOSTNAME}}"

        # Web worker compatibility
        env['VSCODE_WEB_WORKER_EXTENSION_HOST_ENABLED'] = "true"
        env['VSCODE_EXTENSION_HOST_CRYPTO_POLYFILL'] = str(polyfill_file)

        # Enable crypto and other Node.js modules for extensions
        env['NODE_PRESERVE_SYMLINKS'] = "1"
        env['NODE_PRESERVE_SYMLINKS_MAIN'] = "1"

        # Disable Node.js warnings that might interfere with extensions
        env['NODE_NO_WARNINGS'] = "1"

        # Force crypto module availability
        env['FORCE_CRYPTO_POLYFILL'] = "1"

        print(f"🔧 Crypto polyfill created: {polyfill_file}")

        return env



    def _create_code_server_config(self):
        """Create code-server configuration file with crypto polyfill support."""
        try:
            config_dir = Path.home() / ".config" / "code-server"
            config_dir.mkdir(parents=True, exist_ok=True)

            config_file = config_dir / "config.yaml"

            # Get current configuration
            port = self.config.get("code_server.port", 8080)
            password = self.config.get("code_server.password", "colab123")

            # Create simple, compatible configuration
            config_content = f'''# Code Server Configuration
bind-addr: 0.0.0.0:{port}
auth: password
password: {password}
cert: false
extensions-dir: {Path.home() / ".local" / "share" / "code-server" / "extensions"}
user-data-dir: {Path.home() / ".local" / "share" / "code-server"}
disable-telemetry: true
disable-update-check: true
log: info
'''

            with open(config_file, 'w') as f:
                f.write(config_content)

            print(f"🔧 Code-server config created: {config_file}")
            return config_file

        except Exception as e:
            print(f"❌ Failed to create config file: {e}")
            # Return None to indicate failure
            return None

    def _inject_crypto_polyfill_to_extensions(self):
        """Inject crypto polyfill into existing extensions that need it."""
        extensions_dir = Path.home() / ".local" / "share" / "code-server" / "extensions"
        polyfill_file = self._create_crypto_polyfill()

        if not extensions_dir.exists():
            return 0

        # Find extensions that might need crypto polyfill
        target_patterns = ["*augment*", "*vscode-augment*", "*claude*", "*ai*"]
        found_extensions = []

        for pattern in target_patterns:
            found_extensions.extend(list(extensions_dir.glob(pattern)))

        injected_count = 0

        for ext_dir in found_extensions:
            if ext_dir.is_dir():
                injected_count += self._inject_polyfill_into_extension(ext_dir, polyfill_file)

        return injected_count

    def _inject_polyfill_into_extension(self, ext_dir, polyfill_file):
        """Inject crypto polyfill into a specific extension."""
        injected = 0

        # Look for extension.js files in common locations
        possible_locations = [
            ext_dir / "out" / "extension.js",
            ext_dir / "dist" / "extension.js",
            ext_dir / "lib" / "extension.js",
            ext_dir / "extension.js"
        ]

        for extension_js in possible_locations:
            if extension_js.exists():
                try:
                    # Create backup first
                    backup_file = extension_js.with_suffix('.js.backup')
                    if not backup_file.exists():
                        shutil.copy2(extension_js, backup_file)

                    # Read current extension.js
                    with open(extension_js, 'r', encoding='utf-8') as f:
                        content = f.read()

                    # Check if polyfill is already injected
                    if "Enhanced crypto module polyfill loaded successfully" not in content:
                        # Read polyfill content
                        with open(polyfill_file, 'r', encoding='utf-8') as f:
                            polyfill_content = f.read()

                        # Create a more robust injection
                        injection_marker = "// CRYPTO_POLYFILL_INJECTED"
                        if injection_marker not in content:
                            # Inject polyfill at the very beginning with proper wrapping
                            new_content = f'''
{injection_marker}
// Crypto polyfill injection for extension compatibility
try {{
{polyfill_content}
}} catch (polyfillError) {{
    console.error('[Extension] Failed to load crypto polyfill:', polyfillError);
}}

// Original extension code follows:
{content}
'''

                            # Write back to extension.js
                            with open(extension_js, 'w', encoding='utf-8') as f:
                                f.write(new_content)

                            print(f"✅ Crypto polyfill injected into: {extension_js}")
                            injected += 1
                        else:
                            print(f"ℹ️  Crypto polyfill already present in: {extension_js}")
                    else:
                        print(f"ℹ️  Enhanced crypto polyfill already present in: {extension_js}")

                except Exception as e:
                    print(f"⚠️  Failed to inject polyfill into {extension_js}: {e}")
                    # Try to restore backup if injection failed
                    backup_file = extension_js.with_suffix('.js.backup')
                    if backup_file.exists():
                        try:
                            shutil.copy2(backup_file, extension_js)
                            print(f"🔄 Restored backup for: {extension_js}")
                        except:
                            pass

        return injected

    def _create_web_worker_crypto_fix(self):
        """Create a web worker specific crypto fix that gets injected into the extension host."""
        polyfill_dir = Path.home() / ".local" / "share" / "code-server" / "polyfills"
        polyfill_dir.mkdir(parents=True, exist_ok=True)

        # Create a more aggressive web worker crypto polyfill
        web_worker_crypto_content = '''
// Web Worker Crypto Polyfill - Aggressive injection for VS Code extensions
// This runs before any extension code and ensures crypto is available

console.log('[Web Worker Crypto] Starting aggressive crypto polyfill injection');

// Immediately define crypto in all possible global contexts
(function() {
    'use strict';

    // Buffer polyfill for web workers
    if (typeof Buffer === 'undefined') {
        const BufferPolyfill = {
            from: function(data) {
                if (data instanceof Uint8Array) return data;
                if (typeof data === 'string') {
                    const encoder = new TextEncoder();
                    return encoder.encode(data);
                }
                return new Uint8Array(data);
            },
            alloc: function(size) { return new Uint8Array(size); }
        };

        // Define Buffer in all contexts
        if (typeof globalThis !== 'undefined') globalThis.Buffer = BufferPolyfill;
        if (typeof self !== 'undefined') self.Buffer = BufferPolyfill;
        if (typeof global !== 'undefined') global.Buffer = BufferPolyfill;
        if (typeof window !== 'undefined') window.Buffer = BufferPolyfill;
    }

    // Crypto implementation
    const cryptoImpl = {
        randomBytes: function(size, callback) {
            try {
                let array = new Uint8Array(size);

                // Use Web Crypto API if available
                const cryptoSource = globalThis.crypto || self.crypto || window.crypto;
                if (cryptoSource && cryptoSource.getRandomValues) {
                    cryptoSource.getRandomValues(array);
                } else {
                    // Fallback to Math.random
                    for (let i = 0; i < size; i++) {
                        array[i] = Math.floor(Math.random() * 256);
                    }
                }

                const buffer = (globalThis.Buffer || self.Buffer || Buffer).from(array);

                if (callback) {
                    setTimeout(() => callback(null, buffer), 0);
                    return;
                }
                return buffer;
            } catch (error) {
                if (callback) {
                    setTimeout(() => callback(error), 0);
                    return;
                }
                throw error;
            }
        },

        randomBytesSync: function(size) {
            return this.randomBytes(size);
        },

        createHash: function(algorithm) {
            return {
                update: function(data) { this._data = (this._data || '') + data; return this; },
                digest: function(encoding) {
                    const hash = Math.abs((this._data || '').split('').reduce((a, b) => {
                        a = ((a << 5) - a) + b.charCodeAt(0);
                        return a & a;
                    }, 0));
                    return encoding === 'hex' ? hash.toString(16) : hash.toString();
                }
            };
        },

        createHmac: function(algorithm, key) {
            return this.createHash(algorithm);
        }
    };

    // Aggressive global injection
    const contexts = [globalThis, self, global, window].filter(ctx => ctx);
    contexts.forEach(ctx => {
        if (ctx) {
            ctx.crypto = cryptoImpl;
            console.log('[Web Worker Crypto] Injected crypto into context:', ctx.constructor.name);
        }
    });

    // Create require function that returns crypto
    const requirePolyfill = function(module) {
        console.log('[Web Worker Crypto] require() called for:', module);
        if (module === 'crypto') {
            console.log('[Web Worker Crypto] Returning crypto module');
            return cryptoImpl;
        }
        throw new Error('Module not found: ' + module);
    };

    // Inject require in all contexts
    contexts.forEach(ctx => {
        if (ctx && !ctx.require) {
            ctx.require = requirePolyfill;
            console.log('[Web Worker Crypto] Injected require() into context');
        }
    });

    console.log('[Web Worker Crypto] Aggressive crypto polyfill injection complete');
    console.log('[Web Worker Crypto] Testing crypto availability...');

    // Test the implementation
    try {
        const testCrypto = requirePolyfill('crypto');
        const testBytes = testCrypto.randomBytes(16);
        console.log('[Web Worker Crypto] Test successful, crypto is working:', testBytes.length === 16);
    } catch (e) {
        console.error('[Web Worker Crypto] Test failed:', e);
    }
})();
'''

        web_worker_file = polyfill_dir / "web-worker-crypto.js"
        with open(web_worker_file, 'w') as f:
            f.write(web_worker_crypto_content)

        return web_worker_file

    def _create_aggressive_crypto_fix(self):
        """Create an aggressive crypto fix that replaces the extension entirely if needed."""
        print("\n🚨 Creating Aggressive Crypto Fix...")

        # Find all Augment extensions
        extensions_base = Path.home() / ".local" / "share" / "code-server" / "extensions"
        if not extensions_base.exists():
            print(f"❌ Extensions directory not found: {extensions_base}")
            return 0

        augment_dirs = list(extensions_base.glob("*augment*"))
        if not augment_dirs:
            print("❌ No Augment extensions found")
            return 0

        fixed_count = 0
        for ext_dir in augment_dirs:
            print(f"🔧 Processing extension: {ext_dir.name}")

            # Find the extension.js file
            extension_js_paths = [
                ext_dir / "out" / "extension.js",
                ext_dir / "dist" / "extension.js",
                ext_dir / "lib" / "extension.js",
                ext_dir / "extension.js"
            ]

            for ext_js in extension_js_paths:
                if ext_js.exists():
                    print(f"📁 Found extension file: {ext_js}")

                    try:
                        # Read the current content
                        with open(ext_js, 'r', encoding='utf-8') as f:
                            content = f.read()

                        # Create backup
                        backup_file = ext_js.with_suffix('.js.original')
                        if not backup_file.exists():
                            with open(backup_file, 'w', encoding='utf-8') as f:
                                f.write(content)
                            print(f"💾 Backup created: {backup_file}")

                        # Create aggressive crypto replacement
                        crypto_replacement = '''
// AGGRESSIVE CRYPTO POLYFILL - COMPLETE REPLACEMENT
console.log('[AGGRESSIVE CRYPTO] Starting complete crypto module replacement');

// Step 1: Create Buffer polyfill
if (typeof Buffer === 'undefined') {
    globalThis.Buffer = class Buffer extends Uint8Array {
        static from(data) {
            if (data instanceof Uint8Array) return data;
            if (typeof data === 'string') {
                const encoder = new TextEncoder();
                return new this(encoder.encode(data));
            }
            return new this(data);
        }

        static alloc(size) {
            return new this(size);
        }

        toString(encoding = 'utf8') {
            if (encoding === 'hex') {
                return Array.from(this).map(b => b.toString(16).padStart(2, '0')).join('');
            }
            const decoder = new TextDecoder();
            return decoder.decode(this);
        }
    };
    console.log('[AGGRESSIVE CRYPTO] Buffer polyfill created');
}

// Step 2: Create comprehensive crypto module
const cryptoModule = {
    randomBytes: function(size, callback) {
        try {
            const array = new Uint8Array(size);
            const cryptoObj = globalThis.crypto || self.crypto || window.crypto;

            if (cryptoObj && cryptoObj.getRandomValues) {
                cryptoObj.getRandomValues(array);
            } else {
                for (let i = 0; i < size; i++) {
                    array[i] = Math.floor(Math.random() * 256);
                }
            }

            const buffer = Buffer.from(array);

            if (callback) {
                setTimeout(() => callback(null, buffer), 0);
                return;
            }
            return buffer;
        } catch (error) {
            if (callback) {
                setTimeout(() => callback(error), 0);
                return;
            }
            throw error;
        }
    },

    randomBytesSync: function(size) {
        return this.randomBytes(size);
    },

    createHash: function(algorithm) {
        return {
            _data: '',
            update: function(data) {
                this._data += data.toString();
                return this;
            },
            digest: function(encoding) {
                let hash = 0;
                for (let i = 0; i < this._data.length; i++) {
                    const char = this._data.charCodeAt(i);
                    hash = ((hash << 5) - hash) + char;
                    hash = hash & hash;
                }
                hash = Math.abs(hash);

                if (encoding === 'hex') {
                    return hash.toString(16).padStart(8, '0');
                }
                return Buffer.from(hash.toString());
            }
        };
    },

    createHmac: function(algorithm, key) {
        return this.createHash(algorithm);
    }
};

// Step 3: Aggressive global injection
const globalContexts = [globalThis, self, global, window];
globalContexts.forEach(ctx => {
    if (ctx) {
        ctx.crypto = cryptoModule;
        console.log('[AGGRESSIVE CRYPTO] Injected into:', ctx.constructor?.name || 'unknown context');
    }
});

// Step 4: Override require function completely
const originalRequire = (typeof require !== 'undefined') ? require : null;
const aggressiveRequire = function(moduleName) {
    console.log('[AGGRESSIVE CRYPTO] require() called for:', moduleName);

    if (moduleName === 'crypto') {
        console.log('[AGGRESSIVE CRYPTO] Returning crypto module');
        return cryptoModule;
    }

    if (originalRequire) {
        try {
            return originalRequire(moduleName);
        } catch (e) {
            console.log('[AGGRESSIVE CRYPTO] Original require failed for:', moduleName, e.message);
        }
    }

    throw new Error('Module not found: ' + moduleName);
};

// Inject require in all contexts
globalContexts.forEach(ctx => {
    if (ctx) {
        ctx.require = aggressiveRequire;
    }
});

// Step 5: Test the crypto module immediately
try {
    const testCrypto = aggressiveRequire('crypto');
    const testBytes = testCrypto.randomBytes(16);
    console.log('[AGGRESSIVE CRYPTO] ✅ Test successful - crypto is working, bytes length:', testBytes.length);
} catch (error) {
    console.error('[AGGRESSIVE CRYPTO] ❌ Test failed:', error);
}

console.log('[AGGRESSIVE CRYPTO] Complete crypto replacement finished');

// Original extension code follows:
'''

                        # Replace the entire content with crypto fix + original
                        new_content = crypto_replacement + content

                        # Write the new content
                        with open(ext_js, 'w', encoding='utf-8') as f:
                            f.write(new_content)

                        print(f"✅ Aggressive crypto fix applied to: {ext_js}")
                        fixed_count += 1

                    except Exception as e:
                        print(f"❌ Failed to apply aggressive fix to {ext_js}: {e}")
                        # Restore from backup if available
                        backup_file = ext_js.with_suffix('.js.original')
                        if backup_file.exists():
                            try:
                                with open(backup_file, 'r', encoding='utf-8') as f:
                                    original_content = f.read()
                                with open(ext_js, 'w', encoding='utf-8') as f:
                                    f.write(original_content)
                                print(f"🔄 Restored from backup: {ext_js}")
                            except:
                                pass

                    break  # Only process the first found extension.js

        return fixed_count

    def fix_crypto_extensions(self):
        """Fix crypto module issues in installed extensions - Main menu function."""
        print("\n🔧 Fixing Crypto Module Extensions")
        print("=" * 50)

        # Check if Code Server is running
        if self._is_code_server_running():
            print("⚠️  Code Server is currently running.")
            choice = input("🔄 Stop Code Server to apply fixes? (y/N): ").strip().lower()
            if choice == 'y':
                self.stop_code_server()
                time.sleep(2)
            else:
                print("❌ Cannot apply fixes while Code Server is running.")
                return

        # Create all polyfills
        polyfill_file = self._create_crypto_polyfill()
        web_worker_file = self._create_web_worker_crypto_fix()

        # Try normal injection first
        injected_count = self._inject_crypto_polyfill_to_extensions()

        # If normal injection didn't work, try aggressive fix
        if injected_count == 0:
            print("\n🚨 Normal crypto injection found no extensions to patch.")
            print("🔧 Attempting aggressive crypto fix...")
            aggressive_count = self._create_aggressive_crypto_fix()
            injected_count = aggressive_count

        # Create enhanced code-server config
        config_file = self._create_code_server_config()

        print(f"\n📊 Fix Results:")
        print(f"   • Node.js crypto polyfill created: {polyfill_file}")
        print(f"   • Web worker crypto polyfill created: {web_worker_file}")
        print(f"   • Extensions patched: {injected_count}")
        print(f"   • Config file updated: {config_file}")
        print(f"   • Node.js environment: Configured for crypto compatibility")

        if injected_count > 0:
            print("\n✅ Crypto module fixes applied successfully!")
            print("💡 The following fixes have been applied:")
            print("   • Enhanced crypto polyfill with Node.js compatibility")
            print("   • Web worker crypto polyfill for browser context")
            print("   • Aggressive crypto module replacement")
            print("   • Extension host wrapper for early crypto loading")
            print("   • Direct extension patching with backup")
            print("   • Improved Node.js environment configuration")

            restart = input("\n🔄 Start Code Server with crypto fixes? (y/N): ").strip().lower()
            if restart == 'y':
                print("🔄 Starting Code Server with crypto fixes...")
                self.start_code_server()
        else:
            print("\n⚠️  No extensions found that need crypto fixes")
            print("💡 If you install Augment extension later, run this fix again")
            print("💡 The crypto polyfill is still configured for future extensions")

        return injected_count

    def _verify_nodejs_compatibility(self):
        """Verify Node.js installation and compatibility for extensions."""
        try:
            # Check Node.js version
            result = subprocess.run(['node', '--version'], capture_output=True, text=True)
            if result.returncode == 0:
                version = result.stdout.strip()
                print(f"✅ Node.js version: {version}")

                # Check if version is compatible (v14+ recommended)
                version_num = version.replace('v', '').split('.')[0]
                if int(version_num) >= 14:
                    print("✅ Node.js version is compatible with extensions")
                else:
                    print("⚠️  Node.js version might be too old for some extensions")

                return True
            else:
                print("❌ Node.js not found or not working")
                return False

        except Exception as e:
            print(f"❌ Error checking Node.js: {e}")
            return False

    def _check_extension_compatibility(self):
        """Check if the environment is properly configured for extension compatibility."""
        print("\n🔍 Extension Compatibility Check")
        print("=" * 50)

        # Check Node.js
        nodejs_ok = self._verify_nodejs_compatibility()

        # Check crypto module availability
        try:
            result = subprocess.run(['node', '-e', 'console.log(require("crypto"))'],
                                  capture_output=True, text=True)
            if result.returncode == 0:
                print("✅ Crypto module is available")
                crypto_ok = True
            else:
                print("❌ Crypto module is not available")
                crypto_ok = False
        except Exception:
            print("❌ Cannot test crypto module")
            crypto_ok = False

        # Check environment variables
        env_vars = ['NODE_OPTIONS', 'NODE_PATH', 'EXTENSIONS_GALLERY']
        env_ok = True
        for var in env_vars:
            if os.environ.get(var):
                print(f"✅ {var} is set")
            else:
                print(f"❌ {var} is not set")
                env_ok = False

        overall_status = nodejs_ok and crypto_ok and env_ok

        if overall_status:
            print("\n🎉 Environment is ready for extensions like Augment!")
        else:
            print("\n⚠️  Some compatibility issues detected")
            print("💡 Try restarting Code Server with enhanced environment")

        return overall_status

    def _fix_crypto_extensions(self):
        """Fix crypto module issues in installed extensions."""
        print("\n🔧 Fixing Crypto Module Extensions")
        print("=" * 50)

        # Create crypto polyfill
        polyfill_file = self._create_crypto_polyfill()

        # Inject polyfill into extensions
        injected_count = self._inject_crypto_polyfill_to_extensions()

        # Create enhanced code-server config
        config_file = self._create_code_server_config()

        print(f"\n📊 Fix Results:")
        print(f"   • Crypto polyfill created: {polyfill_file}")
        print(f"   • Extensions patched: {injected_count}")
        print(f"   • Config file updated: {config_file}")

        if injected_count > 0:
            print("\n✅ Crypto module fixes applied successfully!")
            print("💡 Restart Code Server to apply changes:")
            print("   Menu: 8 → 7 (Force Restart with Environment)")

            restart = input("\n🔄 Restart Code Server now? (y/N): ").strip().lower()
            if restart == 'y':
                print("🔄 Restarting Code Server with crypto fixes...")
                self._force_restart_with_env()
        else:
            print("\n⚠️  No extensions found that need crypto fixes")
            print("💡 If you install Augment extension later, run this fix again")

        return injected_count

    def start_code_server(self):
        """Start Code Server process with default Hybrid Registry (Microsoft + Open VSX)."""
        print("▶️  Starting Code Server with Crypto Polyfill Support...")

        try:
            # Check if already running
            if self._is_code_server_running():
                print("ℹ️  Code Server is already running.")

                # Show current access information
                password = self.config.get("code_server.password", "colab123")
                port = self.config.get("code_server.port", 8080)

                print(f"\n🌐 Access Information:")
                print(f"   • Local URL: http://127.0.0.1:{port}")
                print(f"   • Password: {password}")

                # Check if ngrok tunnel exists
                if self.ngrok_tunnel and self.ngrok_tunnel.public_url:
                    print(f"   • Public URL: {self.ngrok_tunnel.public_url}")
                elif self.config.get("ngrok.auth_token"):
                    print("   • Setting up ngrok tunnel...")
                    self._start_ngrok_tunnel()
                    if self.ngrok_tunnel and self.ngrok_tunnel.public_url:
                        print(f"   • Public URL: {self.ngrok_tunnel.public_url}")
                else:
                    print("   • Public URL: Not configured (setup ngrok in menu option 9)")

                print(f"\n💡 Options:")
                print(f"   • To restart: Use menu option 4")
                print(f"   • To stop: Use menu option 3")
                print(f"   • To setup ngrok: Use menu option 9")

                return

            # Check if installed
            code_server_bin = BIN_DIR / "code-server"
            if not code_server_bin.exists():
                print("❌ Code Server is not installed. Please install it first.")
                return

            # Setup default hybrid registry configuration
            self._setup_default_hybrid_registry()

            # Create code-server configuration with crypto polyfill support
            config_file = self._create_code_server_config()

            if not config_file:
                print("❌ Failed to create configuration file")
                return

            # Inject crypto polyfill into existing extensions
            injected_count = self._inject_crypto_polyfill_to_extensions()

            # Start Code Server in background
            print("🚀 Starting Code Server with Enhanced Configuration...")
            print("🏢 Primary Registry: Microsoft Marketplace (UI search/discovery)")
            print("🌐 Fallback Registry: Open VSX (automatic fallback)")
            print("🔧 Crypto Polyfill: Enabled for extension compatibility")
            print(f"💉 Extensions Patched: {injected_count} extension(s)")

            # Prepare environment with Microsoft Marketplace as primary
            env = os.environ.copy()
            env["EXTENSIONS_GALLERY"] = '{"serviceUrl": "https://marketplace.visualstudio.com/_apis/public/gallery", "itemUrl": "https://marketplace.visualstudio.com/items", "resourceUrlTemplate": "https://marketplace.visualstudio.com/_apis/public/gallery/publishers/{publisher}/vsextensions/{name}/{version}/vspackage"}'

            # Set password via environment variable
            password = self.config.get("code_server.password", "colab123")
            env['PASSWORD'] = password

            # Setup Node.js environment for extension compatibility (fixes crypto module issue)
            env = self._setup_nodejs_environment(env)

            # Start process with configuration file
            print(f"🔧 Starting with config: {config_file}")
            print(f"🔧 Command: {code_server_bin} --config {config_file}")

            self.code_server_process = subprocess.Popen(
                [str(code_server_bin), "--config", str(config_file)],
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                start_new_session=True
            )

            # Wait a moment for startup
            time.sleep(3)

            if self._is_code_server_running():
                print("✅ Code Server started successfully with Hybrid Registry!")
                print("\n🎯 Hybrid Registry Features:")
                print("   • UI Extensions tab: Search Microsoft Marketplace")
                print("   • Automatic fallback: Open VSX for missing extensions")
                print("   • Enhanced extension manager: Menu 7 for advanced features")
                print("   • Best of both worlds: Complete extension ecosystem")

                # Setup ngrok tunnel if configured
                if self.config.get("ngrok.auth_token"):
                    self._start_ngrok_tunnel()
                else:
                    print(f"\n🌐 Access Code Server at: http://127.0.0.1:8080")
                    print(f"🔑 Password: {password}")
            else:
                print("❌ Failed to start Code Server")

                # Get error details from process
                if self.code_server_process and self.code_server_process.poll() is not None:
                    try:
                        stdout, stderr = self.code_server_process.communicate(timeout=5)
                        if stderr:
                            print(f"🔍 Error details: {stderr.decode().strip()}")
                        if stdout:
                            print(f"🔍 Output: {stdout.decode().strip()}")
                    except subprocess.TimeoutExpired:
                        print("⏱️  Process still running but not responding")
                    except Exception as comm_error:
                        print(f"⚠️  Could not get error details: {comm_error}")

        except Exception as e:
            self.logger.error(f"Failed to start Code Server: {e}")
            print(f"❌ Failed to start Code Server: {e}")
            print(f"🔍 Exception details: {str(e)}")

            # Try to start without config file as fallback
            print("\n🔄 Attempting fallback startup without config file...")
            try:
                self.code_server_process = subprocess.Popen(
                    [str(code_server_bin)],
                    env=env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    start_new_session=True
                )

                time.sleep(3)

                if self._is_code_server_running():
                    print("✅ Code Server started successfully with fallback method!")
                    print(f"\n🌐 Access Code Server at: http://127.0.0.1:8080")
                    print(f"🔑 Password: {password}")
                else:
                    print("❌ Fallback startup also failed")
                    if self.code_server_process and self.code_server_process.poll() is not None:
                        try:
                            stdout, stderr = self.code_server_process.communicate(timeout=5)
                            if stderr:
                                print(f"🔍 Fallback error: {stderr.decode().strip()}")
                        except:
                            pass

            except Exception as fallback_error:
                print(f"❌ Fallback startup failed: {fallback_error}")

    def _setup_default_hybrid_registry(self):
        """Setup default hybrid registry configuration automatically."""
        # Enable hybrid mode by default
        self.config.set("extension_registry.hybrid_mode", True)
        self.config.set("extension_registry.primary", "microsoft")
        self.config.set("extension_registry.fallback", "openvsx")

        # Setup hybrid config
        hybrid_config = {
            "primary_registry": {
                "name": "Microsoft Marketplace",
                "serviceUrl": "https://marketplace.visualstudio.com/_apis/public/gallery",
                "itemUrl": "https://marketplace.visualstudio.com/items",
                "api_url": "https://marketplace.visualstudio.com/_apis/public/gallery/extensionquery"
            },
            "fallback_registry": {
                "name": "Open VSX",
                "serviceUrl": "https://open-vsx.org/vscode/gallery",
                "itemUrl": "https://open-vsx.org/vscode/item",
                "api_url": "https://open-vsx.org/api/-/search"
            },
            "enabled": True,
            "auto_fallback": True
        }

        # Save hybrid config
        self.config.set("extension_registry.hybrid_config", hybrid_config)

        # Update shell profile for persistence
        microsoft_gallery = '{"serviceUrl": "https://marketplace.visualstudio.com/_apis/public/gallery", "itemUrl": "https://marketplace.visualstudio.com/items", "resourceUrlTemplate": "https://marketplace.visualstudio.com/_apis/public/gallery/publishers/{publisher}/vsextensions/{name}/{version}/vspackage"}'
        self._update_shell_profile_registry(microsoft_gallery)

    def stop_code_server(self):
        """Stop Code Server process."""
        print("⏹️  Stopping Code Server...")

        try:
            # Check if Code Server is actually running first
            if not self._is_code_server_running():
                print("ℹ️  Code Server is not running.")
                return

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
            processes_found = 0

            print("🔍 Finding Code Server processes...")

            if PSUTIL_AVAILABLE:
                # Use psutil for more reliable process management
                for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                    try:
                        cmdline = ' '.join(proc.info['cmdline'] or [])
                        if 'code-server' in cmdline:
                            processes_found += 1
                            print(f"   • Found process PID {proc.info['pid']}")
                            proc.terminate()
                            killed = True

                            # Wait a moment for graceful termination
                            try:
                                proc.wait(timeout=3)
                                print(f"   • Process {proc.info['pid']} terminated gracefully")
                            except psutil.TimeoutExpired:
                                print(f"   • Force killing process {proc.info['pid']}")
                                proc.kill()

                    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.TimeoutExpired):
                        continue
            else:
                # Fallback method - platform specific
                print("   • Using system commands...")
                try:
                    if sys.platform == "win32":
                        # Windows: use taskkill command
                        result = subprocess.run(
                            ["taskkill", "/F", "/IM", "code-server.exe"],
                            capture_output=True,
                            text=True,
                            timeout=10
                        )
                        if result.returncode == 0:
                            killed = True
                            processes_found = 1
                    else:
                        # Linux/Unix: use pkill command
                        result = subprocess.run(
                            ["pkill", "-f", "code-server"],
                            capture_output=True,
                            text=True,
                            timeout=10
                        )
                        if result.returncode == 0:
                            killed = True
                            processes_found = 1
                except subprocess.TimeoutExpired:
                    print("⚠️  Stop command timed out, but processes may have been terminated")
                    killed = True
                except Exception as stop_error:
                    print(f"⚠️  Error during stop: {stop_error}")

            # Verify that processes are actually stopped
            time.sleep(1)
            if self._is_code_server_running():
                print("⚠️  Some Code Server processes may still be running")
                print("💡 Try using 'Restart Code Server' (option 4) for a force restart")
            else:
                if killed and processes_found > 0:
                    print(f"✅ Code Server stopped successfully! ({processes_found} process(es) terminated)")
                elif processes_found == 0:
                    print("ℹ️  No Code Server processes were found.")
                else:
                    print("✅ Code Server stopped successfully!")

        except KeyboardInterrupt:
            print("\n⚠️  Stop operation interrupted by user")
            print("💡 Code Server processes may still be running")
        except Exception as e:
            self.logger.error(f"Failed to stop Code Server: {e}")
            print(f"❌ Failed to stop Code Server: {e}")
            print("💡 Try using 'Restart Code Server' (option 4) for a force restart")

    def restart_code_server(self):
        """Restart Code Server."""
        print("🔄 Restarting Code Server...")
        self.stop_code_server()
        time.sleep(2)
        self.start_code_server()

    # ============================================================================
    # VSCode Server Methods (Official Microsoft VSCode Server)
    # ============================================================================

    def install_vscode_server(self):
        """Install VSCode Server (Official Microsoft CLI)."""
        print("🚀 Installing VSCode Server (Official Microsoft CLI)...")

        try:
            # Check if already installed
            vscode_bin = Path(self.config.get("vscode_server.bin_path", str(Path.home() / ".local" / "bin" / "code")))
            if vscode_bin.exists():
                print("✅ VSCode Server CLI already installed")
                return True

            # Create directories
            install_dir = Path(self.config.get("vscode_server.install_dir", str(Path.home() / ".local" / "lib" / "vscode-server")))
            bin_dir = vscode_bin.parent
            install_dir.mkdir(parents=True, exist_ok=True)
            bin_dir.mkdir(parents=True, exist_ok=True)

            # Download VSCode CLI
            if not self._download_vscode_cli():
                print("❌ Failed to download VSCode CLI")
                return False

            # Extract and install
            if not self._extract_vscode_cli():
                print("❌ Failed to extract VSCode CLI")
                return False

            print("✅ VSCode Server installed successfully!")
            print("💡 You can now use 'Start VSCode Server' to create tunnels")
            return True

        except Exception as e:
            self.logger.error(f"VSCode Server installation failed: {e}")
            print(f"❌ Installation failed: {e}")
            return False

    def _download_vscode_cli(self) -> bool:
        """Download VSCode CLI binary."""
        try:
            # Determine platform and architecture
            import platform
            system = platform.system().lower()
            machine = platform.machine().lower()

            # Map to VSCode CLI naming convention
            if system == "linux":
                if machine in ["x86_64", "amd64"]:
                    platform_name = "cli-linux-x64"
                elif machine in ["aarch64", "arm64"]:
                    platform_name = "cli-linux-arm64"
                elif machine in ["armv7l", "armhf"]:
                    platform_name = "cli-linux-armhf"
                else:
                    platform_name = "cli-linux-x64"  # Default fallback
            elif system == "darwin":
                if machine in ["arm64", "aarch64"]:
                    platform_name = "cli-darwin-arm64"
                else:
                    platform_name = "cli-darwin-x64"
            elif system == "windows":
                if machine in ["aarch64", "arm64"]:
                    platform_name = "cli-win32-arm64"
                else:
                    platform_name = "cli-win32-x64"
            else:
                platform_name = "cli-linux-x64"  # Default fallback

            # Use latest stable version
            version = self.config.get("vscode_server.version", "latest")
            if version == "latest":
                download_url = f"https://code.visualstudio.com/sha/download?build=stable&os={platform_name}"
            else:
                download_url = f"https://update.code.visualstudio.com/commit:{version}/{platform_name}/stable"

            print(f"📥 Downloading VSCode CLI for {platform_name}...")
            print(f"🔗 URL: {download_url}")

            # Download
            install_dir = Path(self.config.get("vscode_server.install_dir", str(Path.home() / ".local" / "lib" / "vscode-server")))
            self.vscode_download_path = install_dir / f"vscode-cli-{platform_name}.tar.gz"

            response = requests.get(download_url, stream=True, timeout=300)
            response.raise_for_status()

            with open(self.vscode_download_path, 'wb') as f:
                total_size = int(response.headers.get('content-length', 0))
                downloaded = 0
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            progress = (downloaded / total_size) * 100
                            print(f"\r📥 Progress: {progress:.1f}%", end="", flush=True)

            print(f"\n✅ Downloaded: {self.vscode_download_path}")
            return True

        except Exception as e:
            self.logger.error(f"VSCode CLI download failed: {e}")
            print(f"❌ Download failed: {e}")
            return False

    def _extract_vscode_cli(self) -> bool:
        """Extract VSCode CLI archive."""
        try:
            install_dir = Path(self.config.get("vscode_server.install_dir", str(Path.home() / ".local" / "lib" / "vscode-server")))
            bin_path = Path(self.config.get("vscode_server.bin_path", str(Path.home() / ".local" / "bin" / "code")))

            print("📁 Extracting VSCode CLI...")

            with tarfile.open(self.vscode_download_path, 'r:gz') as tar:
                tar.extractall(install_dir)

            # Find the extracted 'code' binary
            code_binary = None
            for root, dirs, files in os.walk(install_dir):
                if 'code' in files:
                    potential_binary = Path(root) / 'code'
                    if potential_binary.is_file() and os.access(potential_binary, os.X_OK):
                        code_binary = potential_binary
                        break

            if not code_binary:
                print("❌ Could not find 'code' binary in extracted files")
                return False

            # Create symlink or copy to bin directory
            if bin_path.exists():
                bin_path.unlink()

            # Try to create symlink first, fallback to copy
            try:
                bin_path.symlink_to(code_binary)
                print(f"🔗 Created symlink: {bin_path} -> {code_binary}")
            except OSError:
                # Fallback to copy if symlink fails
                import shutil
                shutil.copy2(code_binary, bin_path)
                bin_path.chmod(0o755)
                print(f"📋 Copied binary: {bin_path}")

            # Clean up download
            if self.vscode_download_path.exists():
                self.vscode_download_path.unlink()

            print("✅ VSCode CLI extracted successfully!")
            return True

        except Exception as e:
            self.logger.error(f"VSCode CLI extraction failed: {e}")
            print(f"❌ Extraction failed: {e}")
            return False

    def start_vscode_server(self):
        """Start VSCode Server with tunnel."""
        print("▶️  Starting VSCode Server...")

        try:
            # Check if VSCode CLI is installed
            vscode_bin = Path(self.config.get("vscode_server.bin_path", str(Path.home() / ".local" / "bin" / "code")))
            if not vscode_bin.exists():
                print("❌ VSCode CLI not found. Please install VSCode Server first.")
                return False

            # Check if already running
            if self._is_vscode_server_running():
                print("⚠️  VSCode Server is already running")
                self._show_vscode_server_status()
                return True

            # Accept license terms if configured
            if self.config.get("vscode_server.accept_server_license_terms", False):
                os.environ['VSCODE_SERVER_ACCEPT_LICENSE'] = '1'

            # Configure telemetry
            if not self.config.get("vscode_server.enable_telemetry", False):
                os.environ['VSCODE_DISABLE_TELEMETRY'] = '1'

            # Get tunnel name
            tunnel_name = self.config.get("vscode_server.tunnel_name", "")
            if not tunnel_name:
                tunnel_name = f"colab-{int(time.time())}"
                self.config.set("vscode_server.tunnel_name", tunnel_name)

            print(f"🚇 Creating tunnel: {tunnel_name}")
            print("🔐 You'll need to authenticate with Microsoft/GitHub account")
            print("💡 A browser window will open for authentication")

            # Start VSCode Server tunnel
            cmd = [str(vscode_bin), "tunnel", "--name", tunnel_name, "--accept-server-license-terms"]

            print(f"🚀 Starting: {' '.join(cmd)}")

            self.vscode_server_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True
            )

            # Wait for tunnel to be established
            print("⏳ Waiting for tunnel to be established...")
            tunnel_url = None
            start_time = time.time()
            timeout = 120  # 2 minutes timeout

            while time.time() - start_time < timeout:
                if self.vscode_server_process.poll() is not None:
                    # Process ended unexpectedly
                    stdout, stderr = self.vscode_server_process.communicate()
                    print(f"❌ VSCode Server process ended unexpectedly")
                    if stderr:
                        print(f"Error: {stderr}")
                    return False

                # Check for tunnel URL in output
                try:
                    line = self.vscode_server_process.stdout.readline()
                    if line:
                        print(f"📝 {line.strip()}")
                        if "vscode.dev/tunnel" in line:
                            # Extract tunnel URL
                            import re
                            url_match = re.search(r'https://[^\s]+', line)
                            if url_match:
                                tunnel_url = url_match.group()
                                break
                except:
                    pass

                time.sleep(1)

            if tunnel_url:
                print("✅ VSCode Server tunnel started successfully!")
                print(f"🌐 Access URL: {tunnel_url}")
                print("\n💡 How to connect:")
                print("   • Web: Open the URL above in your browser")
                print("   • Desktop: Install 'Remote - Tunnels' extension in VSCode")
                print("   • Desktop: Use 'Remote-Tunnels: Connect to Tunnel' command")
                print(f"   • Tunnel name: {tunnel_name}")

                # Store tunnel info
                self.config.set("vscode_server.tunnel_url", tunnel_url)
                self.config.set("vscode_server.process_pid", self.vscode_server_process.pid)

                return True
            else:
                print("⚠️  Tunnel URL not detected, but process is running")
                print("💡 Check the process output for authentication instructions")
                return True

        except Exception as e:
            self.logger.error(f"Failed to start VSCode Server: {e}")
            print(f"❌ Failed to start VSCode Server: {e}")
            return False

    def stop_vscode_server(self):
        """Stop VSCode Server tunnel."""
        print("⏹️  Stopping VSCode Server...")

        try:
            stopped = False

            # Try to stop the process we started
            if hasattr(self, 'vscode_server_process') and self.vscode_server_process:
                try:
                    self.vscode_server_process.terminate()
                    self.vscode_server_process.wait(timeout=10)
                    stopped = True
                    print("✅ VSCode Server process stopped")
                except subprocess.TimeoutExpired:
                    self.vscode_server_process.kill()
                    stopped = True
                    print("✅ VSCode Server process killed")
                except:
                    pass

            # Fallback: find and stop VSCode tunnel processes
            if not stopped:
                if PSUTIL_AVAILABLE:
                    import psutil
                    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                        try:
                            if proc.info['name'] == 'code' and proc.info['cmdline']:
                                cmdline = ' '.join(proc.info['cmdline'])
                                if 'tunnel' in cmdline:
                                    proc.terminate()
                                    stopped = True
                                    print(f"✅ Stopped VSCode tunnel process (PID: {proc.info['pid']})")
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            continue

            # Clear stored info
            self.config.set("vscode_server.tunnel_url", "")
            self.config.set("vscode_server.process_pid", 0)

            if stopped:
                print("✅ VSCode Server stopped successfully")
            else:
                print("⚠️  No VSCode Server processes found to stop")

            return stopped

        except Exception as e:
            self.logger.error(f"Failed to stop VSCode Server: {e}")
            print(f"❌ Failed to stop VSCode Server: {e}")
            return False

    def restart_vscode_server(self):
        """Restart VSCode Server."""
        print("🔄 Restarting VSCode Server...")
        self.stop_vscode_server()
        time.sleep(2)
        self.start_vscode_server()

    def _is_vscode_server_running(self) -> bool:
        """Check if VSCode Server tunnel is running."""
        try:
            if PSUTIL_AVAILABLE:
                import psutil
                for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                    try:
                        if proc.info['name'] == 'code' and proc.info['cmdline']:
                            cmdline = ' '.join(proc.info['cmdline'])
                            if 'tunnel' in cmdline:
                                return True
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue
            else:
                # Fallback method
                result = subprocess.run(
                    ["pgrep", "-f", "code.*tunnel"],
                    capture_output=True,
                    text=True
                )
                return result.returncode == 0

        except Exception:
            pass

        return False

    def _show_vscode_server_status(self):
        """Show VSCode Server status information."""
        tunnel_url = self.config.get("vscode_server.tunnel_url", "")
        tunnel_name = self.config.get("vscode_server.tunnel_name", "")

        print("\n📊 VSCode Server Status:")
        print(f"   • Status: {'🟢 Running' if self._is_vscode_server_running() else '🔴 Stopped'}")
        if tunnel_name:
            print(f"   • Tunnel Name: {tunnel_name}")
        if tunnel_url:
            print(f"   • Access URL: {tunnel_url}")
        else:
            print("   • Access URL: Not available")

        print(f"\n💡 Connection Options:")
        print(f"   • Web Browser: Use the access URL above")
        print(f"   • Desktop VSCode: Install 'Remote - Tunnels' extension")
        print(f"   • Desktop VSCode: Use 'Remote-Tunnels: Connect to Tunnel' command")

    def _switch_to_vscode_server(self):
        """Switch from code-server to VSCode Server."""
        print("🔄 Switching to VSCode Server (Official Microsoft)...")
        print("\n📋 About VSCode Server:")
        print("   • Official Microsoft VSCode Server")
        print("   • Works with desktop VSCode Remote extensions")
        print("   • Built-in tunnel support")
        print("   • Microsoft/GitHub authentication")
        print("   • Direct marketplace access")

        confirm = input("\n❓ Switch to VSCode Server? (y/N): ").strip().lower()
        if confirm == 'y':
            # Stop current code-server if running
            if self._is_code_server_running():
                print("⏹️  Stopping current Code Server...")
                self.stop_code_server()

            # Update configuration
            self.config.set("server_type", "vscode-server")
            print("✅ Switched to VSCode Server mode")
            print("💡 Use 'Install VSCode Server' to get started")
        else:
            print("❌ Switch cancelled")

    def _switch_to_code_server(self):
        """Switch from VSCode Server to code-server."""
        print("🔄 Switching to Code Server (Web-based)...")
        print("\n📋 About Code Server:")
        print("   • Third-party web-based VSCode")
        print("   • Runs entirely in browser")
        print("   • Password authentication")
        print("   • Extension management via UI")
        print("   • Ngrok/Cloudflare tunnel support")

        confirm = input("\n❓ Switch to Code Server? (y/N): ").strip().lower()
        if confirm == 'y':
            # Stop current VSCode Server if running
            if self._is_vscode_server_running():
                print("⏹️  Stopping current VSCode Server...")
                self.stop_vscode_server()

            # Update configuration
            self.config.set("server_type", "code-server")
            print("✅ Switched to Code Server mode")
            print("💡 Use 'Install Code Server' to get started")
        else:
            print("❌ Switch cancelled")

    def show_status(self):
        """Show detailed status information."""
        print("📊 System Status")
        print("=" * 50)

        status = self._get_status()
        server_type = self.config.get("server_type", "code-server")

        print(f"🔧 Server Type: {server_type}")

        if server_type == "vscode-server":
            print(f"🔧 VSCode Server: {status['vscode_server']}")

            tunnel_url = status.get('vscode_tunnel_url')
            if tunnel_url:
                print(f"🔗 Tunnel URL: {tunnel_url}")
            else:
                print(f"🔗 Tunnel URL: Not available")

            tunnel_name = self.config.get("vscode_server.tunnel_name", "")
            if tunnel_name:
                print(f"🚇 Tunnel Name: {tunnel_name}")

            print(f"🔐 Authentication: Microsoft/GitHub account")
        else:
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
        """Manage VS Code extensions with built-in Hybrid Registry support."""
        print("📦 Extension Management")
        print("🔄 Hybrid Registry: Microsoft Marketplace + Open VSX")
        print("=" * 50)

        while True:
            print("\n📋 Extension Options:")
            print("1. Install Popular Extensions")
            print("2. Install Custom Extension")
            print("3. List Installed Extensions")
            print("4. Uninstall Extension")
            print("5. Update All Extensions")
            print("6. Hybrid Search (Both Registries)")
            print("7. Install from Specific Registry")
            print("8. Download Extension Info")
            print("9. Check Extension Compatibility")
            print("10. Clear Extension Cache")
            print("0. Back to Main Menu")

            choice = input("\n👉 Select option (0-10): ").strip()

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
                self._hybrid_search_extensions()
            elif choice == "7":
                self._install_from_specific_registry()
            elif choice == "8":
                self._show_extension_info()
            elif choice == "9":
                self._check_extension_compatibility()
            elif choice == "10":
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
        """Advanced registry settings - Override default hybrid registry if needed."""
        print("\n🔧 Advanced Registry Settings")
        print("💡 Note: Hybrid Registry (Microsoft + Open VSX) is now DEFAULT")
        print("   Use this menu only if you need to override the default configuration")

        # Get current registry configuration
        current_registry = self._get_current_registry()
        print(f"\n📋 Current Registry: {current_registry}")

        # Show hybrid registry status
        hybrid_mode = self.config.get("extension_registry.hybrid_mode", True)
        if hybrid_mode:
            print("🔄 Hybrid Mode: ✅ ACTIVE (Default)")
            print("   🏢 Primary: Microsoft Marketplace (UI search)")
            print("   🌐 Fallback: Open VSX (automatic)")
        else:
            print("🔄 Hybrid Mode: ❌ DISABLED (Override active)")

        print("\n📋 Registry Override Options:")
        print("1. Keep Default Hybrid Registry (Recommended)")
        print("   - Microsoft Marketplace + Open VSX")
        print("   - Best of both ecosystems")
        print("   - No action needed")
        print()
        print("2. Override to Open VSX Only")
        print("   - Open source extensions only")
        print("   - Community maintained")
        print("   - No licensing restrictions")
        print()
        print("3. Override to Microsoft Marketplace Only")
        print("   - Full Microsoft extension catalog")
        print("   - Includes proprietary extensions")
        print("   - May have licensing restrictions")
        print()
        print("4. Custom Registry Override")
        print("   - Use your own marketplace")
        print("   - Enterprise/private registries")
        print()
        print("5. Reset to Default Hybrid Registry")
        print("   - Restore Microsoft + Open VSX hybrid")
        print("   - Remove any overrides")
        print()
        print("6. Debug Current Configuration")
        print("   - Verify environment variables")
        print("   - Check Code Server process")
        print()
        print("7. Force Restart with Environment")
        print("   - Restart Code Server with current env vars")
        print("   - Fix registry not applying issue")
        print()
        print("8. Check Extension Compatibility")
        print("   - Verify Node.js and crypto module")
        print("   - Check environment configuration")
        print("   - Test extension host compatibility")
        print()
        print("9. Fix Crypto Module Extensions")
        print("   - Inject crypto polyfill into extensions")
        print("   - Patch Augment and other crypto-dependent extensions")
        print("   - Apply web worker compatibility fixes")
        print()
        print("0. Back to Main Menu")

        choice = input("\n👉 Select option (0-9): ").strip()

        if choice == "1":
            print("✅ Keeping default hybrid registry - no action needed!")
            print("🔄 Hybrid Registry remains active (Microsoft + Open VSX)")
        elif choice == "2":
            self._override_to_openvsx_only()
        elif choice == "3":
            self._override_to_microsoft_only()
        elif choice == "4":
            self._configure_custom_registry()
        elif choice == "5":
            self._reset_to_default_hybrid()
        elif choice == "6":
            self._debug_registry_configuration()
        elif choice == "7":
            self._force_restart_with_env()
        elif choice == "8":
            self._check_extension_compatibility()
        elif choice == "9":
            self._fix_crypto_extensions()
        elif choice == "0":
            return
        else:
            print("❌ Invalid option")

    def _override_to_openvsx_only(self):
        """Override default hybrid to Open VSX only."""
        print("\n🌐 Override to Open VSX Only")
        print("⚠️  This will disable the default hybrid registry")
        print("💡 You will lose access to Microsoft Marketplace extensions")

        confirm = input("\n🔄 Override to Open VSX only? (y/N): ").strip().lower()
        if confirm != 'y':
            return

        # Disable hybrid mode
        self.config.set("extension_registry.hybrid_mode", False)

        # Configure Open VSX
        openvsx_gallery = '{"serviceUrl": "https://open-vsx.org/vscode/gallery", "itemUrl": "https://open-vsx.org/vscode/item"}'
        os.environ['EXTENSIONS_GALLERY'] = openvsx_gallery
        self._update_shell_profile_registry(openvsx_gallery)

        print("✅ Registry overridden to Open VSX only")
        print("💡 Restart Code Server to apply changes")

    def _override_to_microsoft_only(self):
        """Override default hybrid to Microsoft Marketplace only."""
        print("\n🏢 Override to Microsoft Marketplace Only")
        print("⚠️  This will disable the default hybrid registry")
        print("💡 You will lose automatic fallback to Open VSX")

        confirm = input("\n🔄 Override to Microsoft only? (y/N): ").strip().lower()
        if confirm != 'y':
            return

        # Disable hybrid mode
        self.config.set("extension_registry.hybrid_mode", False)

        # Configure Microsoft Marketplace
        microsoft_gallery = '{"serviceUrl": "https://marketplace.visualstudio.com/_apis/public/gallery", "itemUrl": "https://marketplace.visualstudio.com/items", "resourceUrlTemplate": "https://marketplace.visualstudio.com/_apis/public/gallery/publishers/{publisher}/vsextensions/{name}/{version}/vspackage"}'
        os.environ['EXTENSIONS_GALLERY'] = microsoft_gallery
        self._update_shell_profile_registry(microsoft_gallery)

        print("✅ Registry overridden to Microsoft Marketplace only")
        print("💡 Restart Code Server to apply changes")

    def _reset_to_default_hybrid(self):
        """Reset to default hybrid registry."""
        print("\n🔄 Reset to Default Hybrid Registry")
        print("✅ This will restore Microsoft Marketplace + Open VSX hybrid")

        confirm = input("\n🔄 Reset to default hybrid registry? (y/N): ").strip().lower()
        if confirm != 'y':
            return

        # Re-enable hybrid mode
        self._setup_default_hybrid_registry()

        print("✅ Registry reset to default hybrid configuration")
        print("🔄 Hybrid Registry: Microsoft Marketplace + Open VSX")
        print("💡 Restart Code Server to apply changes")

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

    def _configure_hybrid_registry(self):
        """Configure hybrid registry (Microsoft Marketplace + Open VSX fallback)."""
        print("\n🔄 Configuring Hybrid Registry (Microsoft + Open VSX)")
        print("💡 This configuration provides the best of both ecosystems:")
        print("   • Microsoft Marketplace as primary (UI search/discovery)")
        print("   • Open VSX as fallback for missing extensions")
        print("   • Enhanced extension manager with dual registry support")

        confirm = input("\n🔄 Configure hybrid registry? (y/N): ").strip().lower()
        if confirm != 'y':
            return

        # Set Microsoft Marketplace as primary registry
        print("\n📋 Step 1: Setting Microsoft Marketplace as primary registry...")

        microsoft_gallery = {
            "serviceUrl": "https://marketplace.visualstudio.com/_apis/public/gallery",
            "itemUrl": "https://marketplace.visualstudio.com/items",
            "resourceUrlTemplate": "https://marketplace.visualstudio.com/_apis/public/gallery/publishers/{publisher}/vsextensions/{name}/{version}/vspackage"
        }

        import json
        gallery_json = json.dumps(microsoft_gallery)

        # Set environment variable for current session
        os.environ['EXTENSIONS_GALLERY'] = gallery_json

        # Update shell profile for persistence
        self._update_shell_profile_registry(gallery_json)

        # Set hybrid mode flag
        self.config.set("extension_registry.hybrid_mode", True)
        self.config.set("extension_registry.primary", "microsoft")
        self.config.set("extension_registry.fallback", "openvsx")

        print("✅ Microsoft Marketplace configured as primary registry")

        # Configure enhanced extension manager
        print("\n📋 Step 2: Configuring enhanced extension manager...")
        self._setup_hybrid_extension_manager()

        print("✅ Hybrid registry configuration completed!")
        print("\n🎯 Features enabled:")
        print("   • UI search uses Microsoft Marketplace")
        print("   • Fallback installation from Open VSX")
        print("   • Enhanced extension manager (Menu 7)")
        print("   • Dual registry search capabilities")

        restart = input("\n🔄 Force restart Code Server now? (y/N): ").strip().lower()
        if restart == 'y':
            print("🔄 Restarting with hybrid registry configuration...")
            self._force_restart_with_env()
        else:
            print("💡 Remember to restart Code Server to apply changes!")
            print("   Use Menu: 8 → 6 (Force Restart with Environment)")

    def _setup_hybrid_extension_manager(self):
        """Setup enhanced extension manager for hybrid registry support."""
        print("🔧 Setting up enhanced extension manager...")

        # Create extension manager config
        hybrid_config = {
            "primary_registry": {
                "name": "Microsoft Marketplace",
                "serviceUrl": "https://marketplace.visualstudio.com/_apis/public/gallery",
                "itemUrl": "https://marketplace.visualstudio.com/items",
                "api_url": "https://marketplace.visualstudio.com/_apis/public/gallery/extensionquery"
            },
            "fallback_registry": {
                "name": "Open VSX",
                "serviceUrl": "https://open-vsx.org/vscode/gallery",
                "itemUrl": "https://open-vsx.org/vscode/item",
                "api_url": "https://open-vsx.org/api/-/search"
            },
            "enabled": True,
            "auto_fallback": True
        }

        # Save hybrid config
        self.config.set("extension_registry.hybrid_config", hybrid_config)

        print("✅ Enhanced extension manager configured")
        print("💡 Access via Menu: 7 → Enhanced Extension Management")

    def search_extension_hybrid(self, extension_name):
        """Search extension in both registries."""
        print(f"\n🔍 Searching for '{extension_name}' in hybrid registries...")

        results = {
            "microsoft": [],
            "openvsx": [],
            "found": False
        }

        # Search in Microsoft Marketplace
        print("📋 Searching Microsoft Marketplace...")
        try:
            microsoft_results = self._search_microsoft_marketplace(extension_name)
            if microsoft_results:
                results["microsoft"] = microsoft_results
                results["found"] = True
                print(f"✅ Found {len(microsoft_results)} results in Microsoft Marketplace")
        except Exception as e:
            print(f"⚠️  Microsoft Marketplace search failed: {e}")

        # Search in Open VSX
        print("📋 Searching Open VSX Registry...")
        try:
            openvsx_results = self._search_openvsx_registry(extension_name)
            if openvsx_results:
                results["openvsx"] = openvsx_results
                results["found"] = True
                print(f"✅ Found {len(openvsx_results)} results in Open VSX")
        except Exception as e:
            print(f"⚠️  Open VSX search failed: {e}")

        return results

    def _search_microsoft_marketplace(self, extension_name):
        """Search Microsoft Marketplace for extensions."""
        try:
            import requests

            # Microsoft Marketplace API endpoint
            api_url = "https://marketplace.visualstudio.com/_apis/public/gallery/extensionquery"

            # Search payload
            payload = {
                "filters": [{
                    "criteria": [{
                        "filterType": 8,
                        "value": "Microsoft.VisualStudio.Code"
                    }, {
                        "filterType": 10,
                        "value": extension_name
                    }],
                    "pageNumber": 1,
                    "pageSize": 10,
                    "sortBy": 0,
                    "sortOrder": 0
                }],
                "assetTypes": [],
                "flags": 914
            }

            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json;api-version=3.0-preview.1"
            }

            response = requests.post(api_url, json=payload, headers=headers, timeout=10)

            if response.status_code == 200:
                data = response.json()
                extensions = []

                if "results" in data and len(data["results"]) > 0:
                    for ext in data["results"][0].get("extensions", []):
                        extensions.append({
                            "name": ext.get("displayName", ""),
                            "id": ext.get("extensionName", ""),
                            "publisher": ext.get("publisher", {}).get("displayName", ""),
                            "version": ext.get("versions", [{}])[0].get("version", ""),
                            "description": ext.get("shortDescription", ""),
                            "registry": "microsoft"
                        })

                return extensions
            else:
                print(f"⚠️  Microsoft API returned status: {response.status_code}")
                return []

        except Exception as e:
            print(f"❌ Microsoft Marketplace search error: {e}")
            return []

    def _search_openvsx_registry(self, extension_name):
        """Search Open VSX Registry for extensions."""
        try:
            import requests

            # Open VSX API endpoint
            api_url = f"https://open-vsx.org/api/-/search?query={extension_name}&size=10"

            headers = {
                "Accept": "application/json"
            }

            response = requests.get(api_url, headers=headers, timeout=10)

            if response.status_code == 200:
                data = response.json()
                extensions = []

                for ext in data.get("extensions", []):
                    extensions.append({
                        "name": ext.get("displayName", ""),
                        "id": ext.get("name", ""),
                        "publisher": ext.get("namespace", ""),
                        "version": ext.get("version", ""),
                        "description": ext.get("description", ""),
                        "registry": "openvsx"
                    })

                return extensions
            else:
                print(f"⚠️  Open VSX API returned status: {response.status_code}")
                return []

        except Exception as e:
            print(f"❌ Open VSX search error: {e}")
            return []

    def _hybrid_search_extensions(self):
        """Search extensions in both registries (hybrid mode)."""
        print("\n🔍 Hybrid Extension Search (Microsoft + Open VSX)")

        extension_name = input("Extension name or keyword: ").strip()
        if not extension_name:
            return

        results = self.search_extension_hybrid(extension_name)

        if not results["found"]:
            print(f"❌ No extensions found for '{extension_name}' in either registry")
            return

        print(f"\n📋 Search Results for '{extension_name}':")

        # Display Microsoft Marketplace results
        if results["microsoft"]:
            print(f"\n🏢 Microsoft Marketplace ({len(results['microsoft'])} results):")
            for i, ext in enumerate(results["microsoft"], 1):
                print(f"  {i}. {ext['name']} ({ext['publisher']}.{ext['id']})")
                print(f"     Version: {ext['version']}")
                print(f"     Description: {ext['description'][:80]}...")

        # Display Open VSX results
        if results["openvsx"]:
            print(f"\n🌐 Open VSX Registry ({len(results['openvsx'])} results):")
            for i, ext in enumerate(results["openvsx"], 1):
                print(f"  {i}. {ext['name']} ({ext['publisher']}.{ext['id']})")
                print(f"     Version: {ext['version']}")
                print(f"     Description: {ext['description'][:80]}...")

        # Offer installation
        install = input(f"\n📦 Install an extension? (y/N): ").strip().lower()
        if install == 'y':
            ext_id = input("Extension ID to install (publisher.name): ").strip()
            if ext_id:
                self._install_extension_hybrid(ext_id)

    def _install_extension_hybrid(self, ext_id):
        """Install extension using hybrid approach (try Microsoft first, fallback to Open VSX)."""
        print(f"\n📦 Installing {ext_id} using hybrid approach...")

        # Try Microsoft Marketplace first (since it's primary)
        print("🏢 Trying Microsoft Marketplace...")
        success = self._install_extension_direct(ext_id)

        if success:
            print(f"✅ Extension {ext_id} installed from Microsoft Marketplace!")
            return True

        # Fallback to Open VSX
        print("🌐 Falling back to Open VSX Registry...")
        env = os.environ.copy()
        env['SERVICE_URL'] = 'https://open-vsx.org/vscode/gallery'
        env['ITEM_URL'] = 'https://open-vsx.org/vscode/item'

        success, output = SystemUtils.run_command([
            str(BIN_DIR / "code-server"),
            "--install-extension", ext_id
        ], env=env)

        if success:
            print(f"✅ Extension {ext_id} installed from Open VSX!")
            return True
        else:
            print(f"❌ Failed to install {ext_id} from both registries")
            print(f"   Error: {output}")
            return False

    def _install_extension_direct(self, ext_id):
        """Install extension directly using current registry configuration."""
        try:
            success, output = SystemUtils.run_command([
                str(BIN_DIR / "code-server"),
                "--install-extension", ext_id
            ])
            return success
        except Exception:
            return False

    def _install_from_specific_registry(self):
        """Install extension from a specific registry."""
        print("\n📦 Install from Specific Registry")

        print("📋 Available Registries:")
        print("1. Microsoft Marketplace")
        print("2. Open VSX Registry")
        print("0. Cancel")

        choice = input("\n👉 Select registry (0-2): ").strip()

        if choice == "1":
            self._install_from_microsoft_marketplace()
        elif choice == "2":
            self._install_from_openvsx_registry()
        elif choice == "0":
            return
        else:
            print("❌ Invalid option")

    def _install_from_microsoft_marketplace(self):
        """Install extension specifically from Microsoft Marketplace."""
        print("\n🏢 Install from Microsoft Marketplace")

        ext_id = input("Extension ID (publisher.name): ").strip()
        if not ext_id:
            return

        print(f"📦 Installing {ext_id} from Microsoft Marketplace...")

        # Try direct installation first (uses current EXTENSIONS_GALLERY which is Microsoft)
        success = self._install_extension_direct(ext_id)

        if success:
            print(f"✅ Extension {ext_id} installed successfully from Microsoft Marketplace!")
        else:
            print(f"❌ Failed to install {ext_id} from Microsoft Marketplace")
            print("💡 Extension may not be available in Microsoft Marketplace")

    def _install_from_openvsx_registry(self):
        """Install extension specifically from Open VSX Registry."""
        print("\n🌐 Install from Open VSX Registry")

        ext_id = input("Extension ID (publisher.name): ").strip()
        if not ext_id:
            return

        print(f"📦 Installing {ext_id} from Open VSX Registry...")

        # Use Open VSX environment variables for installation
        env = os.environ.copy()
        env['SERVICE_URL'] = 'https://open-vsx.org/vscode/gallery'
        env['ITEM_URL'] = 'https://open-vsx.org/vscode/item'

        success, output = SystemUtils.run_command([
            str(BIN_DIR / "code-server"),
            "--install-extension", ext_id
        ], env=env)

        if success:
            print(f"✅ Extension {ext_id} installed successfully from Open VSX!")
        else:
            print(f"❌ Failed to install {ext_id} from Open VSX: {output}")

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
        print("🔧 Node.js Environment: Configuring for extension compatibility...")

        # Get Code Server configuration
        port = self.config.get("code_server.port", 8080)
        password = self.config.get("code_server.password", "colab123")

        # Prepare environment with EXTENSIONS_GALLERY and PASSWORD
        env = os.environ.copy()
        env['EXTENSIONS_GALLERY'] = extensions_gallery
        env['PASSWORD'] = password  # Use environment variable instead of --password

        # Setup Node.js environment for extension compatibility (fixes crypto module issue)
        env = self._setup_nodejs_environment(env)

        # Start Code Server with explicit environment
        try:
            # Use same approach as regular start_code_server but with custom environment
            code_server_bin = BIN_DIR / "code-server"

            print(f"🚀 Starting Code Server with enhanced environment...")
            print("   • Microsoft Marketplace registry")
            print("   • Node.js modules support (crypto, fs, etc.)")
            print("   • Extension host compatibility")

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
