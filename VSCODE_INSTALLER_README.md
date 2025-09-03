# VSCode Server Interactive Installer

🚀 **Installer interaktif untuk VSCode Server dengan extension dari Microsoft Store**

## 📋 Fitur Utama

- **✅ Auto Installation**: Download dan install VSCode Server otomatis
- **🔧 Tunnel Setup**: Setup tunnel untuk akses remote dengan mudah
- **📦 Extension Management**: Install extension dari Microsoft Store  
- **🎯 Interactive Menu**: Interface menu yang user-friendly
- **📊 Status Monitoring**: Monitor status server dan tunnel
- **⚙️ Configuration**: Konfigurasi yang persistent dan mudah diatur

## 🚀 Quick Start

### 1. Jalankan Installer
```bash
python3 vscode_server_installer.py
```

### 2. Install VSCode Server (Menu 1)
- Script akan download VSCode Server CLI secara otomatis
- Binary akan disimpan di `~/.local/bin/code`
- Mendukung arsitektur: x64, arm64, armhf

### 3. Setup Tunnel (Menu 2)
- Masukkan nama tunnel (contoh: `my-dev-server`)
- Login dengan akun Microsoft/GitHub
- Tunnel akan dikonfigurasi otomatis

### 4. Start Tunnel (Menu 3)
- Tunnel berjalan di background
- Akses via browser: `https://vscode.dev/tunnel/[nama-tunnel]`
- Atau connect via desktop VSCode dengan extension "Remote - Tunnels"

### 5. Install Extensions (Menu 5)
Extension populer yang akan diinstall:
- `ms-python.python` - Python support
- `ms-python.vscode-pylance` - Python IntelliSense
- `ms-toolsai.jupyter` - Jupyter notebook support
- `ms-vscode.vscode-json` - JSON support
- `redhat.vscode-yaml` - YAML support
- `ms-vscode.theme-tomorrow-night-blue` - Dark theme
- `PKief.material-icon-theme` - Material icons

## 📋 Menu Lengkap

```
🚀 VSCode Server Interactive Installer
==================================================

📋 MENU UTAMA:
1. 📥 Install VSCode Server
2. 🔧 Setup Tunnel  
3. 🚀 Start Tunnel
4. 🛑 Stop Tunnel
5. 📦 Install Popular Extensions
6. 📦 Install Custom Extension
7. 📋 List Installed Extensions
8. 📊 Show Status
9. ⚙️ Configure Extensions
0. 🚪 Exit
```

## 🔧 Advanced Features

### Custom Extension Installation (Menu 6)
Install extension spesifik dengan Extension ID:
```
Extension ID: ms-vscode.vscode-typescript-next
```

### Extension Configuration (Menu 9)
- Add extension ke list default
- Remove extension dari list
- Reset ke default extensions

### Status Monitoring (Menu 8)
Lihat status lengkap sistem:
- Status instalasi VSCode Server
- Status konfigurasi tunnel
- Status tunnel (running/stopped)
- URL akses
- Lokasi file konfigurasi

## 📁 File Structure

```
~/.config/vscode-server-installer/
├── config.json          # Konfigurasi installer
└── tunnel.log          # Log tunnel

~/.local/lib/vscode-server/  # Instalasi VSCode Server
~/.local/bin/code           # Binary VSCode Server
```

## 🌐 Cara Akses VSCode

### 1. Via Browser
- Buka: `https://vscode.dev/tunnel/[nama-tunnel]`
- Login dengan akun Microsoft/GitHub yang sama

### 2. Via Desktop VSCode
1. Install extension **"Remote - Tunnels"** di desktop VSCode
2. Command Palette (`Ctrl+Shift+P`)
3. Pilih **"Remote-Tunnels: Connect to Tunnel"**
4. Masukkan nama tunnel yang sama
5. Login dengan akun Microsoft/GitHub

## 🔒 Security & Authentication

- **Microsoft/GitHub Authentication**: Menggunakan OAuth untuk keamanan
- **Secure Tunnels**: Koneksi HTTPS end-to-end encryption
- **Access Control**: Hanya akun yang login yang bisa akses
- **No Public Access**: Tidak seperti ngrok, hanya user yang authenticated

## 🐛 Troubleshooting

### Tunnel Tidak Bisa Start
1. Pastikan VSCode Server sudah terinstall (Menu 1)
2. Pastikan tunnel sudah dikonfigurasi (Menu 2)
3. Cek status dengan Menu 8
4. Lihat log di `~/.config/vscode-server-installer/tunnel.log`

### Extension Tidak Terinstall
1. Pastikan VSCode Server running
2. Cek connection internet
3. Verifikasi Extension ID
4. Coba install manual via desktop VSCode

### Authentication Issues
1. Logout dan login ulang di browser
2. Clear browser cache untuk vscode.dev
3. Regenerate authentication di GitHub/Microsoft

## 💡 Tips & Best Practices

### Naming Tunnels
- Gunakan nama yang mudah diingat
- Hindari spasi dan karakter khusus
- Contoh: `my-dev-server`, `python-workspace`, `data-analysis`

### Extension Management
- Install extension sesuai kebutuhan project
- Gunakan workspace-specific settings untuk project berbeda
- Update extension secara berkala

### Performance
- Tutup tunnel ketika tidak digunakan (Menu 4)
- Monitor resource usage di host machine
- Gunakan `.gitignore` untuk exclude file yang tidak perlu sync

## 🆕 Update & Maintenance

### Update VSCode Server
1. Stop tunnel (Menu 4)
2. Install ulang VSCode Server (Menu 1)
3. Setup tunnel kembali (Menu 2)
4. Start tunnel (Menu 3)

### Backup Configuration
```bash
cp ~/.config/vscode-server-installer/config.json ~/vscode-installer-backup.json
```

## 🤝 Integration dengan Projects

### Python Development
```bash
# Install Python extensions
# Menu 5 sudah include: ms-python.python, ms-python.vscode-pylance, ms-toolsai.jupyter
```

### Web Development  
```bash
# Install via Menu 6:
# - ms-vscode.vscode-typescript-next
# - bradlc.vscode-tailwindcss  
# - esbenp.prettier-vscode
```

### Data Science
```bash  
# Menu 5 sudah include: ms-toolsai.jupyter
# Tambahan via Menu 6:
# - ms-python.vscode-pandas
# - ms-python.vscode-jupyter-slideshow
```

---

🎉 **Selamat menggunakan VSCode Server Interactive Installer!**

Untuk support dan update, cek repository utama: [code-server-labs](https://github.com/mrzlfz/code-server-labs)