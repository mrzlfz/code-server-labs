#!/usr/bin/env python3
"""
VSCode Server Quick Launcher
Script launcher cepat untuk VSCode Server installer
"""

import os
import sys
import subprocess

def main():
    """Main launcher function"""
    
    print("🚀 VSCode Server Quick Launcher")
    print("=" * 40)
    
    # Check if main installer exists
    installer_path = "vscode_server_installer.py"
    if not os.path.exists(installer_path):
        print(f"❌ File {installer_path} tidak ditemukan!")
        print("📥 Download script dari repository atau pastikan file ada")
        return False
    
    print("📋 Pilihan cepat:")
    print("1. 🚀 Jalankan installer lengkap (Interactive Menu)")
    print("2. 🧪 Jalankan test suite")  
    print("3. 📚 Lihat demo dan dokumentasi")
    print("4. ❓ Help & informasi")
    
    choice = input("\n🎯 Pilih (1-4): ").strip()
    
    if choice == "1":
        print("\n🚀 Launching VSCode Server Installer...")
        print("💡 Gunakan menu interaktif untuk install dan configure")
        print("-" * 50)
        os.system(f"python3 {installer_path}")
        
    elif choice == "2":
        print("\n🧪 Running Test Suite...")
        if os.path.exists("test_vscode_installer.py"):
            os.system("python3 test_vscode_installer.py")
        else:
            print("❌ File test tidak ditemukan!")
            
    elif choice == "3":
        print("\n📚 Demo & Dokumentasi...")
        if os.path.exists("demo_vscode_installer.py"):
            os.system("python3 demo_vscode_installer.py")
        else:
            print("❌ File demo tidak ditemukan!")
            
        if os.path.exists("VSCODE_INSTALLER_README.md"):
            print("\n📖 README tersedia di: VSCODE_INSTALLER_README.md")
        else:
            print("❌ README tidak ditemukan!")
            
    elif choice == "4":
        show_help()
        
    else:
        print("❌ Pilihan tidak valid!")
        return False
    
    return True

def show_help():
    """Show help information"""
    print("\n❓ VSCode Server Installer - Help")
    print("=" * 40)
    
    print("\n🎯 TUJUAN:")
    print("Install dan setup VSCode Server dengan extension Microsoft Store")
    
    print("\n📋 LANGKAH INSTALASI:")
    print("1. Jalankan: python3 install_vscode.py")
    print("2. Pilih '1' untuk installer interaktif")
    print("3. Di menu installer:")
    print("   • Menu 1: Install VSCode Server")
    print("   • Menu 2: Setup tunnel (nama + login Microsoft/GitHub)")
    print("   • Menu 3: Start tunnel")
    print("   • Menu 5: Install extension populer")
    
    print("\n🌐 AKSES VSCODE:")
    print("• Browser: https://vscode.dev/tunnel/[nama-tunnel]")
    print("• Desktop: Install extension 'Remote - Tunnels' di VSCode")
    
    print("\n📦 EXTENSION YANG DIINSTALL:")
    print("• ms-python.python - Python support")
    print("• ms-python.vscode-pylance - IntelliSense")
    print("• ms-toolsai.jupyter - Jupyter notebook")
    print("• ms-vscode.vscode-json - JSON support")
    print("• redhat.vscode-yaml - YAML support")
    print("• Themes & icons")
    
    print("\n🔧 REQUIREMENTS:")
    print("• Python 3.6+")
    print("• Internet connection")
    print("• Akun Microsoft/GitHub untuk authentication")
    
    print("\n📁 FILE YANG DIBUAT:")
    print("• Config: ~/.config/vscode-server-installer/")
    print("• Install: ~/.local/lib/vscode-server/")
    print("• Binary: ~/.local/bin/code")
    
    print("\n🆘 TROUBLESHOOTING:")
    print("• Menu 8: Cek status sistem")
    print("• Logs: ~/.config/vscode-server-installer/tunnel.log")
    print("• Test: python3 test_vscode_installer.py")
    
    print("\n📞 SUPPORT:")
    print("• Repository: https://github.com/mrzlfz/code-server-labs")
    print("• Documentation: VSCODE_INSTALLER_README.md")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Keluar dari launcher. Terima kasih!")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)