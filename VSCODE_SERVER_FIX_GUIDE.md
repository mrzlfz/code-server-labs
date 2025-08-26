# VSCode Server Installation Fix Guide

## Masalah yang Terjadi

Ketika menginstal VSCode Server di Google Cloud Shell, Anda mendapatkan error:
```
❌ Could not find 'code' binary in extracted files
❌ Failed to extract VSCode CLI
```

## Penyebab Masalah

1. **Struktur Archive Berbeda**: File yang diunduh dari Microsoft mungkin memiliki struktur direktori yang berbeda dari yang diharapkan
2. **Binary Name Variations**: Binary mungkin memiliki nama yang berbeda atau berada di lokasi yang tidak terduga
3. **Permission Issues**: File binary mungkin tidak memiliki permission executable
4. **Archive Format Issues**: Format archive mungkin berbeda atau corrupt

## Solusi Cepat

### Opsi 1: Gunakan Script Perbaikan Cepat

```bash
# Jalankan script perbaikan cepat
python quick_vscode_fix.py
```

### Opsi 2: Gunakan Script Perbaikan Lengkap

```bash
# Jalankan script perbaikan lengkap dengan multiple fallback
python fix_vscode_server_installation.py
```

### Opsi 3: Manual Installation

```bash
# 1. Buat direktori yang diperlukan
mkdir -p ~/.local/lib/vscode-server
mkdir -p ~/.local/bin

# 2. Download VSCode CLI
cd ~/.local/lib/vscode-server
curl -L -o vscode-cli.tar.gz "https://update.code.visualstudio.com/latest/cli-linux-x64/stable"

# 3. Extract dan cari binary
tar -xzf vscode-cli.tar.gz
find . -name "*code*" -type f -executable

# 4. Copy binary yang ditemukan ke ~/.local/bin/code
# (ganti 'path/to/found/binary' dengan path yang ditemukan)
cp path/to/found/binary ~/.local/bin/code
chmod +x ~/.local/bin/code

# 5. Test installation
~/.local/bin/code --version
```

### Opsi 4: Menggunakan Snap (jika tersedia)

```bash
# Install via snap
sudo snap install code --classic

# Create symlink
ln -sf /snap/bin/code ~/.local/bin/code
```

## Perbaikan dalam Kode Utama

Kode `code_server_colab_setup.py` telah diperbaiki dengan:

1. **Enhanced Binary Detection**: Mencari binary dengan berbagai nama dan pattern
2. **Debug Logging**: Menampilkan isi archive untuk debugging
3. **Multiple Fallback Methods**: Jika satu metode gagal, coba metode lain
4. **Better Error Handling**: Informasi error yang lebih detail
5. **Alternative Installation Methods**: Curl, wget, dan package manager fallbacks

## Fitur Perbaikan Baru

### 1. Enhanced Binary Search
```python
binary_patterns = [
    'code',           # Standard VSCode CLI
    'vscode',         # Alternative name
    'code-server',    # Code server binary
    'code.exe',       # Windows executable
    'vscode.exe',     # Windows alternative
]
```

### 2. Executable Testing
```python
# Test if binary actually works
result = subprocess.run([str(file_path), '--version'], 
                      capture_output=True, text=True, timeout=10)
if result.returncode == 0 and ('code' in result.stdout.lower() or 'visual studio code' in result.stdout.lower()):
    # This is a valid VSCode binary
```

### 3. Multiple Download URLs
- Primary: `https://update.code.visualstudio.com/latest/cli-linux-x64/stable`
- Fallback 1: `https://code.visualstudio.com/sha/download?build=stable&os=cli-alpine-x64`
- Fallback 2: GitHub releases

### 4. Alternative Installation Methods
- Direct binary download
- Curl/wget download
- Package manager installation (snap, apt, yum, dnf)

## Troubleshooting

### Jika Masih Gagal

1. **Check Internet Connection**:
   ```bash
   curl -I https://update.code.visualstudio.com/latest/cli-linux-x64/stable
   ```

2. **Check Available Space**:
   ```bash
   df -h ~/.local/
   ```

3. **Check Permissions**:
   ```bash
   ls -la ~/.local/bin/
   ```

4. **Manual Debug**:
   ```bash
   # Download dan extract manual
   cd /tmp
   curl -L -o vscode-cli.tar.gz "https://update.code.visualstudio.com/latest/cli-linux-x64/stable"
   tar -tzf vscode-cli.tar.gz | head -20  # List archive contents
   tar -xzf vscode-cli.tar.gz
   find . -type f -executable | head -10  # Find executable files
   ```

### Environment Variables

Pastikan PATH sudah include ~/.local/bin:
```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

## Testing Installation

Setelah instalasi berhasil:

```bash
# Test basic functionality
code --version

# Test tunnel creation (akan meminta login)
code tunnel --name test-tunnel

# Test extension installation
code --install-extension ms-python.python
```

## Catatan untuk Google Cloud Shell

Google Cloud Shell memiliki beberapa keterbatasan:
- Tidak ada systemd
- Limited sudo access
- Temporary filesystem untuk beberapa direktori
- Network restrictions

Script perbaikan telah disesuaikan untuk mengatasi keterbatasan ini.
