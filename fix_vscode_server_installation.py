#!/usr/bin/env python3
"""
VSCode Server Installation Fix
==============================

This script fixes the VSCode Server installation issue where the 'code' binary
cannot be found after extraction. It provides multiple fallback methods to
ensure successful installation.

Usage:
    python fix_vscode_server_installation.py

Author: AI Assistant
Version: 1.0.0
"""

import os
import sys
import subprocess
import requests
import tarfile
import shutil
from pathlib import Path
import tempfile

def print_status(message, status="info"):
    """Print colored status messages."""
    colors = {
        "info": "\033[94m",      # Blue
        "success": "\033[92m",   # Green
        "warning": "\033[93m",   # Yellow
        "error": "\033[91m",     # Red
        "reset": "\033[0m"       # Reset
    }
    
    icons = {
        "info": "ℹ️",
        "success": "✅",
        "warning": "⚠️",
        "error": "❌"
    }
    
    color = colors.get(status, colors["info"])
    icon = icons.get(status, "•")
    reset = colors["reset"]
    
    print(f"{color}{icon} {message}{reset}")

def check_existing_installation():
    """Check if VSCode CLI is already installed."""
    bin_path = Path.home() / ".local" / "bin" / "code"
    
    if bin_path.exists():
        try:
            result = subprocess.run([str(bin_path), '--version'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                print_status(f"VSCode CLI already installed: {result.stdout.strip()}", "success")
                return True
        except:
            pass
    
    return False

def create_directories():
    """Create necessary directories."""
    dirs = [
        Path.home() / ".local" / "lib" / "vscode-server",
        Path.home() / ".local" / "bin"
    ]
    
    for dir_path in dirs:
        dir_path.mkdir(parents=True, exist_ok=True)
        print_status(f"Created directory: {dir_path}", "info")

def download_vscode_cli():
    """Download VSCode CLI with multiple fallback URLs."""
    install_dir = Path.home() / ".local" / "lib" / "vscode-server"
    
    # Multiple URLs to try
    urls = [
        "https://update.code.visualstudio.com/latest/cli-linux-x64/stable",
        "https://code.visualstudio.com/sha/download?build=stable&os=cli-alpine-x64",
        "https://github.com/microsoft/vscode/releases/latest/download/vscode-cli-linux-x64.tar.gz"
    ]
    
    for i, url in enumerate(urls, 1):
        print_status(f"Trying download URL {i}/{len(urls)}: {url}", "info")
        
        try:
            response = requests.get(url, stream=True, timeout=300)
            response.raise_for_status()
            
            download_path = install_dir / f"vscode-cli-attempt-{i}.tar.gz"
            
            with open(download_path, 'wb') as f:
                total_size = int(response.headers.get('content-length', 0))
                downloaded = 0
                
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            progress = (downloaded / total_size) * 100
                            print(f"\r📥 Progress: {progress:.1f}%", end="", flush=True)
            
            print()  # New line after progress
            print_status(f"Downloaded: {download_path}", "success")
            return download_path
            
        except Exception as e:
            print_status(f"Download failed: {e}", "error")
            continue
    
    return None

def extract_and_find_binary(download_path):
    """Extract archive and find the VSCode binary."""
    install_dir = Path.home() / ".local" / "lib" / "vscode-server"
    bin_path = Path.home() / ".local" / "bin" / "code"
    
    print_status("Extracting VSCode CLI...", "info")
    
    try:
        # Extract to temporary directory first
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            with tarfile.open(download_path, 'r:gz') as tar:
                tar.extractall(temp_path)
            
            # List all extracted files for debugging
            print_status("Listing extracted files:", "info")
            all_files = []
            for root, _, files in os.walk(temp_path):
                for file in files:
                    file_path = Path(root) / file
                    is_executable = os.access(file_path, os.X_OK)
                    size = file_path.stat().st_size
                    rel_path = file_path.relative_to(temp_path)
                    all_files.append((str(rel_path), is_executable, size))
                    print(f"  📄 {rel_path} (executable: {is_executable}, size: {size})")
            
            # Search for VSCode binary with multiple strategies
            binary_candidates = []
            
            # Strategy 1: Look for exact names
            binary_names = ['code', 'vscode', 'code-server', 'code.exe']
            for root, _, files in os.walk(temp_path):
                for name in binary_names:
                    if name in files:
                        candidate = Path(root) / name
                        if candidate.is_file():
                            binary_candidates.append(candidate)
            
            # Strategy 2: Look for any executable files
            if not binary_candidates:
                for root, _, files in os.walk(temp_path):
                    for file in files:
                        file_path = Path(root) / file
                        if file_path.is_file() and file_path.stat().st_size > 1000:
                            # Try to make it executable
                            try:
                                file_path.chmod(0o755)
                                if os.access(file_path, os.X_OK):
                                    binary_candidates.append(file_path)
                            except:
                                continue
            
            # Test candidates to find the real VSCode CLI
            for candidate in binary_candidates:
                print_status(f"Testing candidate: {candidate.name}", "info")
                try:
                    result = subprocess.run([str(candidate), '--version'], 
                                          capture_output=True, text=True, timeout=10)
                    if result.returncode == 0:
                        output = result.stdout.lower()
                        if 'code' in output or 'visual studio code' in output:
                            print_status(f"Found valid VSCode CLI: {candidate}", "success")
                            
                            # Copy to final location
                            if bin_path.exists():
                                bin_path.unlink()
                            
                            shutil.copy2(candidate, bin_path)
                            bin_path.chmod(0o755)
                            
                            print_status(f"Installed VSCode CLI to: {bin_path}", "success")
                            return True
                except Exception as e:
                    print_status(f"Candidate test failed: {e}", "warning")
                    continue
            
            # If no valid binary found, show detailed information
            print_status("No valid VSCode binary found in archive", "error")
            print_status("Archive contents summary:", "info")
            for file_info in all_files[:20]:  # Show first 20 files
                print(f"  - {file_info[0]} (executable: {file_info[1]}, size: {file_info[2]})")
            if len(all_files) > 20:
                print(f"  ... and {len(all_files) - 20} more files")
            
            return False
    
    except Exception as e:
        print_status(f"Extraction failed: {e}", "error")
        return False
    
    finally:
        # Clean up download file
        if download_path.exists():
            download_path.unlink()

def try_alternative_installation():
    """Try alternative installation methods."""
    bin_path = Path.home() / ".local" / "bin" / "code"
    
    print_status("Trying alternative installation methods...", "info")
    
    # Method 1: Try curl/wget
    curl_commands = [
        ["curl", "-L", "-o", "/tmp/vscode-cli.tar.gz", 
         "https://update.code.visualstudio.com/latest/cli-linux-x64/stable"],
        ["wget", "-O", "/tmp/vscode-cli.tar.gz", 
         "https://update.code.visualstudio.com/latest/cli-linux-x64/stable"]
    ]
    
    for cmd in curl_commands:
        try:
            print_status(f"Trying: {' '.join(cmd)}", "info")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                download_path = Path("/tmp/vscode-cli.tar.gz")
                if download_path.exists():
                    if extract_and_find_binary(download_path):
                        return True
        except Exception as e:
            print_status(f"{cmd[0]} failed: {e}", "warning")
            continue
    
    # Method 2: Try snap installation
    try:
        print_status("Trying snap installation...", "info")
        result = subprocess.run(["snap", "install", "code", "--classic"], 
                              capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            snap_code = Path("/snap/bin/code")
            if snap_code.exists():
                if bin_path.exists():
                    bin_path.unlink()
                bin_path.symlink_to(snap_code)
                print_status("Successfully installed via snap", "success")
                return True
    except Exception as e:
        print_status(f"Snap installation failed: {e}", "warning")
    
    return False

def verify_installation():
    """Verify that VSCode CLI is working."""
    bin_path = Path.home() / ".local" / "bin" / "code"
    
    if not bin_path.exists():
        print_status("VSCode CLI binary not found", "error")
        return False
    
    try:
        result = subprocess.run([str(bin_path), '--version'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print_status(f"VSCode CLI verification successful:", "success")
            print(f"  Version: {result.stdout.strip()}")
            return True
        else:
            print_status(f"VSCode CLI verification failed: {result.stderr}", "error")
            return False
    except Exception as e:
        print_status(f"VSCode CLI verification error: {e}", "error")
        return False

def main():
    """Main function to fix VSCode Server installation."""
    print("🚀 VSCode Server Installation Fix")
    print("=" * 50)
    
    # Check if already installed
    if check_existing_installation():
        print_status("VSCode CLI is already working correctly", "success")
        return True
    
    # Create necessary directories
    create_directories()
    
    # Try to download and install
    download_path = download_vscode_cli()
    if download_path:
        if extract_and_find_binary(download_path):
            if verify_installation():
                print_status("VSCode Server installation completed successfully!", "success")
                return True
    
    # Try alternative methods
    if try_alternative_installation():
        if verify_installation():
            print_status("VSCode Server installation completed via alternative method!", "success")
            return True
    
    print_status("All installation methods failed", "error")
    print_status("Please check your internet connection and try again", "info")
    return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
