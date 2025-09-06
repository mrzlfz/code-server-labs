#!/usr/bin/env python3
"""
Complete Tunnel Setup - Two-step authentication process
1. Wait for user authentication to complete
2. Start the tunnel automatically
"""

import subprocess
import time
import json
from pathlib import Path

def wait_for_authentication():
    """Wait for user to complete GitHub authentication"""
    code_path = Path.home() / ".local" / "bin" / "code"
    
    print("⏳ Waiting for GitHub authentication to complete...")
    print("👉 Please complete authentication at: https://github.com/login/device")
    print("🔄 Checking authentication status every 5 seconds...")
    
    max_attempts = 60  # 5 minutes max
    
    for attempt in range(max_attempts):
        try:
            # Check if user is authenticated
            result = subprocess.run(
                f'"{code_path}" tunnel user show',
                shell=True,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                print("✅ Authentication completed successfully!")
                print(f"👤 User info: {result.stdout.strip()}")
                return True
            else:
                print(f"⏳ Attempt {attempt + 1}/{max_attempts} - Not authenticated yet...")
                time.sleep(5)
                
        except Exception as e:
            print(f"⚠️  Error checking auth (attempt {attempt + 1}): {e}")
            time.sleep(5)
    
    print("❌ Authentication timeout - please try manual authentication")
    return False

def start_tunnel():
    """Start the tunnel after authentication is complete"""
    code_path = Path.home() / ".local" / "bin" / "code"
    
    # Get tunnel name from config
    config_file = Path.home() / ".config" / "vscode-server-installer" / "config.json"
    tunnel_name = "my-dev-tunnel"  # default
    
    if config_file.exists():
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
                tunnel_name = config.get('tunnel_name', tunnel_name)
        except:
            pass
    
    if not tunnel_name:
        tunnel_name = input("📝 Enter tunnel name: ").strip()
        if not tunnel_name:
            tunnel_name = "my-dev-tunnel"
    
    print(f"🚀 Starting tunnel: {tunnel_name}")
    
    try:
        # Start tunnel in background
        command = f'"{code_path}" tunnel --name "{tunnel_name}" --accept-server-license-terms'
        print(f"▶️  Command: {command}")
        
        # Use nohup to run in background
        bg_command = f"nohup {command} > tunnel_output.log 2>&1 &"
        
        result = subprocess.run(bg_command, shell=True)
        
        if result.returncode == 0:
            print("✅ Tunnel started successfully!")
            print(f"🌐 Web access: https://vscode.dev/tunnel/{tunnel_name}")
            print(f"📱 Desktop access: Connect to tunnel '{tunnel_name}' in VSCode")
            print(f"📋 Log file: tunnel_output.log")
            
            # Wait a moment and check status
            time.sleep(3)
            status_result = subprocess.run(
                f'"{code_path}" tunnel status',
                shell=True,
                capture_output=True,
                text=True
            )
            
            if status_result.returncode == 0:
                print("📊 Tunnel Status:")
                print(status_result.stdout)
            
            return True
        else:
            print("❌ Failed to start tunnel")
            return False
            
    except Exception as e:
        print(f"❌ Error starting tunnel: {e}")
        return False

def main():
    print("🔧 VSCode Tunnel Complete Setup")
    print("=" * 40)
    
    # Step 1: Wait for authentication
    if not wait_for_authentication():
        print("💡 Try manual authentication:")
        print("   ~/.local/bin/code tunnel user login --provider github")
        return
    
    # Step 2: Start tunnel
    if start_tunnel():
        print("\n✅ Setup completed successfully!")
        print("\n📖 Next steps:")
        print("1. Open https://vscode.dev in your browser")
        print("2. Click 'Connect to Tunnel'")
        print("3. Enter your tunnel name")
        print("4. Start coding!")
    else:
        print("\n❌ Tunnel setup failed")
        print("💡 Try manual tunnel start:")
        print("   ~/.local/bin/code tunnel --name YOUR_NAME --accept-server-license-terms")

if __name__ == "__main__":
    main()