#!/usr/bin/env python3
"""
Token-based Authentication Solution
Bypasses device flow issues by using GitHub Personal Access Token
"""

import subprocess
import json
from pathlib import Path

def create_github_token_instructions():
    """Show instructions for creating GitHub token"""
    print("🔑 GitHub Personal Access Token Setup")
    print("=" * 45)
    print("\n📋 Steps to create token:")
    print("1. Go to: https://github.com/settings/tokens")
    print("2. Click 'Generate new token' -> 'Generate new token (classic)'")
    print("3. Token name: 'VSCode CLI'")
    print("4. Expiration: '90 days' (or your preference)")
    print("5. Select scopes:")
    print("   ✅ user:email")
    print("   ✅ read:user")
    print("6. Click 'Generate token'")
    print("7. Copy the token (it starts with 'ghp_')")
    print("\n⚠️  Important: Copy the token now - you won't see it again!")

def use_token_auth():
    """Use access token for authentication"""
    code_path = Path.home() / ".local" / "bin" / "code"
    
    create_github_token_instructions()
    
    token = input("\n🔢 Enter your GitHub token (ghp_...): ").strip()
    
    if not token:
        print("❌ No token provided")
        return False
    
    if not token.startswith('ghp_'):
        print("⚠️  Token should start with 'ghp_' - are you sure this is correct?")
        confirm = input("Continue anyway? (y/N): ").strip().lower()
        if confirm != 'y':
            return False
    
    print("🔐 Authenticating with token...")
    
    try:
        # Use token for authentication
        auth_command = f'"{code_path}" tunnel user login --access-token "{token}"'
        
        result = subprocess.run(
            auth_command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            print("✅ Token authentication successful!")
            
            # Verify authentication
            verify_result = subprocess.run(
                f'"{code_path}" tunnel user show',
                shell=True,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if verify_result.returncode == 0:
                print(f"👤 Authenticated as: {verify_result.stdout.strip()}")
                return True
            else:
                print("❌ Authentication verification failed")
                return False
                
        else:
            print("❌ Token authentication failed")
            print(f"Error: {result.stderr.strip()}")
            return False
            
    except Exception as e:
        print(f"❌ Authentication error: {e}")
        return False

def start_tunnel_with_auth():
    """Start tunnel after successful authentication"""
    code_path = Path.home() / ".local" / "bin" / "code"
    
    # Get tunnel name
    config_file = Path.home() / ".config" / "vscode-server-installer" / "config.json"
    tunnel_name = "deer-codev"
    
    if config_file.exists():
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
                tunnel_name = config.get('tunnel_name', tunnel_name)
        except:
            pass
    
    new_name = input(f"\n📝 Tunnel name [{tunnel_name}]: ").strip()
    if new_name:
        tunnel_name = new_name
    
    print(f"🚀 Starting tunnel: {tunnel_name}")
    
    # Start tunnel
    tunnel_command = f'"{code_path}" tunnel --name "{tunnel_name}" --accept-server-license-terms'
    
    print(f"▶️  Command: {tunnel_command}")
    print("🔄 Starting tunnel...")
    
    try:
        # Start in background
        bg_command = f"nohup {tunnel_command} > tunnel_output.log 2>&1 &"
        subprocess.run(bg_command, shell=True, check=True)
        
        print("✅ Tunnel started in background!")
        print(f"🌐 Web access: https://vscode.dev/tunnel/{tunnel_name}")
        print(f"📋 Log file: tunnel_output.log")
        
        # Check status after a moment
        import time
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
    print("🚀 Token-based Authentication Solution")
    print("=" * 40)
    print("\nThis method bypasses the device flow issues")
    print("by using a GitHub Personal Access Token.\n")
    
    if use_token_auth():
        print("\n✅ Authentication successful!")
        
        choice = input("\n🚀 Start tunnel now? (Y/n): ").strip().lower()
        if choice != 'n':
            if start_tunnel_with_auth():
                print("\n🎉 Setup complete!")
                print("\n📖 Next steps:")
                print("1. Open https://vscode.dev in browser")
                print("2. Click 'Connect to Tunnel'")
                print("3. Enter your tunnel name")
                print("4. Start coding!")
            else:
                print("\n❌ Tunnel setup failed")
        
    else:
        print("\n❌ Authentication failed")
        print("\n💡 Alternative:")
        print("Try the device flow one more time with better network connection")

if __name__ == "__main__":
    main()