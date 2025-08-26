#!/usr/bin/env python3
"""
VSCode Server Authentication Fix Script
Diagnoses and fixes authentication issues with VSCode Server tunnels
"""

import sys
import os
import subprocess
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from code_server_colab_setup import CodeServerSetup

def diagnose_vscode_auth_issue():
    """Diagnose VSCode Server authentication issues."""
    print("🔍 VSCode Server Authentication Diagnosis")
    print("=" * 50)
    
    app = CodeServerSetup()
    
    # Check 1: VSCode CLI Installation
    print("\n1. Checking VSCode CLI installation...")
    vscode_bin = Path(app.config.get("vscode_server.bin_path", str(Path.home() / ".local" / "bin" / "code")))
    if vscode_bin.exists():
        print(f"✅ VSCode CLI found: {vscode_bin}")
        try:
            result = subprocess.run([str(vscode_bin), "--version"], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                print(f"✅ Version: {result.stdout.strip()}")
            else:
                print(f"⚠️  Version check failed: {result.stderr}")
        except Exception as e:
            print(f"❌ Version check error: {e}")
    else:
        print(f"❌ VSCode CLI not found: {vscode_bin}")
        return False
    
    # Check 2: Authentication Status
    print("\n2. Checking authentication status...")
    try:
        result = subprocess.run([str(vscode_bin), "tunnel", "user", "show"], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print("✅ User is authenticated")
            print(f"📝 User info: {result.stdout.strip()}")
            auth_ok = True
        else:
            print("❌ User is not authenticated")
            print(f"📝 Error: {result.stderr.strip()}")
            auth_ok = False
    except Exception as e:
        print(f"❌ Auth check failed: {e}")
        auth_ok = False
    
    # Check 3: Running Processes
    print("\n3. Checking running VSCode processes...")
    try:
        result = subprocess.run(["pgrep", "-f", "code.*tunnel"], capture_output=True, text=True)
        if result.returncode == 0:
            pids = result.stdout.strip().split('\n')
            print(f"✅ Found {len(pids)} VSCode tunnel process(es)")
            for pid in pids:
                if pid:
                    print(f"   PID: {pid}")
        else:
            print("❌ No VSCode tunnel processes found")
    except Exception as e:
        print(f"⚠️  Process check failed: {e}")
    
    # Check 4: Tunnel Status
    print("\n4. Checking tunnel status...")
    try:
        result = subprocess.run([str(vscode_bin), "tunnel", "status"], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print("✅ Tunnel status:")
            print(f"📝 {result.stdout.strip()}")
        else:
            print("❌ No active tunnels")
            print(f"📝 {result.stderr.strip()}")
    except Exception as e:
        print(f"⚠️  Tunnel status check failed: {e}")
    
    return auth_ok

def fix_vscode_auth():
    """Fix VSCode Server authentication issues."""
    print("\n🔧 VSCode Server Authentication Fix")
    print("=" * 40)
    
    app = CodeServerSetup()
    vscode_bin = Path(app.config.get("vscode_server.bin_path", str(Path.home() / ".local" / "bin" / "code")))
    
    if not vscode_bin.exists():
        print("❌ VSCode CLI not found. Please install VSCode Server first.")
        return False
    
    # Step 1: Stop any running tunnels
    print("\n1. Stopping existing tunnels...")
    try:
        subprocess.run(["pkill", "-f", "code.*tunnel"], timeout=10)
        print("✅ Stopped existing tunnel processes")
    except Exception as e:
        print(f"⚠️  Could not stop processes: {e}")
    
    # Step 2: Clear authentication if needed
    print("\n2. Checking authentication...")
    try:
        result = subprocess.run([str(vscode_bin), "tunnel", "user", "show"], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode != 0:
            print("❌ Not authenticated, need to login")
            
            # Choose provider
            print("\n🔐 Choose authentication provider:")
            print("1. GitHub")
            print("2. Microsoft")
            
            while True:
                try:
                    choice = input("👉 Choose (1 or 2): ").strip()
                    if choice == "1":
                        provider = "github"
                        break
                    elif choice == "2":
                        provider = "microsoft"
                        break
                    else:
                        print("❌ Please enter 1 or 2")
                except KeyboardInterrupt:
                    print("\n❌ Cancelled")
                    return False
            
            # Authenticate
            print(f"\n🔐 Authenticating with {provider}...")
            print("💡 Follow the prompts and complete authentication in your browser")
            print("-" * 40)
            
            try:
                result = subprocess.run([str(vscode_bin), "tunnel", "user", "login", "--provider", provider], 
                                      timeout=300)
                if result.returncode == 0:
                    print("-" * 40)
                    print("✅ Authentication successful!")
                else:
                    print("-" * 40)
                    print("❌ Authentication failed")
                    return False
            except subprocess.TimeoutExpired:
                print("⏳ Authentication timed out")
                return False
            except KeyboardInterrupt:
                print("\n❌ Authentication cancelled")
                return False
        else:
            print("✅ Already authenticated")
    except Exception as e:
        print(f"❌ Authentication check failed: {e}")
        return False
    
    # Step 3: Create tunnel
    print("\n3. Creating tunnel...")
    tunnel_name = f"colab-fixed-{int(__import__('time').time())}"
    
    print(f"🚇 Creating tunnel: {tunnel_name}")
    print("💡 This will show authentication URLs if needed")
    print("-" * 40)
    
    try:
        # Start tunnel in foreground so user can see output
        cmd = [str(vscode_bin), "tunnel", "--name", tunnel_name, "--accept-server-license-terms"]
        print(f"🚀 Running: {' '.join(cmd)}")
        print("👆 Watch for authentication URLs and tunnel creation")
        print("🛑 Press Ctrl+C when you see the tunnel URL to stop")
        
        subprocess.run(cmd)
        
    except KeyboardInterrupt:
        print("\n✅ Tunnel creation process stopped")
        print("💡 If you saw a tunnel URL, the fix was successful!")
        return True
    except Exception as e:
        print(f"❌ Tunnel creation failed: {e}")
        return False

def main():
    """Main function."""
    print("🔧 VSCode Server Authentication Troubleshooter")
    print("=" * 60)
    
    # Diagnose the issue
    auth_ok = diagnose_vscode_auth_issue()
    
    if not auth_ok:
        print("\n💡 Authentication issues detected!")
        print("🔧 Would you like to try fixing them?")
        
        try:
            fix_choice = input("👉 Fix authentication issues? (y/N): ").strip().lower()
            if fix_choice == 'y':
                success = fix_vscode_auth()
                if success:
                    print("\n🎉 Authentication fix completed!")
                    print("💡 You can now try starting VSCode Server again")
                else:
                    print("\n❌ Fix failed. Please try manual authentication")
            else:
                print("❌ Fix cancelled")
        except KeyboardInterrupt:
            print("\n❌ Cancelled")
    else:
        print("\n✅ Authentication appears to be working!")
        print("💡 The issue might be with tunnel creation or network connectivity")

if __name__ == "__main__":
    main()
