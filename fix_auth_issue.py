#!/usr/bin/env python3
"""
Fix VSCode Authentication Issue
Uses a different approach to complete authentication properly
"""

import subprocess
import time
import os
import signal
import threading
from pathlib import Path

def run_auth_with_timeout():
    """Run authentication with proper timeout and signal handling"""
    code_path = Path.home() / ".local" / "bin" / "code"
    
    print("🔐 Starting GitHub authentication...")
    print("📱 This will open the device flow - please complete it quickly")
    
    # Create the authentication command
    auth_command = f'"{code_path}" tunnel user login --provider github'
    
    print(f"▶️  Running: {auth_command}")
    
    try:
        # Start the process
        process = subprocess.Popen(
            auth_command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            preexec_fn=os.setsid  # Create new process group
        )
        
        print(f"🔄 Process started with PID: {process.pid}")
        
        # Create a thread to read output
        output_lines = []
        device_code = None
        auth_url = None
        
        def read_output():
            nonlocal device_code, auth_url
            while True:
                line = process.stdout.readline()
                if not line:
                    break
                
                line = line.strip()
                if line:
                    output_lines.append(line)
                    print(f"📄 {line}")
                    
                    # Extract device code and URL
                    if "use code" in line:
                        parts = line.split("use code ")
                        if len(parts) > 1:
                            device_code = parts[1].strip()
                            print(f"🔢 Device Code: {device_code}")
                    
                    if "github.com/login/device" in line:
                        auth_url = "https://github.com/login/device"
                        print(f"🌐 Auth URL: {auth_url}")
        
        # Start output reading thread
        output_thread = threading.Thread(target=read_output)
        output_thread.daemon = True
        output_thread.start()
        
        # Wait for device code to appear
        print("⏳ Waiting for device code...")
        
        wait_time = 0
        max_wait = 30  # 30 seconds to get device code
        
        while device_code is None and wait_time < max_wait:
            if process.poll() is not None:
                break
            time.sleep(1)
            wait_time += 1
            
        if device_code:
            print(f"\n🎯 Device Code Found: {device_code}")
            print(f"🌐 Go to: https://github.com/login/device")
            print(f"🔢 Enter code: {device_code}")
            print("\n⏰ You have 15 minutes to complete authentication")
            print("👉 Press Enter AFTER you complete authentication on GitHub...")
            
            input("Press Enter after completing GitHub authentication...")
            
            # Give process a moment to receive the auth
            print("⏳ Waiting for authentication to complete...")
            time.sleep(3)
            
            # Check if process completed
            if process.poll() is None:
                print("🔄 Process still running, waiting...")
                try:
                    process.wait(timeout=10)
                    print("✅ Process completed normally")
                except subprocess.TimeoutExpired:
                    print("⏰ Process timeout, terminating...")
                    os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                    
        else:
            print("❌ Device code not received, terminating...")
            os.killpg(os.getpgid(process.pid), signal.SIGTERM)
            
        # Wait for output thread to finish
        output_thread.join(timeout=2)
        
        return process.returncode == 0
        
    except Exception as e:
        print(f"❌ Error during authentication: {e}")
        return False

def verify_authentication():
    """Verify that authentication worked"""
    code_path = Path.home() / ".local" / "bin" / "code"
    
    print("\n🔍 Verifying authentication...")
    
    try:
        result = subprocess.run(
            f'"{code_path}" tunnel user show',
            shell=True,
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            print("✅ Authentication successful!")
            print(f"👤 User: {result.stdout.strip()}")
            return True
        else:
            print("❌ Authentication failed")
            print(f"Error: {result.stderr.strip()}")
            return False
            
    except Exception as e:
        print(f"❌ Error verifying auth: {e}")
        return False

def start_tunnel_after_auth():
    """Start tunnel after successful authentication"""
    if not verify_authentication():
        return False
    
    code_path = Path.home() / ".local" / "bin" / "code"
    tunnel_name = input("\n📝 Enter tunnel name (or press Enter for 'my-tunnel'): ").strip()
    
    if not tunnel_name:
        tunnel_name = "my-tunnel"
    
    print(f"🚀 Starting tunnel: {tunnel_name}")
    
    # Start tunnel in background
    tunnel_command = f'nohup "{code_path}" tunnel --name "{tunnel_name}" --accept-server-license-terms > tunnel.log 2>&1 &'
    
    try:
        subprocess.run(tunnel_command, shell=True, check=True)
        print("✅ Tunnel started in background!")
        print(f"🌐 Web access: https://vscode.dev/tunnel/{tunnel_name}")
        print(f"📋 Log file: tunnel.log")
        
        # Wait and check status
        time.sleep(3)
        
        status_result = subprocess.run(
            f'"{code_path}" tunnel status',
            shell=True,
            capture_output=True,
            text=True
        )
        
        if status_result.returncode == 0:
            print("\n📊 Tunnel Status:")
            print(status_result.stdout)
        
        return True
        
    except Exception as e:
        print(f"❌ Error starting tunnel: {e}")
        return False

def main():
    print("🛠️  VSCode Authentication Fix")
    print("=" * 40)
    
    if run_auth_with_timeout():
        print("\n✅ Authentication process completed!")
        
        if verify_authentication():
            choice = input("\n🚀 Start tunnel now? (y/N): ").strip().lower()
            if choice == 'y':
                start_tunnel_after_auth()
        else:
            print("\n💡 Try the authentication again if it failed")
    else:
        print("\n❌ Authentication process failed")
        print("\n🔧 Alternative manual commands:")
        print("1. ~/.local/bin/code tunnel user login --provider github")
        print("2. ~/.local/bin/code tunnel --name YOUR_NAME --accept-server-license-terms")

if __name__ == "__main__":
    main()