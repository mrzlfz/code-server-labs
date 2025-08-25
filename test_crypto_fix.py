#!/usr/bin/env python3
"""
Test script to verify crypto polyfill functionality
"""

import subprocess
import sys
from pathlib import Path

def test_crypto_polyfill():
    """Test if the crypto polyfill works correctly."""
    print("🧪 Testing Crypto Polyfill")
    print("=" * 40)
    
    # Path to the polyfill
    polyfill_file = Path.home() / ".local" / "share" / "code-server" / "polyfills" / "crypto-polyfill.js"
    
    if not polyfill_file.exists():
        print("❌ Crypto polyfill file not found!")
        print(f"Expected location: {polyfill_file}")
        return False
    
    print(f"✅ Crypto polyfill found: {polyfill_file}")
    
    # Test the polyfill with Node.js
    test_script = '''
    // Load the polyfill
    require('%s');
    
    // Test crypto module
    try {
        const crypto = require('crypto');
        console.log('✅ Crypto module loaded successfully');
        
        // Test randomBytes
        const randomBytes = crypto.randomBytes(16);
        console.log('✅ randomBytes works:', randomBytes.length, 'bytes');
        
        // Test createHash
        const hash = crypto.createHash('sha256');
        hash.update('test');
        const digest = hash.digest('hex');
        console.log('✅ createHash works:', digest);
        
        // Test createHmac
        const hmac = crypto.createHmac('sha256', 'secret');
        hmac.update('test');
        const hmacDigest = hmac.digest('hex');
        console.log('✅ createHmac works:', hmacDigest);
        
        console.log('🎉 All crypto tests passed!');
        
    } catch (error) {
        console.error('❌ Crypto test failed:', error.message);
        process.exit(1);
    }
    ''' % str(polyfill_file).replace('\\', '\\\\')
    
    try:
        # Run the test with Node.js
        result = subprocess.run(
            ['node', '-e', test_script],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            print("\n📊 Test Results:")
            print(result.stdout)
            return True
        else:
            print("\n❌ Test Failed:")
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ Test timed out")
        return False
    except FileNotFoundError:
        print("❌ Node.js not found. Please install Node.js to test the polyfill.")
        return False
    except Exception as e:
        print(f"❌ Test error: {e}")
        return False

def test_extension_injection():
    """Test if extensions have been properly injected."""
    print("\n🔍 Testing Extension Injection")
    print("=" * 40)
    
    extensions_dir = Path.home() / ".local" / "share" / "code-server" / "extensions"
    
    if not extensions_dir.exists():
        print("ℹ️  No extensions directory found")
        return True
    
    # Look for Augment extension
    augment_dirs = list(extensions_dir.glob("*augment*"))
    
    if not augment_dirs:
        print("ℹ️  No Augment extensions found")
        return True
    
    injected_count = 0
    for augment_dir in augment_dirs:
        extension_js = augment_dir / "out" / "extension.js"
        if extension_js.exists():
            try:
                with open(extension_js, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                if "CRYPTO_POLYFILL_INJECTED" in content:
                    print(f"✅ Crypto polyfill injected: {extension_js}")
                    injected_count += 1
                else:
                    print(f"⚠️  No crypto polyfill: {extension_js}")
                    
            except Exception as e:
                print(f"❌ Error checking {extension_js}: {e}")
    
    print(f"\n📊 Injection Results: {injected_count} extensions patched")
    return injected_count > 0

if __name__ == "__main__":
    print("🔧 Crypto Fix Verification Tool")
    print("=" * 50)
    
    # Test polyfill functionality
    polyfill_ok = test_crypto_polyfill()
    
    # Test extension injection
    injection_ok = test_extension_injection()
    
    print("\n" + "=" * 50)
    print("📋 Summary:")
    print(f"   • Crypto Polyfill: {'✅ Working' if polyfill_ok else '❌ Failed'}")
    print(f"   • Extension Injection: {'✅ Applied' if injection_ok else 'ℹ️  No extensions found'}")
    
    if polyfill_ok:
        print("\n🎉 Crypto fix is working correctly!")
        print("💡 You can now start Code Server and the Augment extension should work.")
    else:
        print("\n⚠️  Crypto fix needs attention.")
        print("💡 Try running the fix again from the main menu (option 8).")
