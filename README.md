# Code Server Colab Setup

A comprehensive Python script to set up VS Code Server on Google Colab with multiple server options, tunneling, and desktop VSCode integration.

## 🚀 Features

- **Dual Server Support**: Choose between Code Server (web-based) or VSCode Server (official Microsoft)
- **Desktop VSCode Integration**: Connect with desktop VSCode using Remote-Tunnels extension
- **Interactive CLI Menu**: User-friendly command-line interface with menu-driven options
- **Multiple Installation Options**: Automated installation without systemd dependency
- **Tunneling Support**: Ngrok, Cloudflare, and built-in VSCode tunnels
- **Extensions Management**: Install, update, and manage VS Code extensions
- **Google Colab Optimized**: Specifically designed for Google Colab environment
- **Configuration Persistence**: Save and restore settings across sessions
- **Process Management**: Start, stop, restart, and monitor servers
- **Comprehensive Logging**: Detailed logging and error handling

## 📋 Requirements

- Python 3.6+
- Internet connection
- Google Colab environment (recommended)
- For Code Server: Ngrok account (free tier available)
- For VSCode Server: Microsoft/GitHub account for authentication

## 🛠️ Installation

### Quick Start in Google Colab

1. **Upload the script to your Colab session:**
   ```python
   # In a Colab cell
   !wget https://raw.githubusercontent.com/your-repo/code_server_colab_setup.py
   ```

2. **Run the script:**
   ```python
   !python code_server_colab_setup.py
   ```

3. **Or run directly:**
   ```python
   exec(open('code_server_colab_setup.py').read())
   ```

### Local Installation

1. **Download the script:**
   ```bash
   wget https://raw.githubusercontent.com/your-repo/code_server_colab_setup.py
   chmod +x code_server_colab_setup.py
   ```

2. **Run the script:**
   ```bash
   python3 code_server_colab_setup.py
   ```

## 🎯 Usage

### Interactive Menu

Run the script without arguments to access the interactive menu:

```bash
python3 code_server_colab_setup.py
```

### Command Line Options

```bash
# Install Code Server
python3 code_server_colab_setup.py --install

# Start Code Server
python3 code_server_colab_setup.py --start

# Stop Code Server
python3 code_server_colab_setup.py --stop

# Show status
python3 code_server_colab_setup.py --status

# Configure settings
python3 code_server_colab_setup.py --config
```

## 📖 Step-by-Step Guide

### 1. Initial Setup

1. **Run the script** and select option `1` to install Code Server
2. **Setup ngrok** by selecting option `8`:
   - Get your auth token from [ngrok dashboard](https://dashboard.ngrok.com/get-started/your-authtoken)
   - Enter the token when prompted
3. **Start Code Server** by selecting option `2`

### 2. Choosing Server Type

The script supports two server types:

#### Code Server (Web-based)
- Third-party web-based VSCode
- Runs entirely in browser
- Password authentication
- Ngrok/Cloudflare tunnel support

#### VSCode Server (Official Microsoft)
- Official Microsoft VSCode Server
- Works with desktop VSCode Remote extensions
- Built-in tunnel support
- Microsoft/GitHub authentication

### 3. Accessing Your Server

#### Code Server Access:
- **Local URL**: `http://127.0.0.1:8080` (if running locally)
- **Ngrok URL**: `https://xxxxx.ngrok.io` (for web access)
- **Password**: Automatically generated or custom set

#### VSCode Server Access:
- **Tunnel URL**: `https://vscode.dev/tunnel/your-tunnel-name`
- **Desktop VSCode**: Install 'Remote - Tunnels' extension
- **Authentication**: Microsoft/GitHub account

### 4. Installing Extensions (Code Server only)

Select option `7` to manage extensions:
- **Popular Extensions**: Installs common development extensions
- **Custom Extensions**: Install specific extensions by ID
- **Extension Management**: List, update, or remove extensions

### 5. Configuration

Select option `6` to configure:
- **Server Settings**: Port, password, authentication (Code Server)
- **Tunnel Settings**: Tunnel name, authentication (VSCode Server)
- **Ngrok Settings**: Auth token, region (Code Server)
- **System Settings**: Server type, optimizations

### 6. Switching Between Server Types

Use the menu options to switch:
- **Switch to VSCode Server**: For desktop VSCode integration
- **Switch to Code Server**: For web-based access

## 🔧 Configuration

The script creates configuration files in:
- **Config**: `~/.config/code-server-colab/config.json`
- **Logs**: `~/.config/code-server-colab/setup.log`
- **Installation**: `~/.local/lib/code-server/`
- **Binary**: `~/.local/bin/code-server`

### Default Configuration

```json
{
  "code_server": {
    "version": "4.23.1",
    "port": 8080,
    "auth": "password",
    "bind_addr": "127.0.0.1"
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
      "redhat.vscode-yaml"
    ]
  }
}
```

## 🌐 Ngrok Setup

1. **Create Account**: Visit [ngrok.com](https://ngrok.com) and create a free account
2. **Get Auth Token**: Go to [your authtoken page](https://dashboard.ngrok.com/get-started/your-authtoken)
3. **Configure**: Use option `8` in the menu to setup ngrok
4. **Test**: The script will test the connection automatically

## 📦 Popular Extensions

The script includes these popular extensions by default:

- **Python Development**: `ms-python.python`, `ms-python.vscode-pylance`
- **Jupyter Support**: `ms-toolsai.jupyter`
- **File Formats**: `ms-vscode.vscode-json`, `redhat.vscode-yaml`
- **Themes**: `ms-vscode.theme-tomorrow-night-blue`
- **Icons**: `PKief.material-icon-theme`
- **Web Development**: `bradlc.vscode-tailwindcss`, `esbenp.prettier-vscode`

## 🐛 Troubleshooting

### Common Issues

1. **Permission Denied**:
   ```bash
   chmod +x code_server_colab_setup.py
   ```

2. **Module Not Found**:
   - The script auto-installs required packages
   - Manually install: `pip install pyngrok psutil requests`

3. **Code Server Won't Start**:
   - Check logs: Select option `10` in menu
   - Verify installation: Select option `5` for status
   - Try reinstalling: Select option `1`

4. **Ngrok Connection Failed**:
   - Verify auth token is correct
   - Check internet connection
   - Try different region in ngrok settings

### Log Files

View logs through the menu (option `10`) or directly:
```bash
tail -f ~/.config/code-server-colab/setup.log
```

## 🔒 Security Notes

- **Password Protection**: Always use strong passwords
- **Ngrok URLs**: Are publicly accessible - use authentication
- **File Access**: Code Server has access to your file system
- **Extensions**: Only install trusted extensions

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- [Code Server](https://github.com/coder/code-server) - VS Code in the browser
- [ngrok](https://ngrok.com) - Secure tunneling service
- [pyngrok](https://github.com/alexdlaird/pyngrok) - Python ngrok wrapper

## 📞 Support

- **Issues**: Report bugs and feature requests
- **Discussions**: Ask questions and share ideas
- **Documentation**: Comprehensive guides and examples

---

**Made with ❤️ for the developer community**
