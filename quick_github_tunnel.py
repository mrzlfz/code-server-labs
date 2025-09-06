#!/usr/bin/env python3
"""
Quick VSCode Tunnel Setup with GitHub Authentication
Bypasses interactive menu by using command-line flags
"""

import os
import sys
import subprocess
from pathlib import Path

def setup_github_tunnel():
    """Setup VSCode tunnel dengan GitHub authentication langsung"""
    
    # Path ke code binary
    code_path = Path.home() / ".local" / "bin" / "code"
    
    if not code_path.exists():
        print("❌ VSCode Server belum terinstall!")
        print("💡 Install dulu dengan: python3 vscode_server_installer.py")
        return False
    
    # Get tunnel name
    tunnel_name = input("📝 Masukkan nama tunnel: ").strip()
    if not tunnel_name:
        print("❌ Nama tunnel tidak boleh kosong!")
        return False
    
    print(f"🔧 Setting up GitHub tunnel: {tunnel_name}")
    print("🤖 Using GitHub authentication directly...")
    
    # Try different approaches to force GitHub auth
    approaches = [
        # Approach 1: Use environment variable
        {
            "name": "Environment Variable",
            "env": {"VSCODE_CLI_AUTH_PROVIDER": "github"},
            "command": f'"{code_path}" tunnel --name "{tunnel_name}" --accept-server-license-terms'
        },
        # Approach 2: Use --auth-provider flag if available
        {
            "name": "Auth Provider Flag",
            "env": {},
            "command": f'"{code_path}" tunnel --name "{tunnel_name}" --accept-server-license-terms --auth-provider github'
        },
        # Approach 3: Direct GitHub login command
        {
            "name": "GitHub Login Command",
            "env": {},
            "command": f'"{code_path}" tunnel --name "{tunnel_name}" --accept-server-license-terms --provider github'
        }
    ]
    
    for approach in approaches:
        print(f"\n🎯 Trying: {approach['name']}")
        
        try:
            env = os.environ.copy()
            env.update(approach['env'])
            
            print(f"▶️  Command: {approach['command']}")
            if approach['env']:
                print(f"🌍 Environment: {approach['env']}")
            
            # Execute with custom environment
            process = subprocess.Popen(
                approach['command'],
                shell=True,
                env=env,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True
            )
            
            print("⏳ Starting process...")
            
            # Monitor for first few seconds
            import time
            start_time = time.time()
            
            while time.time() - start_time < 10:  # Monitor for 10 seconds
                line = process.stdout.readline()
                if line:
                    line = line.strip()
                    print(f"📄 {line}")
                    
                    # Check if we got past the menu selection
                    if "github.com/login/device" in line.lower():
                        print("✅ Successfully bypassed menu selection!")
                        print("🌐 GitHub device authentication URL detected")
                        print("👉 Continue with the authentication in your browser")
                        
                        # Let process continue running
                        print("\n⏳ Process continues running for authentication...")
                        print("🔄 The process will wait for you to complete GitHub authentication")
                        print("📱 Go to the GitHub URL above and enter the device code")
                        
                        # Wait for completion
                        try:
                            process.wait(timeout=300)  # 5 minute timeout
                            print("✅ Process completed!")
                            return True
                        except subprocess.TimeoutExpired:
                            print("⏰ Process timed out after 5 minutes")
                            process.terminate()
                            return False
                    
                    elif "How would you like to log in" in line:
                        print("❌ Still showing menu selection - trying next approach")
                        process.terminate()
                        break
                
                # Check if process ended
                if process.poll() is not None:
                    break
                
                time.sleep(0.1)
            else:
                print("⏰ Monitoring timeout - terminating attempt")
                process.terminate()
                
        except Exception as e:
            print(f"❌ Error: {e}")
    
    print("\n❌ All approaches failed")
    print("💡 Try the enhanced vscode_server_installer.py instead")
    return False

if __name__ == "__main__":
    print("🚀 Quick GitHub Tunnel Setup")
    print("=" * 40)
    setup_github_tunnel()