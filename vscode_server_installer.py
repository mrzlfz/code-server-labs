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
from pathlib import Path
from urllib.parse import urlparse

class VSCodeServerInstaller:
    def __init__(self):
        self.home_dir = Path.home()
        self.config_dir = self.home_dir / ".config" / "vscode-server-installer"
        self.install_dir = self.home_dir / ".local" / "lib" / "vscode-server"
        self.bin_dir = self.home_dir / ".local" / "bin"
        self.config_file = self.config_dir / "config.json"
        
        # Buat direktori yang diperlukan
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.install_dir.mkdir(parents=True, exist_ok=True)
        self.bin_dir.mkdir(parents=True, exist_ok=True)
        
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
        
    def save_config(self):
        """Simpan konfigurasi ke file"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"❌ Error saving config: {e}")
    
    def run_command(self, command, shell=True, capture_output=False):
        """Jalankan command dengan error handling"""
        try:
            if capture_output:
                result = subprocess.run(command, shell=shell, capture_output=True, text=True)
                return result.returncode == 0, result.stdout.strip(), result.stderr.strip()
            else:
                result = subprocess.run(command, shell=shell)
                return result.returncode == 0, "", ""
        except Exception as e:
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
        """Setup VSCode Server tunnel"""
        print("\n🔧 Setting up VSCode Server Tunnel...")
        
        if not self.config.get("server_installed", False):
            print("❌ VSCode Server belum terinstall! Install terlebih dahulu.")
            return False
        
        tunnel_name = input("📝 Masukkan nama tunnel (contoh: my-dev-server): ").strip()
        if not tunnel_name:
            print("❌ Nama tunnel tidak boleh kosong!")
            return False
        
        self.config["tunnel_name"] = tunnel_name
        self.save_config()
        
        code_path = self.bin_dir / "code"
        
        print(f"🔐 Melakukan login dan setup tunnel '{tunnel_name}'...")
        print("📋 Ikuti instruksi untuk login dengan akun Microsoft/GitHub Anda")
        
        # Setup tunnel
        command = f'"{code_path}" tunnel --name "{tunnel_name}" --accept-server-license-terms'
        success, stdout, stderr = self.run_command(command, capture_output=False)
        
        if success:
            print("✅ Tunnel berhasil dikonfigurasi!")
            self.config["tunnel_configured"] = True
            self.save_config()
            return True
        else:
            print(f"❌ Error setting up tunnel: {stderr}")
            return False
    
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
            print("0. 🚪 Exit")
            
            choice = input("\n🎯 Pilih menu (0-9): ").strip()
            
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