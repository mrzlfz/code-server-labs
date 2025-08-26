#!/usr/bin/env python3
"""
Verify Augment Extension Fix
===========================

This script helps verify that the Augment extension crypto fix is working
by checking the extension files and testing the crypto functionality.
"""

import os
import sys
import subprocess
from pathlib import Path

def check_extension_files():
    """Check if Augment extension files exist and have been patched."""
    print("🔍 Checking Augment extension files...")
    
    extensions_dir = Path.home() / ".local" / "share" / "code-server" / "extensions"
    if not extensions_dir.exists():
        print(f"❌ Extensions directory not found: {extensions_dir}")
        return False
    
    # Find Augment extensions
    augment_dirs = list(extensions_dir.glob("*augment*"))
    if not augment_dirs:
        print("❌ No Augment extensions found")
        return False
    
    print(f"✅ Found {len(augment_dirs)} Augment extension(s):")
    
    patched_count = 0
    for ext_dir in augment_dirs:
        print(f"  📁 {ext_dir.name}")
        
        # Check for extension.js files
        extension_files = [
            ext_dir / "out" / "extension.js",
            ext_dir / "dist" / "extension.js",
            ext_dir / "lib" / "extension.js",
            ext_dir / "extension.js"
        ]
        
        for ext_file in extension_files:
            if ext_file.exists():
                print(f"    📄 Found: {ext_file.relative_to(ext_dir)}")
                
                # Check if crypto fix is present
                try:
                    with open(ext_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    if "AGGRESSIVE CRYPTO" in content:
                        print(f"    ✅ Aggressive crypto fix detected")
                        patched_count += 1
                    elif "Enhanced crypto module polyfill" in content:
                        print(f"    ⚠️  Old crypto polyfill detected (may not work)")
                    else:
                        print(f"    ❌ No crypto fix detected")
                    
                    # Check for backup
                    backup_file = ext_file.with_suffix('.js.original')
                    if backup_file.exists():
                        print(f"    💾 Backup file exists: {backup_file.name}")
                    
                except Exception as e:
                    print(f"    ❌ Error reading file: {e}")
                
                break
    
    return patched_count > 0

def check_polyfill_files():
    """Check if crypto polyfill files exist."""
    print("\n🔍 Checking crypto polyfill files...")
    
    polyfill_dir = Path.home() / ".local" / "share" / "code-server" / "polyfills"
    if not polyfill_dir.exists():
        print(f"❌ Polyfill directory not found: {polyfill_dir}")
        return False
    
    files_to_check = [
        "crypto-polyfill.js",
        "web-worker-crypto.js"
    ]
    
    found_files = 0
    for filename in files_to_check:
        file_path = polyfill_dir / filename
        if file_path.exists():
            print(f"✅ Found: {filename}")
            found_files += 1
        else:
            print(f"❌ Missing: {filename}")
    
    return found_files > 0

def check_code_server_config():
    """Check code-server configuration."""
    print("\n🔍 Checking code-server configuration...")
    
    config_file = Path.home() / ".config" / "code-server" / "config.yaml"
    if not config_file.exists():
        print(f"❌ Config file not found: {config_file}")
        return False
    
    try:
        with open(config_file, 'r') as f:
            config_content = f.read()
        
        print(f"✅ Config file exists: {config_file}")
        
        # Check for important settings
        if "extensions-dir:" in config_content:
            print("✅ Extensions directory configured")
        if "user-data-dir:" in config_content:
            print("✅ User data directory configured")
        
        return True
        
    except Exception as e:
        print(f"❌ Error reading config: {e}")
        return False

def test_crypto_in_node():
    """Test if crypto works in Node.js environment."""
    print("\n🧪 Testing crypto in Node.js environment...")
    
    test_script = '''
try {
    const crypto = require('crypto');
    const bytes = crypto.randomBytes(16);
    console.log("✅ Crypto test passed, bytes length:", bytes.length);
} catch (error) {
    console.log("❌ Crypto test failed:", error.message);
    process.exit(1);
}
'''
    
    try:
        result = subprocess.run(['node', '-e', test_script], 
                              capture_output=True, text=True, timeout=5)
        
        if result.returncode == 0:
            print("✅ Node.js crypto test passed")
            print(f"   Output: {result.stdout.strip()}")
            return True
        else:
            print("❌ Node.js crypto test failed")
            print(f"   Error: {result.stderr.strip()}")
            return False
            
    except subprocess.TimeoutExpired:
        print("⚠️  Node.js crypto test timed out")
        return False
    except FileNotFoundError:
        print("❌ Node.js not found")
        return False

def check_code_server_process():
    """Check if code-server is running."""
    print("\n🔍 Checking code-server process...")
    
    try:
        # Try to find code-server process
        if sys.platform == "win32":
            result = subprocess.run(["tasklist", "/FI", "IMAGENAME eq code-server.exe"],
                                  capture_output=True, text=True)
            if "code-server.exe" in result.stdout:
                print("✅ Code-server is running")
                return True
        else:
            result = subprocess.run(["pgrep", "-f", "code-server"],
                                  capture_output=True, text=True)
            if result.returncode == 0:
                print("✅ Code-server is running")
                return True
        
        print("❌ Code-server is not running")
        return False
        
    except Exception as e:
        print(f"⚠️  Could not check code-server process: {e}")
        return False

def main():
    """Run all verification checks."""
    print("🔍 Augment Extension Crypto Fix Verification")
    print("=" * 50)
    
    checks = [
        ("Extension Files", check_extension_files),
        ("Polyfill Files", check_polyfill_files),
        ("Code-server Config", check_code_server_config),
        ("Node.js Crypto", test_crypto_in_node),
        ("Code-server Process", check_code_server_process)
    ]
    
    results = []
    for check_name, check_func in checks:
        try:
            result = check_func()
            results.append((check_name, result))
        except Exception as e:
            print(f"❌ {check_name} check failed: {e}")
            results.append((check_name, False))
    
    # Summary
    print("\n📊 Verification Summary:")
    print("=" * 50)
    
    passed = 0
    for check_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"  {check_name}: {status}")
        if result:
            passed += 1
    
    total = len(results)
    print(f"\nOverall: {passed}/{total} checks passed")
    
    # Recommendations
    print("\n💡 Recommendations:")
    if passed == total:
        print("🎉 All checks passed! The Augment extension should work now.")
        print("   • Try opening VS Code and check if Augment loads without errors")
        print("   • Check the browser console for any remaining crypto errors")
    elif passed >= 3:
        print("⚠️  Most checks passed, but some issues remain:")
        if not results[4][1]:  # Code-server not running
            print("   • Start code-server to test the extension")
        if not results[0][1]:  # Extension files issue
            print("   • Re-run the crypto fix: python code_server_colab_setup.py (option 8)")
    else:
        print("❌ Multiple issues detected:")
        print("   • Re-run the crypto fix: python code_server_colab_setup.py (option 8)")
        print("   • Make sure code-server is properly installed")
        print("   • Check that the Augment extension is installed")
    
    return passed >= 3

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
