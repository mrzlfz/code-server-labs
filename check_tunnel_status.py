#!/usr/bin/env python3
"""
Check VSCode Tunnel Status and Authentication
Verifies if authentication completed and tunnel is running
"""

import subprocess
import json
import os
from pathlib import Path

def check_tunnel_status():
    """Check current tunnel status"""
    print("🔍 Checking VSCode Tunnel Status...")
    
    code_path = Path.home() / ".local" / "bin" / "code"
    
    if not code_path.exists():
        print("❌ VSCode CLI not found")
        return False
    
    print(f"📂 Code path: {code_path}")
    
    # Check if user is logged in
    print("\n1️⃣ Checking authentication status...")
    try:
        result = subprocess.run(
            f'"{code_path}" tunnel user show',
            shell=True,
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            print("✅ User authenticated successfully!")
            print(f"👤 User info: {result.stdout.strip()}")
        else:
            print("❌ User not authenticated")
            print(f"Error: {result.stderr.strip()}")
            
            # Try to see available login options
            print("\n🔑 Available login providers:")
            providers_result = subprocess.run(
                f'"{code_path}" tunnel user login --help',
                shell=True,
                capture_output=True,
                text=True,
                timeout=10
            )
            if providers_result.returncode == 0:
                print(providers_result.stdout)
                
    except subprocess.TimeoutExpired:
        print("⏰ Authentication check timed out")
    except Exception as e:
        print(f"❌ Error checking auth: {e}")
    
    # Check running tunnels
    print("\n2️⃣ Checking active tunnels...")
    try:
        result = subprocess.run(
            f'"{code_path}" tunnel status',
            shell=True,
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            print("✅ Tunnel status retrieved:")
            print(result.stdout.strip())
        else:
            print("❌ No active tunnel or error getting status")
            print(f"Error: {result.stderr.strip()}")
            
    except subprocess.TimeoutExpired:
        print("⏰ Tunnel status check timed out")
    except Exception as e:
        print(f"❌ Error checking tunnel: {e}")
    
    # Check processes
    print("\n3️⃣ Checking running processes...")
    try:
        result = subprocess.run(
            "ps aux | grep 'code tunnel' | grep -v grep",
            shell=True,
            capture_output=True,
            text=True
        )
        
        if result.stdout.strip():
            print("✅ Found running tunnel processes:")
            for line in result.stdout.strip().split('\n'):
                print(f"  🔄 {line}")
        else:
            print("❌ No tunnel processes found")
            
    except Exception as e:
        print(f"❌ Error checking processes: {e}")
    
    # Check config
    print("\n4️⃣ Checking configuration...")
    config_dir = Path.home() / ".config" / "vscode-server-installer"
    config_file = config_dir / "config.json"
    
    if config_file.exists():
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
            
            print("✅ Configuration found:")
            print(f"  🚇 Tunnel name: {config.get('tunnel_name', 'Not set')}")
            print(f"  ✅ Server installed: {config.get('server_installed', False)}")
            print(f"  🔧 Tunnel configured: {config.get('tunnel_configured', False)}")
            
            if config.get('tunnel_name'):
                tunnel_url = f"https://vscode.dev/tunnel/{config['tunnel_name']}"
                print(f"  🌐 Web access: {tunnel_url}")
                
        except Exception as e:
            print(f"❌ Error reading config: {e}")
    else:
        print("❌ Configuration file not found")
    
    # Manual login instruction
    print("\n💡 If authentication is stuck, try manual login:")
    print(f'   {code_path} tunnel user login --provider github')
    print("\n💡 If you want to start tunnel manually:")
    print(f'   {code_path} tunnel --name YOUR_TUNNEL_NAME --accept-server-license-terms')

if __name__ == "__main__":
    print("🔍 VSCode Tunnel Status Checker")
    print("=" * 40)
    check_tunnel_status()