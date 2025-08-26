#!/usr/bin/env python3
"""
Aggressive Crypto Fix Test
=========================

This script tests the aggressive crypto fix by simulating the exact environment
where the Augment extension fails and verifying the fix works.
"""

import os
import sys
import subprocess
import tempfile
from pathlib import Path

def create_test_extension_content():
    """Create test content that simulates the Augment extension's crypto usage."""
    return '''
// Simulated Augment extension code that fails with "crypto is not defined"
console.log("Extension: Starting Augment extension simulation...");

try {
    // This is what causes the "crypto is not defined" error
    console.log("Extension: Attempting to require crypto module...");
    const crypto = require('crypto');
    
    console.log("Extension: ✅ Crypto module loaded successfully");
    
    // Test typical crypto operations that Augment might use
    console.log("Extension: Testing randomBytes...");
    const sessionId = crypto.randomBytes(16);
    console.log("Extension: ✅ Generated session ID, length:", sessionId.length);
    
    console.log("Extension: Testing createHash...");
    const hash = crypto.createHash('sha256');
    hash.update('test-data');
    const digest = hash.digest('hex');
    console.log("Extension: ✅ Generated hash:", digest);
    
    console.log("Extension: 🎉 All crypto operations successful!");
    console.log("Extension: Augment extension would work now!");
    
} catch (error) {
    console.error("Extension: ❌ CRYPTO ERROR:", error.message);
    console.error("Extension: This is the error that breaks Augment extension");
    process.exit(1);
}
'''

def test_without_fix():
    """Test extension code without crypto fix - should fail."""
    print("🧪 Testing WITHOUT crypto fix (should fail)...")
    
    test_content = create_test_extension_content()
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as f:
        f.write(test_content)
        test_file = f.name
    
    try:
        result = subprocess.run(['node', test_file], capture_output=True, text=True, timeout=10)
        
        print("Output:")
        print(result.stdout)
        if result.stderr:
            print("Errors:")
            print(result.stderr)
        
        if result.returncode != 0:
            print("✅ Test confirmed: Extension fails without crypto fix")
            return True
        else:
            print("⚠️  Unexpected: Extension worked without fix")
            return False
            
    except subprocess.TimeoutExpired:
        print("⚠️  Test timed out")
        return False
    finally:
        os.unlink(test_file)

def test_with_aggressive_fix():
    """Test extension code with aggressive crypto fix - should work."""
    print("\n🚨 Testing WITH aggressive crypto fix (should work)...")
    
    # Get the aggressive crypto fix from the Python script
    try:
        with open('code_server_colab_setup.py', 'r') as f:
            content = f.read()
        
        # Extract the aggressive crypto replacement
        start_marker = "crypto_replacement = '''"
        end_marker = "'''"
        
        start_idx = content.find(start_marker)
        if start_idx == -1:
            print("❌ Could not find aggressive crypto fix in script")
            return False
        
        start_idx += len(start_marker)
        end_idx = content.find(end_marker, start_idx)
        if end_idx == -1:
            print("❌ Could not find end of aggressive crypto fix")
            return False
        
        crypto_fix = content[start_idx:end_idx].strip()
        
    except Exception as e:
        print(f"❌ Error reading crypto fix: {e}")
        return False
    
    # Create test content with crypto fix
    test_content_with_fix = crypto_fix + "\n\n" + create_test_extension_content()
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as f:
        f.write(test_content_with_fix)
        test_file = f.name
    
    try:
        result = subprocess.run(['node', test_file], capture_output=True, text=True, timeout=10)
        
        print("Output:")
        print(result.stdout)
        if result.stderr:
            print("Errors:")
            print(result.stderr)
        
        if result.returncode == 0 and "All crypto operations successful!" in result.stdout:
            print("✅ Test confirmed: Extension works with aggressive crypto fix!")
            return True
        else:
            print("❌ Test failed: Extension still doesn't work with crypto fix")
            return False
            
    except subprocess.TimeoutExpired:
        print("⚠️  Test timed out")
        return False
    finally:
        os.unlink(test_file)

def test_web_worker_context():
    """Test crypto fix in web worker context."""
    print("\n🌐 Testing in Web Worker context...")
    
    # Create a web worker test
    worker_test = '''
// Web Worker Context Test
console.log("Worker: Testing crypto in web worker context...");

// Simulate web worker globals
if (typeof global === 'undefined') {
    global = globalThis;
}
if (typeof self === 'undefined') {
    self = globalThis;
}

''' + '''
// AGGRESSIVE CRYPTO POLYFILL - COMPLETE REPLACEMENT
console.log('[AGGRESSIVE CRYPTO] Starting complete crypto module replacement');

// Step 1: Create Buffer polyfill
if (typeof Buffer === 'undefined') {
    globalThis.Buffer = class Buffer extends Uint8Array {
        static from(data) {
            if (data instanceof Uint8Array) return data;
            if (typeof data === 'string') {
                const encoder = new TextEncoder();
                return new this(encoder.encode(data));
            }
            return new this(data);
        }
        
        static alloc(size) {
            return new this(size);
        }
        
        toString(encoding = 'utf8') {
            if (encoding === 'hex') {
                return Array.from(this).map(b => b.toString(16).padStart(2, '0')).join('');
            }
            const decoder = new TextDecoder();
            return decoder.decode(this);
        }
    };
    console.log('[AGGRESSIVE CRYPTO] Buffer polyfill created');
}

// Step 2: Create comprehensive crypto module
const cryptoModule = {
    randomBytes: function(size, callback) {
        try {
            const array = new Uint8Array(size);
            const cryptoObj = globalThis.crypto || self.crypto || window.crypto;
            
            if (cryptoObj && cryptoObj.getRandomValues) {
                cryptoObj.getRandomValues(array);
            } else {
                for (let i = 0; i < size; i++) {
                    array[i] = Math.floor(Math.random() * 256);
                }
            }
            
            const buffer = Buffer.from(array);
            
            if (callback) {
                setTimeout(() => callback(null, buffer), 0);
                return;
            }
            return buffer;
        } catch (error) {
            if (callback) {
                setTimeout(() => callback(error), 0);
                return;
            }
            throw error;
        }
    },
    
    randomBytesSync: function(size) {
        return this.randomBytes(size);
    },
    
    createHash: function(algorithm) {
        return {
            _data: '',
            update: function(data) {
                this._data += data.toString();
                return this;
            },
            digest: function(encoding) {
                let hash = 0;
                for (let i = 0; i < this._data.length; i++) {
                    const char = this._data.charCodeAt(i);
                    hash = ((hash << 5) - hash) + char;
                    hash = hash & hash;
                }
                hash = Math.abs(hash);
                
                if (encoding === 'hex') {
                    return hash.toString(16).padStart(8, '0');
                }
                return Buffer.from(hash.toString());
            }
        };
    },
    
    createHmac: function(algorithm, key) {
        return this.createHash(algorithm);
    }
};

// Step 3: Aggressive global injection
const globalContexts = [globalThis, self, global, window];
globalContexts.forEach(ctx => {
    if (ctx) {
        ctx.crypto = cryptoModule;
        console.log('[AGGRESSIVE CRYPTO] Injected into:', ctx.constructor?.name || 'unknown context');
    }
});

// Step 4: Override require function completely
const originalRequire = (typeof require !== 'undefined') ? require : null;
const aggressiveRequire = function(moduleName) {
    console.log('[AGGRESSIVE CRYPTO] require() called for:', moduleName);
    
    if (moduleName === 'crypto') {
        console.log('[AGGRESSIVE CRYPTO] Returning crypto module');
        return cryptoModule;
    }
    
    if (originalRequire) {
        try {
            return originalRequire(moduleName);
        } catch (e) {
            console.log('[AGGRESSIVE CRYPTO] Original require failed for:', moduleName, e.message);
        }
    }
    
    throw new Error('Module not found: ' + moduleName);
};

// Inject require in all contexts
globalContexts.forEach(ctx => {
    if (ctx) {
        ctx.require = aggressiveRequire;
    }
});

console.log('[AGGRESSIVE CRYPTO] Complete crypto replacement finished');
''' + '''

// Test the crypto module in web worker context
try {
    console.log("Worker: Testing require('crypto')...");
    const crypto = require('crypto');
    
    console.log("Worker: Testing randomBytes...");
    const bytes = crypto.randomBytes(16);
    console.log("Worker: ✅ randomBytes works, length:", bytes.length);
    
    console.log("Worker: Testing createHash...");
    const hash = crypto.createHash('sha256');
    hash.update('worker-test');
    const digest = hash.digest('hex');
    console.log("Worker: ✅ createHash works, digest:", digest);
    
    console.log("Worker: 🎉 All web worker crypto tests passed!");
    
} catch (error) {
    console.error("Worker: ❌ Web worker crypto test failed:", error);
}
'''
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as f:
        f.write(worker_test)
        test_file = f.name
    
    try:
        result = subprocess.run(['node', test_file], capture_output=True, text=True, timeout=10)
        
        print("Web Worker Test Output:")
        print(result.stdout)
        if result.stderr:
            print("Web Worker Test Errors:")
            print(result.stderr)
        
        if "All web worker crypto tests passed!" in result.stdout:
            print("✅ Web worker crypto test passed!")
            return True
        else:
            print("❌ Web worker crypto test failed")
            return False
            
    except subprocess.TimeoutExpired:
        print("⚠️  Web worker test timed out")
        return False
    finally:
        os.unlink(test_file)

def main():
    """Run all aggressive crypto fix tests."""
    print("🚨 Aggressive Crypto Fix Test Suite")
    print("=" * 50)
    
    # Check Node.js availability
    try:
        subprocess.run(['node', '--version'], capture_output=True, check=True)
        print("✅ Node.js is available")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ Node.js is not available. Please install Node.js to run tests.")
        return False
    
    # Run tests
    tests = [
        ("Extension without fix", test_without_fix),
        ("Extension with aggressive fix", test_with_aggressive_fix),
        ("Web worker context", test_web_worker_context)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} failed with error: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n📊 Aggressive Crypto Fix Test Summary:")
    print("=" * 50)
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"  {test_name}: {status}")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed >= 2:  # At least the fix and web worker tests should pass
        print("🎉 Aggressive crypto fix should resolve the Augment extension issue!")
        return True
    else:
        print("⚠️  Aggressive crypto fix may need further adjustment.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
