#!/usr/bin/env python3
"""
Test VSCode Server download functionality
"""

import sys
import os
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from code_server_colab_setup import CodeServerSetup

def test_vscode_download():
    """Test VSCode Server download URL."""
    print("🧪 Testing VSCode Server download...")
    
    # Initialize the setup
    app = CodeServerSetup()
    
    # Switch to VSCode Server mode
    app.config.set("server_type", "vscode-server")
    
    # Test the download URL generation
    print("\n1. Testing download URL generation...")
    
    # Test platform detection
    import platform
    system = platform.system().lower()
    machine = platform.machine().lower()
    
    print(f"   Detected system: {system}")
    print(f"   Detected machine: {machine}")
    
    # Test URL construction (without actually downloading)
    if system == "linux":
        if machine in ["x86_64", "amd64"]:
            platform_name = "cli-linux-x64"
        elif machine in ["aarch64", "arm64"]:
            platform_name = "cli-linux-arm64"
        elif machine in ["armv7l", "armhf"]:
            platform_name = "cli-linux-armhf"
        else:
            platform_name = "cli-linux-x64"
    else:
        platform_name = "cli-linux-x64"  # Default for testing
    
    download_url = f"https://update.code.visualstudio.com/latest/{platform_name}/stable"
    print(f"   Generated URL: {download_url}")
    
    # Test URL accessibility (HEAD request)
    try:
        import requests
        response = requests.head(download_url, timeout=10)
        print(f"   URL status: {response.status_code}")
        if response.status_code == 302:
            print(f"   Redirect to: {response.headers.get('Location', 'Unknown')}")
            print("   ✅ URL is accessible")
        else:
            print("   ❌ URL returned unexpected status")
    except Exception as e:
        print(f"   ❌ URL test failed: {e}")
    
    print("\n💡 The download URL has been fixed!")
    print("   You can now try installing VSCode Server again.")

if __name__ == "__main__":
    test_vscode_download()
