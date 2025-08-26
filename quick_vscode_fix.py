#!/usr/bin/env python3
"""
Quick VSCode Server Fix
=======================

A simple script to quickly fix the VSCode Server installation issue
in Google Cloud Shell or similar environments.

Usage:
    python quick_vscode_fix.py
"""

import os
import subprocess
import requests
import tarfile
from pathlib import Path

def main():
    print("🔧 Quick VSCode Server Fix")
    print("-" * 30)
    
    # Setup paths
    install_dir = Path.home() / ".local" / "lib" / "vscode-server"
    bin_dir = Path.home() / ".local" / "bin"
    bin_path = bin_dir / "code"
    
    # Create directories
    install_dir.mkdir(parents=True, exist_ok=True)
    bin_dir.mkdir(parents=True, exist_ok=True)
    
    # Check if already working
    if bin_path.exists():
        try:
            result = subprocess.run([str(bin_path), '--version'], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                print("✅ VSCode CLI already working!")
                print(f"Version: {result.stdout.strip()}")
                return
        except:
            pass
    
    print("📥 Downloading VSCode CLI...")
    
    # Download with a more reliable URL
    url = "https://update.code.visualstudio.com/latest/cli-linux-x64/stable"
    download_path = install_dir / "vscode-cli.tar.gz"
    
    try:
        response = requests.get(url, stream=True, timeout=300)
        response.raise_for_status()
        
        with open(download_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        
        print("✅ Download completed")
        
        # Extract and find binary
        print("📁 Extracting...")
        
        with tarfile.open(download_path, 'r:gz') as tar:
            tar.extractall(install_dir)
        
        # Look for the binary more aggressively
        print("🔍 Searching for VSCode binary...")
        
        found_binary = None
        for root, dirs, files in os.walk(install_dir):
            print(f"Checking directory: {root}")
            for file in files:
                file_path = Path(root) / file
                print(f"  Found file: {file} (size: {file_path.stat().st_size})")
                
                # Check if this could be the VSCode binary
                if file in ['code', 'vscode'] or 'code' in file.lower():
                    if file_path.stat().st_size > 1000:  # Reasonable size
                        # Make it executable
                        file_path.chmod(0o755)
                        
                        # Test if it's the VSCode CLI
                        try:
                            test_result = subprocess.run([str(file_path), '--version'], 
                                                       capture_output=True, text=True, timeout=5)
                            if test_result.returncode == 0:
                                print(f"✅ Found working VSCode binary: {file_path}")
                                found_binary = file_path
                                break
                        except:
                            continue
            
            if found_binary:
                break
        
        if found_binary:
            # Copy to bin directory
            if bin_path.exists():
                bin_path.unlink()
            
            import shutil
            shutil.copy2(found_binary, bin_path)
            bin_path.chmod(0o755)
            
            # Verify
            result = subprocess.run([str(bin_path), '--version'], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                print("🎉 VSCode CLI installed successfully!")
                print(f"Version: {result.stdout.strip()}")
                print(f"Location: {bin_path}")
            else:
                print("❌ Installation verification failed")
        else:
            print("❌ Could not find VSCode binary in the archive")
            print("📋 Archive contents:")
            for root, dirs, files in os.walk(install_dir):
                for file in files:
                    file_path = Path(root) / file
                    print(f"  {file_path.relative_to(install_dir)} ({file_path.stat().st_size} bytes)")
        
        # Clean up
        download_path.unlink()
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
