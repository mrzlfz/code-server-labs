#!/usr/bin/env python3
"""
Demo VSCode Server Installer
Contoh penggunaan VSCode Server Interactive Installer
"""

from vscode_server_installer import VSCodeServerInstaller

def demo_installation():
    """Demo instalasi VSCode Server"""
    print("🚀 Demo VSCode Server Installation")
    print("="*50)
    
    # Inisialisasi installer
    installer = VSCodeServerInstaller()
    
    # Tampilkan status awal
    print("\n📊 Status Awal:")
    installer.show_status()
    
    print("\n" + "="*50)
    print("💡 CARA PENGGUNAAN:")
    print("="*50)
    
    print("\n1️⃣ INSTALASI VSCODE SERVER:")
    print("   • Pilih menu '1' untuk download dan install VSCode Server")
    print("   • Script akan otomatis download binary yang sesuai dengan sistem")
    print("   • Binary akan disimpan di ~/.local/bin/code")
    
    print("\n2️⃣ SETUP TUNNEL:")
    print("   • Pilih menu '2' untuk setup tunnel")
    print("   • Masukkan nama tunnel (contoh: my-dev-server)")  
    print("   • Login dengan akun Microsoft/GitHub")
    print("   • Tunnel akan dikonfigurasi otomatis")
    
    print("\n3️⃣ START TUNNEL:")
    print("   • Pilih menu '3' untuk mulai tunnel")
    print("   • Tunnel akan berjalan di background")
    print("   • Akses via: https://vscode.dev/tunnel/[nama-tunnel]")
    
    print("\n4️⃣ INSTALL EXTENSIONS:")
    print("   • Pilih menu '5' untuk install extension populer:")
    print("     - ms-python.python (Python support)")
    print("     - ms-python.vscode-pylance (Python IntelliSense)")  
    print("     - ms-toolsai.jupyter (Jupyter support)")
    print("     - ms-vscode.vscode-json (JSON support)")
    print("     - redhat.vscode-yaml (YAML support)")
    print("     - ms-vscode.theme-tomorrow-night-blue (Theme)")
    print("     - PKief.material-icon-theme (Icons)")
    
    print("\n5️⃣ AKSES VSCODE:")
    print("   🌐 Via Browser: https://vscode.dev/tunnel/[nama-tunnel]")
    print("   💻 Via Desktop VSCode:")
    print("      • Install extension 'Remote - Tunnels'")
    print("      • Connect to tunnel dengan nama yang sama")
    
    print("\n" + "="*50)
    print("🔧 FITUR TAMBAHAN:")
    print("="*50)
    
    print("• 📦 Install extension custom (menu 6)")
    print("• 📋 List extension yang terinstall (menu 7)")  
    print("• 📊 Cek status sistem (menu 8)")
    print("• ⚙️  Konfigurasi extension list (menu 9)")
    print("• 🛑 Stop tunnel (menu 4)")
    
    print("\n" + "="*50)
    print("📁 LOKASI FILE:")
    print("="*50)
    
    print(f"• Config: {installer.config_dir}")
    print(f"• Install: {installer.install_dir}")  
    print(f"• Binary: {installer.bin_dir}/code")
    print(f"• Logs: {installer.config_dir}/tunnel.log")
    
    print("\n" + "="*50)
    print("🚀 JALANKAN INSTALLER:")
    print("="*50)
    
    print("python3 vscode_server_installer.py")
    
    return installer

if __name__ == "__main__":
    demo_installation()