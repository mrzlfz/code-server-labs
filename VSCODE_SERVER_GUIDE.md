# VSCode Server Integration Guide

## 🎯 Overview

This guide explains the new VSCode Server functionality that enables **desktop VSCode remote connectivity** similar to GitHub Codespaces.

## 🔄 Server Types Comparison

### Code Server (Original)
- **Type**: Third-party web-based VSCode
- **Access**: Web browser only
- **Authentication**: Password-based
- **Tunneling**: Ngrok, Cloudflare
- **Extensions**: Manual management via UI
- **Use Case**: Quick web-based development

### VSCode Server (New)
- **Type**: Official Microsoft VSCode Server
- **Access**: Desktop VSCode + Web browser
- **Authentication**: Microsoft/GitHub account
- **Tunneling**: Built-in VSCode tunnels
- **Extensions**: Automatic marketplace access
- **Use Case**: Full desktop VSCode experience remotely

## 🚀 Getting Started with VSCode Server

### Step 1: Switch to VSCode Server
```bash
python code_server_colab_setup.py
# Choose option 12: "Switch to VSCode Server"
```

### Step 2: Install VSCode Server
```bash
# Choose option 1: "Install VSCode Server"
```

### Step 3: Start VSCode Server
```bash
# Choose option 2: "Start VSCode Server"
```

## 🔗 Connecting from Desktop VSCode

### Method 1: Remote-Tunnels Extension
1. Install the **Remote - Tunnels** extension in desktop VSCode
2. Open Command Palette (`Ctrl+Shift+P`)
3. Run: `Remote-Tunnels: Connect to Tunnel`
4. Enter your tunnel name when prompted
5. Authenticate with Microsoft/GitHub account

### Method 2: Direct URL
1. Copy the tunnel URL from the terminal output
2. Open it in your browser
3. Click "Open in VS Code Desktop" when prompted

## 🛠️ Configuration Options

### VSCode Server Settings
```json
{
  "vscode_server": {
    "version": "latest",
    "tunnel_name": "my-tunnel",
    "accept_server_license_terms": true,
    "enable_telemetry": false,
    "install_dir": "~/.local/lib/vscode-server",
    "bin_path": "~/.local/bin/code"
  }
}
```

### Environment Variables
- `VSCODE_SERVER_ACCEPT_LICENSE=1`: Accept license terms
- `VSCODE_DISABLE_TELEMETRY=1`: Disable telemetry

## 🔧 Technical Details

### Download URLs
- Linux x64: `https://update.code.visualstudio.com/latest/cli-linux-x64/stable`
- Linux ARM64: `https://update.code.visualstudio.com/latest/cli-linux-arm64/stable`
- macOS x64: `https://update.code.visualstudio.com/latest/cli-darwin-x64/stable`
- Windows x64: `https://update.code.visualstudio.com/latest/cli-win32-x64/stable`

### Command Structure
```bash
code tunnel --name <tunnel-name> --accept-server-license-terms
```

## 🔍 Troubleshooting

### Common Issues

1. **Authentication Failed**
   - Ensure you have a Microsoft/GitHub account
   - Check internet connectivity
   - Try clearing browser cache

2. **Tunnel Not Accessible**
   - Verify tunnel name is correct
   - Check if process is still running
   - Restart the tunnel if needed

3. **Desktop VSCode Won't Connect**
   - Install/update Remote-Tunnels extension
   - Check VSCode version (requires recent version)
   - Verify authentication status

### Debug Commands
```bash
# Check if VSCode CLI is installed
~/.local/bin/code --version

# List active tunnels
~/.local/bin/code tunnel --list

# Check process status
ps aux | grep "code.*tunnel"
```

## 🎉 Benefits of VSCode Server

1. **Native Desktop Experience**: Full VSCode features and performance
2. **Extension Compatibility**: All extensions work as expected
3. **File System Access**: Direct access to remote file system
4. **Integrated Terminal**: Native terminal experience
5. **Debugging Support**: Full debugging capabilities
6. **Git Integration**: Native Git support
7. **Settings Sync**: Your VSCode settings sync automatically

## 🔄 Switching Between Server Types

You can easily switch between Code Server and VSCode Server:

### From Code Server to VSCode Server
1. Stop Code Server if running
2. Choose "Switch to VSCode Server" from menu
3. Install and start VSCode Server

### From VSCode Server to Code Server
1. Stop VSCode Server if running
2. Choose "Switch to Code Server" from menu
3. Install and start Code Server

## 📚 Additional Resources

- [VSCode Remote Development](https://code.visualstudio.com/docs/remote/remote-overview)
- [Remote-Tunnels Extension](https://marketplace.visualstudio.com/items?itemName=ms-vscode.remote-server)
- [VSCode CLI Documentation](https://code.visualstudio.com/docs/editor/command-line)
