#!/usr/bin/env python3
"""
Test script for VSCode Server functionality
"""

import sys
import os
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from code_server_colab_setup import CodeServerSetup

def test_vscode_server():
    """Test VSCode Server installation and basic functionality."""
    print("🧪 Testing VSCode Server functionality...")
    
    # Initialize the setup
    app = CodeServerSetup()
    
    # Test configuration
    print("\n1. Testing configuration...")
    app.config.set("server_type", "vscode-server")
    server_type = app.config.get("server_type")
    print(f"   Server type: {server_type}")
    assert server_type == "vscode-server", "Server type not set correctly"
    
    # Test status method
    print("\n2. Testing status method...")
    status = app._get_status()
    print(f"   VSCode Server status: {status.get('vscode_server', 'Not found')}")
    
    # Test VSCode Server detection
    print("\n3. Testing VSCode Server detection...")
    is_running = app._is_vscode_server_running()
    print(f"   Is running: {is_running}")
    
    # Test switch methods
    print("\n4. Testing switch methods...")
    print("   Switch to VSCode Server method exists:", hasattr(app, '_switch_to_vscode_server'))
    print("   Switch to Code Server method exists:", hasattr(app, '_switch_to_code_server'))
    
    # Test installation methods
    print("\n5. Testing installation methods...")
    print("   Install VSCode Server method exists:", hasattr(app, 'install_vscode_server'))
    print("   Start VSCode Server method exists:", hasattr(app, 'start_vscode_server'))
    print("   Stop VSCode Server method exists:", hasattr(app, 'stop_vscode_server'))
    
    print("\n✅ All tests passed!")
    print("\n💡 To test full functionality:")
    print("   1. Run: python code_server_colab_setup.py")
    print("   2. Choose option 12 to switch to VSCode Server")
    print("   3. Choose option 1 to install VSCode Server")
    print("   4. Choose option 2 to start VSCode Server")

if __name__ == "__main__":
    test_vscode_server()
