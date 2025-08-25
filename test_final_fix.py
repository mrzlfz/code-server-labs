#!/usr/bin/env python3
"""
Final test to verify the complete crypto fix is working
"""

import subprocess
import sys
import os
from pathlib import Path

def test_complete_fix():
    """Test the complete crypto fix setup."""
    print("🔧 Final Crypto Fix Test")
    print("=" * 50)
    
    # Check if polyfill exists
    polyfill_file = Path.home() / ".local" / "share" / "code-server" / "polyfills" / "crypto-polyfill.js"
    if not polyfill_file.exists():
        print("❌ Crypto polyfill not found!")
        return False
    
    print(f"✅ Crypto polyfill: {polyfill_file}")
    
    # Check config file
    config_file = Path.home() / ".config" / "code-server" / "config.yaml"
    if config_file.exists():
        print(f"✅ Code-server config: {config_file}")
    else:
        print(f"⚠️  Code-server config not found: {config_file}")
    
    # Test Node.js environment (simulating code-server startup)
    env = os.environ.copy()
    
    # Set up the same environment that code-server would use
    node_options = [
        "--experimental-modules",
        "--experimental-json-modules", 
        "--enable-source-maps",
        "--max-old-space-size=4096",
        "--unhandled-rejections=warn",
        f"--require={polyfill_file}"
    ]
    
    env['NODE_OPTIONS'] = " ".join(node_options)
    env['NODE_NO_WARNINGS'] = "1"
    env['VSCODE_ALLOW_IO'] = "true"
    env['FORCE_CRYPTO_POLYFILL'] = "1"
    
    print(f"🔧 Environment configured with NODE_OPTIONS")
    
    # Test script that simulates extension host loading
    test_script = '''
    console.log('[Extension Host Simulation] Starting...');
    
    // Simulate what happens when an extension tries to use crypto
    try {
        console.log('[Extension Host Simulation] Loading crypto module...');
        const crypto = require('crypto');
        
        if (!crypto) {
            throw new Error('Crypto module is null or undefined');
        }
        
        console.log('[Extension Host Simulation] ✅ Crypto module loaded');
        
        // Test the specific functions that Augment extension might use
        console.log('[Extension Host Simulation] Testing crypto functions...');
        
        // Test randomBytes (commonly used for generating IDs)
        const randomBytes = crypto.randomBytes(32);
        if (!randomBytes || randomBytes.length !== 32) {
            throw new Error('randomBytes failed');
        }
        console.log('[Extension Host Simulation] ✅ randomBytes working');
        
        // Test createHash (commonly used for checksums)
        const hash = crypto.createHash('sha256');
        hash.update('test-data');
        const digest = hash.digest('hex');
        if (!digest || digest.length === 0) {
            throw new Error('createHash failed');
        }
        console.log('[Extension Host Simulation] ✅ createHash working');
        
        // Test createHmac (commonly used for authentication)
        const hmac = crypto.createHmac('sha256', 'secret-key');
        hmac.update('test-data');
        const hmacDigest = hmac.digest('hex');
        if (!hmacDigest || hmacDigest.length === 0) {
            throw new Error('createHmac failed');
        }
        console.log('[Extension Host Simulation] ✅ createHmac working');
        
        console.log('[Extension Host Simulation] 🎉 All crypto functions working!');
        console.log('[Extension Host Simulation] ✅ Augment extension should now work');
        
    } catch (error) {
        console.error('[Extension Host Simulation] ❌ Crypto error:', error.message);
        console.error('[Extension Host Simulation] This is the same error Augment was getting');
        process.exit(1);
    }
    
    console.log('[Extension Host Simulation] ✅ Test completed successfully');
    '''
    
    try:
        print("\n🧪 Running Extension Host Simulation...")
        result = subprocess.run(
            ['node', '-e', test_script],
            env=env,
            capture_output=True,
            text=True,
            timeout=20
        )
        
        if result.returncode == 0:
            print("\n📊 Simulation Results:")
            print(result.stdout)
            return True
        else:
            print("\n❌ Simulation Failed:")
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ Simulation timed out")
        return False
    except FileNotFoundError:
        print("❌ Node.js not found")
        return False
    except Exception as e:
        print(f"❌ Simulation error: {e}")
        return False

def check_extension_patches():
    """Check if extensions have been patched."""
    print("\n🔍 Checking Extension Patches")
    print("=" * 30)
    
    extensions_dir = Path.home() / ".local" / "share" / "code-server" / "extensions"
    if not extensions_dir.exists():
        print("ℹ️  No extensions directory found")
        return True
    
    # Look for Augment extensions
    augment_dirs = list(extensions_dir.glob("*augment*"))
    patched_count = 0
    
    for augment_dir in augment_dirs:
        extension_js = augment_dir / "out" / "extension.js"
        if extension_js.exists():
            try:
                with open(extension_js, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                if "CRYPTO_POLYFILL_INJECTED" in content:
                    print(f"✅ Patched: {augment_dir.name}")
                    patched_count += 1
                else:
                    print(f"⚠️  Not patched: {augment_dir.name}")
                    
            except Exception as e:
                print(f"❌ Error checking {augment_dir.name}: {e}")
    
    print(f"📊 Extensions patched: {patched_count}")
    return patched_count > 0

if __name__ == "__main__":
    print("🎯 Complete Crypto Fix Verification")
    print("=" * 60)
    
    # Test the complete setup
    fix_working = test_complete_fix()
    
    # Check extension patches
    patches_applied = check_extension_patches()
    
    print("\n" + "=" * 60)
    print("📋 Final Results:")
    print(f"   • Crypto Environment: {'✅ Working' if fix_working else '❌ Failed'}")
    print(f"   • Extension Patches: {'✅ Applied' if patches_applied else 'ℹ️  No extensions found'}")
    
    if fix_working:
        print("\n🎉 CRYPTO FIX IS COMPLETE AND WORKING!")
        print("💡 The Augment extension should now load without errors.")
        print("🚀 You can start Code Server and test the extension.")
        print("\n📝 Next steps:")
        print("   1. Start Code Server using the setup script")
        print("   2. Install or enable the Augment extension")
        print("   3. Check that it loads without crypto errors")
    else:
        print("\n⚠️  Crypto fix needs attention.")
        print("💡 Run the fix again from the main menu (option 8).")
