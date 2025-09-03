# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Code Server Labs is a comprehensive Python solution for setting up VS Code Server environments on Google Colab and Linux systems. It provides dual server support with both web-based Code Server and official Microsoft VSCode Server, designed for cloud development environments.

## Development Commands

### Primary Application
```bash
# Interactive menu-driven interface
python3 code_server_colab_setup.py

# Command line operations
python3 code_server_colab_setup.py --install    # Install servers
python3 code_server_colab_setup.py --start      # Start server
python3 code_server_colab_setup.py --stop       # Stop server
python3 code_server_colab_setup.py --restart    # Restart server
python3 code_server_colab_setup.py --status     # Show status
python3 code_server_colab_setup.py --config     # Configure settings
```

### Google Colab Usage
```python
# Direct execution in Colab notebook
exec(open('code_server_colab_setup.py').read())

# Or download and run
!wget https://raw.githubusercontent.com/your-repo/code_server_colab_setup.py
!python code_server_colab_setup.py
```

### Testing and Troubleshooting
```bash
python3 fix_vscode_auth.py                      # Fix authentication issues
python3 fix_vscode_server_installation.py       # Fix installation problems
python3 verify_augment_fix.py                   # Fix extension compatibility
python3 quick_vscode_fix.py                     # Quick fixes
python3 test_*.py                               # Various test utilities
```

## Architecture Overview

### Core Classes (in code_server_colab_setup.py)
- **`CodeServerSetup`** (main): Primary orchestrator class managing all operations
- **`ConfigManager`**: Handles configuration persistence and management  
- **`Logger`**: Centralized logging system with file and console output
- **`ExtensionManager`**: VS Code extension installation and management
- **`SystemUtils`**: System utilities and helper functions

### Key Design Patterns
- **Object-oriented modular design**: Each major feature encapsulated in dedicated classes
- **Configuration-driven**: JSON-based configuration with persistence across sessions
- **Process management**: Comprehensive server lifecycle management without systemd dependency
- **Dual server architecture**: Support for both Code Server (web) and VSCode Server (desktop remote)

### Server Types
1. **Code Server**: Third-party web-based VS Code running in browser
2. **VSCode Server**: Official Microsoft server for desktop VSCode Remote-Tunnels

### Configuration System
- **Config Directory**: `~/.config/code-server-colab/`
- **Main Config**: `~/.config/code-server-colab/config.json`
- **Log File**: `~/.config/code-server-colab/setup.log`
- **Installation**: `~/.local/lib/code-server/`
- **Binaries**: `~/.local/bin/`

## Key Dependencies

### Auto-installed Dependencies
- `pyngrok`: Ngrok tunneling integration
- `psutil`: Process management and monitoring
- `requests`: HTTP operations and API calls

### Server Dependencies
- **Code Server**: Downloaded as pre-compiled binary (v4.23.1)
- **VSCode Server**: Downloaded via official Microsoft CLI

## Development Guidelines

### Code Organization
- Main application logic in `code_server_colab_setup.py` (5,373+ lines)
- Dedicated fix/troubleshooting scripts for specific issues
- Comprehensive error handling with detailed logging
- Menu-driven CLI with extensive user interaction

### Configuration Management
- All settings persisted in JSON format
- Runtime configuration updates reflected immediately
- Default configurations for both server types
- Extension management with popular preset bundles

### Process Management
- No systemd dependency (Colab-optimized)
- Background process monitoring and health checks
- Graceful start/stop/restart operations
- Automatic cleanup on termination

## Google Colab Specific Features

### Environment Optimization
- Designed specifically for Google Colab's constraints
- Handles ephemeral filesystem with persistent configuration
- Works without root privileges or systemd
- Automatic dependency installation in user space

### Tunneling Solutions
- **Ngrok**: External HTTP/HTTPS tunnels with authentication
- **Cloudflare**: Alternative tunneling service
- **VSCode Tunnels**: Built-in Microsoft tunneling for Remote-Tunnels extension

## Security Considerations

- Password-protected Code Server access
- Ngrok tunnel authentication and security warnings
- VSCode Server uses Microsoft/GitHub authentication
- File system access controls and user permissions
- Extension installation from trusted registries only

## Common Workflows

### Initial Setup
1. Run `python3 code_server_colab_setup.py`
2. Select server type (Code Server or VSCode Server)
3. Install and configure tunneling (Ngrok for Code Server)
4. Start server and access via provided URL
5. Install extensions as needed

### Troubleshooting
1. Check status via menu option or `--status` flag
2. Review logs at `~/.config/code-server-colab/setup.log`
3. Use dedicated fix scripts for specific issues
4. Restart services via menu or `--restart` flag

### Extension Management
- Popular extension bundles available via menu
- Custom extension installation by ID
- Support for both Microsoft and OpenVSX registries
- Extension compatibility fixes for crypto modules