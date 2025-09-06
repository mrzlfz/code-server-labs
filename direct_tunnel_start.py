#!/usr/bin/env python3
"""
Direct Tunnel Start - Bypass authentication issues
Since you've already authorized GitHub, let's try direct tunnel start
"""

import subprocess
import time
import json
from pathlib import Path

def check_existing_auth():
    """Check if there's already valid authentication"""
    code_path = Path.home() / ".local" / "bin" / "code"
    
    try:
        result = subprocess.run(
            f'"{code_path}" tunnel user show',
            shell=True,
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0:
            print("✅ Found existing authentication!")
            print(f"👤 User: {result.stdout.strip()}")
            return True
        else:
            print("❌ No valid authentication found")
            return False
            
    except Exception as e:
        print(f"⚠️  Error checking auth: {e}")
        return False

def try_direct_tunnel_start():
    """Try to start tunnel directly"""
    code_path = Path.home() / ".local" / "bin" / "code"
    
    # Get tunnel name
    config_file = Path.home() / ".config" / "vscode-server-installer" / "config.json"
    tunnel_name = "deer-codev"  # from your logs
    
    if config_file.exists():
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
                tunnel_name = config.get('tunnel_name', tunnel_name)
        except:
            pass
    
    print(f"🚀 Attempting to start tunnel: {tunnel_name}")
    
    # Try starting tunnel directly
    tunnel_command = f'"{code_path}" tunnel --name "{tunnel_name}" --accept-server-license-terms'
    
    print(f"▶️  Command: {tunnel_command}")
    print("🔄 Starting tunnel process...")
    
    try:
        # Start process and monitor for a short time
        process = subprocess.Popen(
            tunnel_command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True
        )
        
        print(f"📋 Process PID: {process.pid}")
        print("⏳ Monitoring startup (15 seconds)...")
        
        start_time = time.time()
        success_indicators = []
        
        while time.time() - start_time < 15:  # Monitor for 15 seconds
            line = process.stdout.readline()
            
            if line:
                line = line.strip()
                print(f"📄 {line}")
                
                # Check for success indicators
                if "tunnel" in line.lower() and any(word in line.lower() for word in ["ready", "started", "running"]):
                    success_indicators.append("tunnel_ready")
                    print("✅ Tunnel appears to be ready!")
                
                if "open" in line.lower() and "vscode.dev" in line.lower():
                    success_indicators.append("web_url")
                    print("✅ Web URL detected!")
                
                if "github.com/login/device" in line:
                    print("⚠️  Still asking for device authentication...")
                    print("💡 Your previous authorization might not have been saved")
                    return False
            
            # Check if process ended
            if process.poll() is not None:
                if process.returncode == 0:
                    print("✅ Process completed successfully!")
                    return True
                else:
                    print(f"❌ Process failed with code: {process.returncode}")
                    return False
            
            time.sleep(0.5)
        
        # After monitoring period
        if success_indicators:
            print(f"✅ Detected success indicators: {success_indicators}")
            print("🚀 Tunnel appears to be running!")
            print(f"🌐 Try accessing: https://vscode.dev/tunnel/{tunnel_name}")
            
            # Keep process running in background
            print("📋 Process continues in background...")
            return True
        else:
            print("⚠️  No clear success indicators detected")
            print("🔄 Process might still be initializing...")
            return False
            
    except Exception as e:
        print(f"❌ Error starting tunnel: {e}")
        return False

def manual_auth_restart():
    """Restart authentication manually"""
    code_path = Path.home() / ".local" / "bin" / "code"
    
    print("🔄 Attempting manual authentication restart...")
    
    # Clear any existing auth state
    print("🧹 Clearing auth state...")
    
    try:
        # Try to logout first
        subprocess.run(f'"{code_path}" tunnel user logout', shell=True, capture_output=True)
        print("✅ Logged out (or no session to logout)")
    except:
        pass
    
    # Start fresh auth
    print("🔐 Starting fresh authentication...")
    auth_command = f'"{code_path}" tunnel user login --provider github'
    
    print(f"▶️  Running: {auth_command}")
    print("👉 Complete the GitHub authentication when prompted")
    
    try:
        result = subprocess.run(auth_command, shell=True, timeout=120)  # 2 minute timeout
        
        if result.returncode == 0:
            print("✅ Authentication completed!")
            return True
        else:
            print("❌ Authentication failed")
            return False
            
    except subprocess.TimeoutExpired:
        print("⏰ Authentication timed out")
        return False
    except Exception as e:
        print(f"❌ Authentication error: {e}")
        return False

def main():
    print("🎯 Direct Tunnel Start")
    print("=" * 30)
    
    # Step 1: Check existing auth
    print("\n1️⃣ Checking existing authentication...")
    if check_existing_auth():
        # Step 2: Try direct tunnel start
        print("\n2️⃣ Attempting direct tunnel start...")
        if try_direct_tunnel_start():
            print("\n✅ Success! Tunnel should be running")
            print("🌐 Access your tunnel at: https://vscode.dev")
            return
    
    # Step 3: If direct start failed, try manual auth restart
    print("\n3️⃣ Direct start failed, trying manual auth...")
    if manual_auth_restart():
        print("\n4️⃣ Retrying tunnel start after auth...")
        if try_direct_tunnel_start():
            print("\n✅ Success! Tunnel should be running")
            return
    
    print("\n❌ All attempts failed")
    print("\n🔧 Manual troubleshooting:")
    print("1. Check auth: ~/.local/bin/code tunnel user show")
    print("2. Login manually: ~/.local/bin/code tunnel user login --provider github")
    print("3. Start tunnel: ~/.local/bin/code tunnel --name deer-codev --accept-server-license-terms")

if __name__ == "__main__":
    main()