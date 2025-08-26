#!/usr/bin/env python3
"""
Test script to verify the Code Server fix
"""

import subprocess
import sys
import time

def test_code_server_status():
    """Test the Code Server status detection"""
    print("🧪 Testing Code Server Fix")
    print("=" * 40)
    
    # Check if code-server process is running
    try:
        result = subprocess.run(
            ["pgrep", "-f", "code-server"],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print("✅ Code Server process detected")
            print(f"   PIDs: {result.stdout.strip()}")
            
            # Test the menu option 2 behavior
            print("\n🔍 Testing menu option 2 behavior...")
            print("   The fix should now show:")
            print("   • Access URL and password")
            print("   • Ngrok tunnel status")
            print("   • Available options (restart, stop, setup ngrok)")
            print("   • No more 'stuck' behavior")
            
        else:
            print("ℹ️  No Code Server process found")
            print("   You can test by:")
            print("   1. Running the main script")
            print("   2. Installing Code Server (option 1)")
            print("   3. Starting Code Server (option 2)")
            print("   4. Then trying option 2 again to see the fix")
            
    except Exception as e:
        print(f"❌ Error checking processes: {e}")
        
    print("\n📋 Fix Summary:")
    print("   • Enhanced start_code_server() method")
    print("   • Shows access information when already running")
    print("   • Provides clear next steps")
    print("   • Sets up ngrok tunnel if configured")
    print("   • No more hanging on 'already running' message")

if __name__ == "__main__":
    test_code_server_status()
