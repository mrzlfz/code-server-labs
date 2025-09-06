#!/usr/bin/env python3
"""
VSCode Server Interactive Installer
Installer interaktif untuk VSCode Server dengan extension Microsoft Store
"""

import os
import sys
import json
import subprocess
import requests
import tarfile
import shutil
import time
import logging
import threading
from pathlib import Path
from urllib.parse import urlparse
from datetime import datetime

class VSCodeServerInstaller:
    def __init__(self):
        self.home_dir = Path.home()
        self.config_dir = self.home_dir / ".config" / "vscode-server-installer"
        self.install_dir = self.home_dir / ".local" / "lib" / "vscode-server"
        self.bin_dir = self.home_dir / ".local" / "bin"
        self.config_file = self.config_dir / "config.json"
        self.log_file = self.config_dir / "auth_debug.log"
        
        # Buat direktori yang diperlukan
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.install_dir.mkdir(parents=True, exist_ok=True)
        self.bin_dir.mkdir(parents=True, exist_ok=True)
        
        # Setup logging
        self.setup_logging()
        
        # Load konfigurasi
        self.config = self.load_config()
        
    def load_config(self):
        """Load konfigurasi dari file"""
        default_config = {
            "tunnel_name": "",
            "extensions": [
                "ms-python.python",
                "ms-python.vscode-pylance", 
                "ms-toolsai.jupyter",
                "ms-vscode.vscode-json",
                "redhat.vscode-yaml",
                "ms-vscode.theme-tomorrow-night-blue",
                "PKief.material-icon-theme"
            ],
            "server_installed": False,
            "tunnel_configured": False
        }
        
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                # Merge dengan default untuk key yang hilang
                for key, value in default_config.items():
                    if key not in config:
                        config[key] = value
                return config
            except Exception as e:
                print(f"❌ Error loading config: {e}")
                return default_config
        return default_config
    
    def setup_logging(self):
        """Setup logging system untuk debug authentication"""
        # Setup logger
        self.logger = logging.getLogger('vscode_auth')
        self.logger.setLevel(logging.DEBUG)
        
        # Remove existing handlers
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)
        
        # File handler
        file_handler = logging.FileHandler(self.log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        
        self.logger.info("=== VSCode Auth Debug Session Started ===")
        
    def save_config(self):
        """Simpan konfigurasi ke file"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"❌ Error saving config: {e}")
    
    def run_command(self, command, shell=True, capture_output=False, log_output=True):
        """Jalankan command dengan error handling dan logging"""
        if hasattr(self, 'logger') and log_output:
            self.logger.debug(f"Executing command: {command}")
        
        try:
            if capture_output:
                result = subprocess.run(command, shell=shell, capture_output=True, text=True)
                success = result.returncode == 0
                stdout = result.stdout.strip()
                stderr = result.stderr.strip()
                
                if hasattr(self, 'logger') and log_output:
                    self.logger.debug(f"Command exit code: {result.returncode}")
                    if stdout:
                        self.logger.debug(f"STDOUT: {stdout}")
                    if stderr:
                        self.logger.debug(f"STDERR: {stderr}")
                
                return success, stdout, stderr
            else:
                result = subprocess.run(command, shell=shell)
                success = result.returncode == 0
                
                if hasattr(self, 'logger') and log_output:
                    self.logger.debug(f"Command exit code: {result.returncode}")
                
                return success, "", ""
        except Exception as e:
            if hasattr(self, 'logger') and log_output:
                self.logger.error(f"Exception running command: {e}")
            return False, "", str(e)
    
    def download_vscode_server(self):
        """Download VSCode Server dari Microsoft"""
        print("📥 Downloading VSCode Server...")
        
        # Deteksi arsitektur sistem
        arch_map = {
            'x86_64': 'x64',
            'aarch64': 'arm64',
            'armv7l': 'armhf'
        }
        
        import platform
        machine = platform.machine()
        arch = arch_map.get(machine, 'x64')
        
        # URL download VSCode Server CLI
        download_url = f"https://update.code.visualstudio.com/latest/cli-alpine-{arch}/stable"
        
        try:
            response = requests.get(download_url, stream=True)
            response.raise_for_status()
            
            # Download ke file temporary
            temp_file = self.install_dir / "vscode-server.tar.gz"
            with open(temp_file, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            print("📦 Extracting VSCode Server...")
            
            # Extract file
            with tarfile.open(temp_file, 'r:gz') as tar:
                tar.extractall(self.install_dir)
            
            # Pindahkan binary ke bin directory
            binary_path = None
            for item in self.install_dir.rglob("code"):
                if item.is_file() and os.access(item, os.X_OK):
                    binary_path = item
                    break
            
            if binary_path:
                target_path = self.bin_dir / "code"
                shutil.copy2(binary_path, target_path)
                os.chmod(target_path, 0o755)
                
                # Cleanup
                temp_file.unlink()
                
                print("✅ VSCode Server berhasil diinstall!")
                self.config["server_installed"] = True
                self.save_config()
                return True
            else:
                print("❌ Binary VSCode Server tidak ditemukan!")
                return False
                
        except Exception as e:
            print(f"❌ Error downloading VSCode Server: {e}")
            return False
    
    def setup_tunnel(self):
        """Setup VSCode Server tunnel dengan detailed logging"""
        print("\n🔧 Setting up VSCode Server Tunnel...")
        self.logger.info("=== Starting Tunnel Setup Process ===")
        
        if not self.config.get("server_installed", False):
            print("❌ VSCode Server belum terinstall! Install terlebih dahulu.")
            self.logger.error("VSCode Server not installed")
            return False
        
        tunnel_name = input("📝 Masukkan nama tunnel (contoh: my-dev-server): ").strip()
        if not tunnel_name:
            print("❌ Nama tunnel tidak boleh kosong!")
            self.logger.error("Empty tunnel name provided")
            return False
        
        self.logger.info(f"Tunnel name: {tunnel_name}")
        self.config["tunnel_name"] = tunnel_name
        self.save_config()
        
        code_path = self.bin_dir / "code"
        self.logger.info(f"Code path: {code_path}")
        
        # Verify code binary exists and is executable
        if not code_path.exists():
            print(f"❌ Code binary tidak ditemukan di: {code_path}")
            self.logger.error(f"Code binary not found at: {code_path}")
            return False
        
        if not os.access(code_path, os.X_OK):
            print(f"❌ Code binary tidak executable: {code_path}")
            self.logger.error(f"Code binary not executable: {code_path}")
            return False
        
        print(f"🔐 Melakukan login dan setup tunnel '{tunnel_name}'...")
        print("📋 Ikuti instruksi untuk login dengan akun Microsoft/GitHub Anda")
        print(f"📝 Debug log akan disimpan di: {self.log_file}")
        
        self.logger.info("Starting authentication process...")
        
        # Setup tunnel dengan logging real-time dan automated input
        command = f'"{code_path}" tunnel --name "{tunnel_name}" --accept-server-license-terms'
        
        try:
            self.logger.info("Executing tunnel command...")
            self.logger.debug(f"Full command: {command}")
            
            # Start process dengan stdin untuk automated input
            process = subprocess.Popen(
                command,
                shell=True,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1
            )
            
            self.logger.info(f"Process started with PID: {process.pid}")
            
            # Monitor output real-time dengan timeout dan automated input
            output_lines = []
            timeout_seconds = 300  # 5 menit timeout
            start_time = time.time()
            auth_method_sent = False
            
            print("🔍 Monitoring authentication process...")
            print("📊 Real-time status akan ditampilkan...")
            print("🤖 Auto-selecting GitHub Account when prompted...")
            
            while True:
                # Check timeout
                if time.time() - start_time > timeout_seconds:
                    self.logger.warning(f"Process timeout after {timeout_seconds} seconds")
                    print(f"⏰ Timeout setelah {timeout_seconds} detik!")
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()
                    return False
                
                # Read output
                try:
                    line = process.stdout.readline()
                    if line:
                        line = line.strip()
                        output_lines.append(line)
                        
                        # Log output
                        if line:
                            self.logger.info(f"Process output: {line}")
                            
                            # Detect dan handle authentication method selection
                            if "How would you like to log in" in line and not auth_method_sent:
                                print(f"🔑 Detected login prompt, auto-selecting GitHub Account...")
                                self.logger.info("Authentication method selection prompt detected - sending GitHub selection")
                                # Send down arrow to select GitHub, then Enter
                                process.stdin.write("\x1b[B\n")  # Down arrow + Enter
                                process.stdin.flush()
                                auth_method_sent = True
                                continue
                            
                            # Filter out repetitive menu display lines
                            if ("Microsoft Account" in line or "GitHub Account" in line or 
                                "[2A" in line or "[2K" in line or "[1B" in line):
                                if not auth_method_sent:
                                    # Only show first few menu displays
                                    if output_lines.count(line) < 3:
                                        print(f"📋 {line}")
                                continue
                            
                            # Show important status updates
                            if "github.com/login/device" in line:
                                print(f"🌐 {line}")
                                self.logger.info("GitHub device login URL detected")
                            elif "use code" in line.lower():
                                print(f"🔢 {line}")
                                self.logger.info("Device code detected")
                            elif "Open this link" in line or "open the link" in line.lower():
                                print(f"🔗 {line}")
                                self.logger.info("Authentication link detected")
                            elif "successfully" in line.lower():
                                print(f"✅ {line}")
                                self.logger.info("Success message detected")
                            elif "error" in line.lower():
                                print(f"❌ {line}")
                                self.logger.error(f"Error detected in output: {line}")
                            elif "waiting" in line.lower():
                                print(f"⏳ {line}")
                                self.logger.info("Waiting status detected")
                            elif "To grant access" in line:
                                print(f"🔐 {line}")
                                self.logger.info("Access grant instruction detected")
                                print("👉 Please complete authentication in your browser")
                                print("⏳ Waiting for authentication completion...")
                            elif "tunnel" in line.lower() and "ready" in line.lower():
                                print(f"🚀 {line}")
                                self.logger.info("Tunnel ready message detected")
                            elif "tunnel" in line.lower() and ("started" in line.lower() or "running" in line.lower()):
                                print(f"✅ {line}")
                                self.logger.info("Tunnel started successfully")
                            elif "authentication" in line.lower() and ("complete" in line.lower() or "successful" in line.lower()):
                                print(f"✅ {line}")
                                self.logger.info("Authentication completed")
                            elif "logged in" in line.lower():
                                print(f"✅ {line}")
                                self.logger.info("Login confirmation detected")
                            elif line and not any(x in line for x in ["*", "[?25l", "❯", "[2025-"]):
                                # Show other meaningful output, filtering UI artifacts and timestamps
                                print(f"📄 {line}")
                            elif "[2025-" in line and ("info" in line.lower() or "error" in line.lower()):
                                # Show timestamped info/error messages but clean format
                                clean_line = line.split("] ")[-1] if "] " in line else line
                                print(f"ℹ️  {clean_line}")
                                self.logger.info(f"Timestamped message: {clean_line}")
                    
                    # Check if process is still running
                    poll = process.poll()
                    if poll is not None:
                        self.logger.info(f"Process finished with exit code: {poll}")
                        
                        # Read any remaining output
                        remaining_output = process.stdout.read()
                        if remaining_output:
                            for remaining_line in remaining_output.split('\n'):
                                if remaining_line.strip():
                                    output_lines.append(remaining_line.strip())
                                    self.logger.info(f"Final output: {remaining_line.strip()}")
                        
                        if poll == 0:
                            print("✅ Tunnel berhasil dikonfigurasi!")
                            self.logger.info("Tunnel setup completed successfully")
                            self.config["tunnel_configured"] = True
                            self.save_config()
                            return True
                        else:
                            print(f"❌ Tunnel setup gagal dengan exit code: {poll}")
                            self.logger.error(f"Tunnel setup failed with exit code: {poll}")
                            return False
                
                except Exception as e:
                    self.logger.error(f"Error reading process output: {e}")
                    break
                
                time.sleep(0.1)  # Small delay untuk mengurangi CPU usage
                
        except Exception as e:
            self.logger.error(f"Exception during tunnel setup: {e}")
            print(f"❌ Error setting up tunnel: {e}")
            return False
        
        finally:
            # Cleanup jika process masih running
            try:
                if 'process' in locals() and process.poll() is None:
                    self.logger.info("Terminating process...")
                    process.terminate()
                    process.wait(timeout=5)
            except:
                pass
    
    def analyze_auth_logs(self):
        """Analyze authentication logs untuk troubleshooting"""
        print("\n🔍 Analyzing Authentication Logs...")
        
        if not self.log_file.exists():
            print("❌ Log file tidak ditemukan!")
            return
        
        try:
            with open(self.log_file, 'r', encoding='utf-8') as f:
                logs = f.read()
            
            print(f"📂 Log file: {self.log_file}")
            print(f"📊 Log size: {len(logs)} characters")
            
            # Analisis patterns
            patterns_to_check = {
                "Authentication started": "Starting authentication process",
                "Device code shown": "use code",
                "GitHub URL shown": "github.com/login/device",
                "Waiting detected": "waiting",
                "Success messages": "successfully",
                "Error messages": "error",
                "Process timeout": "timeout",
                "Authentication method": "How would you like to log in"
            }
            
            print("\n📋 Pattern Analysis:")
            for description, pattern in patterns_to_check.items():
                count = logs.lower().count(pattern.lower())
                if count > 0:
                    print(f"  ✅ {description}: {count} occurrences")
                else:
                    print(f"  ❌ {description}: Not found")
            
            # Tampilkan last 10 lines
            lines = logs.strip().split('\n')
            print(f"\n📄 Last 10 log entries:")
            for line in lines[-10:]:
                if line.strip():
                    print(f"  {line}")
            
            # Recommendations
            print(f"\n💡 Troubleshooting Recommendations:")
            if "timeout" in logs.lower():
                print("  🔄 Process timed out - try increasing timeout or check network")
            if "error" in logs.lower():
                print("  ❌ Errors detected - check error messages above")
            if logs.lower().count("github.com/login/device") == 0:
                print("  🌐 Device authentication URL not shown - check network connectivity")
            if logs.lower().count("successfully") == 0:
                print("  ⏳ Authentication not completed - process may be stuck")
            
        except Exception as e:
            print(f"❌ Error reading log file: {e}")
    
    def start_tunnel(self):
        """Start VSCode Server tunnel"""
        if not self.config.get("tunnel_configured", False):
            print("❌ Tunnel belum dikonfigurasi! Setup tunnel terlebih dahulu.")
            return False
        
        code_path = self.bin_dir / "code"
        tunnel_name = self.config.get("tunnel_name", "")
        
        print(f"🚀 Starting tunnel '{tunnel_name}'...")
        print("📱 Tunnel akan berjalan di background...")
        print(f"🌐 Akses melalui: https://vscode.dev/tunnel/{tunnel_name}")
        print("📱 Atau buka desktop VSCode dan connect ke tunnel")
        
        command = f'"{code_path}" tunnel --name "{tunnel_name}" --accept-server-license-terms'
        
        # Start di background menggunakan nohup
        bg_command = f"nohup {command} > {self.config_dir}/tunnel.log 2>&1 &"
        success, stdout, stderr = self.run_command(bg_command)
        
        if success:
            print("✅ Tunnel berhasil dijalankan!")
            print(f"📋 Log tersedia di: {self.config_dir}/tunnel.log")
            return True
        else:
            print(f"❌ Error starting tunnel: {stderr}")
            return False
    
    def stop_tunnel(self):
        """Stop VSCode Server tunnel"""
        print("🛑 Stopping VSCode Server tunnel...")
        
        # Kill proses code tunnel
        command = "pkill -f 'code tunnel'"
        success, stdout, stderr = self.run_command(command)
        
        if success:
            print("✅ Tunnel berhasil dihentikan!")
        else:
            print("ℹ️  Tidak ada tunnel yang berjalan")
        
        return True
    
    def install_extension(self, extension_id):
        """Install extension VSCode"""
        if not self.config.get("server_installed", False):
            print("❌ VSCode Server belum terinstall!")
            return False
        
        code_path = self.bin_dir / "code"
        
        print(f"📦 Installing extension: {extension_id}")
        command = f'"{code_path}" --install-extension "{extension_id}"'
        
        success, stdout, stderr = self.run_command(command, capture_output=True)
        
        if success:
            print(f"✅ Extension {extension_id} berhasil diinstall!")
            return True
        else:
            print(f"❌ Error installing {extension_id}: {stderr}")
            return False
    
    def install_popular_extensions(self):
        """Install extension populer"""
        print("\n📦 Installing popular extensions...")
        
        extensions = self.config.get("extensions", [])
        success_count = 0
        
        for ext in extensions:
            if self.install_extension(ext):
                success_count += 1
            time.sleep(1)  # Delay untuk menghindari rate limit
        
        print(f"\n✅ {success_count}/{len(extensions)} extensions berhasil diinstall!")
    
    def list_extensions(self):
        """List installed extensions"""
        if not self.config.get("server_installed", False):
            print("❌ VSCode Server belum terinstall!")
            return
        
        code_path = self.bin_dir / "code"
        command = f'"{code_path}" --list-extensions'
        
        success, stdout, stderr = self.run_command(command, capture_output=True)
        
        if success and stdout:
            print("\n📋 Installed Extensions:")
            for ext in stdout.split('\n'):
                if ext.strip():
                    print(f"  • {ext.strip()}")
        else:
            print("📋 Tidak ada extension yang terinstall")
    
    def show_status(self):
        """Tampilkan status sistem"""
        print("\n📊 VSCode Server Status:")
        print("=" * 40)
        
        # Status instalasi
        if self.config.get("server_installed", False):
            print("✅ VSCode Server: Terinstall")
        else:
            print("❌ VSCode Server: Belum terinstall")
        
        # Status tunnel
        if self.config.get("tunnel_configured", False):
            tunnel_name = self.config.get("tunnel_name", "")
            print(f"✅ Tunnel: Dikonfigurasi ({tunnel_name})")
        else:
            print("❌ Tunnel: Belum dikonfigurasi")
        
        # Cek apakah tunnel berjalan
        command = "pgrep -f 'code tunnel'"
        success, stdout, stderr = self.run_command(command, capture_output=True)
        
        if success and stdout:
            print("✅ Tunnel Status: Berjalan")
        else:
            print("❌ Tunnel Status: Tidak berjalan")
        
        # Informasi akses
        if self.config.get("tunnel_configured", False):
            tunnel_name = self.config.get("tunnel_name", "")
            print(f"\n🌐 URL Akses: https://vscode.dev/tunnel/{tunnel_name}")
        
        print(f"\n📁 Config Directory: {self.config_dir}")
        print(f"📁 Install Directory: {self.install_dir}")
    
    def show_menu(self):
        """Tampilkan menu utama"""
        while True:
            print("\n" + "="*50)
            print("🚀 VSCode Server Interactive Installer")
            print("="*50)
            
            print("\n📋 MENU UTAMA:")
            print("1. 📥 Install VSCode Server")
            print("2. 🔧 Setup Tunnel")
            print("3. 🚀 Start Tunnel")
            print("4. 🛑 Stop Tunnel")
            print("5. 📦 Install Popular Extensions")
            print("6. 📦 Install Custom Extension")
            print("7. 📋 List Installed Extensions")
            print("8. 📊 Show Status")
            print("9. ⚙️  Configure Extensions")
            print("10. 🔍 Analyze Auth Logs")
            print("0. 🚪 Exit")
            
            choice = input("\n🎯 Pilih menu (0-10): ").strip()
            
            if choice == "1":
                self.download_vscode_server()
            elif choice == "2":
                self.setup_tunnel()
            elif choice == "3":
                self.start_tunnel()
            elif choice == "4":
                self.stop_tunnel()
            elif choice == "5":
                self.install_popular_extensions()
            elif choice == "6":
                ext_id = input("📝 Masukkan Extension ID: ").strip()
                if ext_id:
                    self.install_extension(ext_id)
            elif choice == "7":
                self.list_extensions()
            elif choice == "8":
                self.show_status()
            elif choice == "9":
                self.configure_extensions()
            elif choice == "10":
                self.analyze_auth_logs()
            elif choice == "0":
                print("👋 Terima kasih! Sampai jumpa!")
                break
            else:
                print("❌ Pilihan tidak valid!")
            
            input("\n⏸️  Tekan Enter untuk melanjutkan...")
    
    def configure_extensions(self):
        """Konfigurasi extension list"""
        print("\n⚙️ Configure Extensions")
        print("Current extensions:")
        
        extensions = self.config.get("extensions", [])
        for i, ext in enumerate(extensions, 1):
            print(f"  {i}. {ext}")
        
        print("\nOptions:")
        print("1. Add extension")
        print("2. Remove extension")
        print("3. Reset to default")
        
        choice = input("Pilih (1-3): ").strip()
        
        if choice == "1":
            ext_id = input("Extension ID to add: ").strip()
            if ext_id and ext_id not in extensions:
                extensions.append(ext_id)
                self.config["extensions"] = extensions
                self.save_config()
                print(f"✅ Added {ext_id}")
        elif choice == "2":
            try:
                index = int(input("Nomor extension to remove: ")) - 1
                if 0 <= index < len(extensions):
                    removed = extensions.pop(index)
                    self.config["extensions"] = extensions
                    self.save_config()
                    print(f"✅ Removed {removed}")
                else:
                    print("❌ Invalid number")
            except ValueError:
                print("❌ Invalid input")
        elif choice == "3":
            self.config["extensions"] = [
                "ms-python.python",
                "ms-python.vscode-pylance", 
                "ms-toolsai.jupyter",
                "ms-vscode.vscode-json",
                "redhat.vscode-yaml",
                "ms-vscode.theme-tomorrow-night-blue",
                "PKief.material-icon-theme"
            ]
            self.save_config()
            print("✅ Reset to default extensions")

def main():
    """Main function"""
    print("🚀 Starting VSCode Server Interactive Installer...")
    
    # Check Python version
    if sys.version_info < (3, 6):
        print("❌ Python 3.6+ required!")
        sys.exit(1)
    
    # Install required packages
    required_packages = ['requests']
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            print(f"📦 Installing {package}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])
    
    # Start installer
    installer = VSCodeServerInstaller()
    installer.show_menu()

if __name__ == "__main__":
    main()