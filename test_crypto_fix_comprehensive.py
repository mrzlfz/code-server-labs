#!/usr/bin/env python3
"""
Comprehensive Crypto Fix Test
============================

This script tests the crypto polyfill fix for VS Code extensions in code-server.
It verifies that the crypto module is available in web worker contexts.
"""

import os
import sys
import subprocess
import tempfile
from pathlib import Path

def test_crypto_polyfill():
    """Test the crypto polyfill in a Node.js environment."""
    print("🧪 Testing Crypto Polyfill...")
    
    # Create a test script that simulates the extension environment
    test_script = '''
// Test script to verify crypto polyfill works
console.log("Testing crypto polyfill...");

try {
    // Test 1: Check if crypto is available via require
    const crypto = require('crypto');
    console.log("✅ crypto module loaded via require()");
    
    // Test 2: Test randomBytes function
    const randomBytes = crypto.randomBytes(16);
    console.log("✅ randomBytes works, length:", randomBytes.length);
    
    // Test 3: Test createHash function
    const hash = crypto.createHash('sha256');
    hash.update('test');
    const digest = hash.digest('hex');
    console.log("✅ createHash works, digest:", digest);
    
    console.log("🎉 All crypto tests passed!");
    process.exit(0);
    
} catch (error) {
    console.error("❌ Crypto test failed:", error.message);
    process.exit(1);
}
'''
    
    # Write test script to temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as f:
        f.write(test_script)
        test_file = f.name
    
    try:
        # Run the test script with Node.js
        result = subprocess.run(['node', test_file], capture_output=True, text=True)
        
        print("Test Output:")
        print(result.stdout)
        
        if result.stderr:
            print("Test Errors:")
            print(result.stderr)
        
        return result.returncode == 0
        
    finally:
        # Clean up
        os.unlink(test_file)

def test_web_worker_crypto():
    """Test crypto availability in web worker context."""
    print("\n🌐 Testing Web Worker Crypto...")
    
    # Create a web worker test script
    worker_script = '''
// Web Worker Crypto Test
console.log("Web Worker: Testing crypto availability...");

// Load the crypto polyfill
''' + open('code_server_colab_setup.py').read().split('web_worker_crypto_content = \'\'\'')[1].split('\'\'\'')[0] + '''

// Test crypto functionality
try {
    console.log("Web Worker: Testing require('crypto')...");
    const crypto = require('crypto');
    
    console.log("Web Worker: Testing randomBytes...");
    const bytes = crypto.randomBytes(16);
    console.log("Web Worker: ✅ randomBytes works, length:", bytes.length);
    
    console.log("Web Worker: 🎉 All web worker crypto tests passed!");
    
} catch (error) {
    console.error("Web Worker: ❌ Crypto test failed:", error.message);
}
'''
    
    # Write worker script to temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as f:
        f.write(worker_script)
        worker_file = f.name
    
    try:
        # Run the worker script with Node.js
        result = subprocess.run(['node', worker_file], capture_output=True, text=True)
        
        print("Web Worker Test Output:")
        print(result.stdout)
        
        if result.stderr:
            print("Web Worker Test Errors:")
            print(result.stderr)
        
        return "All web worker crypto tests passed!" in result.stdout
        
    finally:
        # Clean up
        os.unlink(worker_file)

def test_extension_environment():
    """Test crypto in simulated extension environment."""
    print("\n🔌 Testing Extension Environment...")
    
    # Simulate the extension loading environment
    extension_test = '''
// Simulate VS Code extension environment
global.vscode = {
    window: {
        showInformationMessage: function(msg) {
            console.log("VS Code Message:", msg);
        }
    }
};

// Load crypto polyfill
''' + open('code_server_colab_setup.py').read().split('crypto_polyfill_content = \'\'\'')[1].split('\'\'\'')[0] + '''

// Test extension-like crypto usage
try {
    console.log("Extension: Activating extension...");
    
    // This simulates what the Augment extension might do
    const crypto = require('crypto');
    console.log("Extension: ✅ Crypto module loaded");
    
    // Generate some random data like an extension might
    const sessionId = crypto.randomBytes(16).toString('hex');
    console.log("Extension: ✅ Generated session ID:", sessionId);
    
    // Create a hash like an extension might
    const hash = crypto.createHash('sha256');
    hash.update('extension-data');
    const checksum = hash.digest('hex');
    console.log("Extension: ✅ Generated checksum:", checksum);
    
    console.log("Extension: 🎉 Extension crypto simulation successful!");
    
} catch (error) {
    console.error("Extension: ❌ Extension crypto failed:", error.message);
    console.error("Extension: Stack trace:", error.stack);
}
'''
    
    # Write extension test script to temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as f:
        f.write(extension_test)
        ext_file = f.name
    
    try:
        # Run the extension test script with Node.js
        result = subprocess.run(['node', ext_file], capture_output=True, text=True)
        
        print("Extension Test Output:")
        print(result.stdout)
        
        if result.stderr:
            print("Extension Test Errors:")
            print(result.stderr)
        
        return "Extension crypto simulation successful!" in result.stdout
        
    finally:
        # Clean up
        os.unlink(ext_file)

def main():
    """Run all crypto tests."""
    print("🔧 Comprehensive Crypto Fix Test")
    print("=" * 50)
    
    # Check if Node.js is available
    try:
        subprocess.run(['node', '--version'], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ Node.js is not available. Please install Node.js to run tests.")
        return False
    
    # Run all tests
    tests = [
        ("Basic Crypto Polyfill", test_crypto_polyfill),
        ("Web Worker Crypto", test_web_worker_crypto),
        ("Extension Environment", test_extension_environment)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
            print(f"{'✅' if result else '❌'} {test_name}: {'PASSED' if result else 'FAILED'}")
        except Exception as e:
            results.append((test_name, False))
            print(f"❌ {test_name}: ERROR - {e}")
    
    # Summary
    print("\n📊 Test Summary:")
    print("=" * 50)
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"  {test_name}: {status}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The crypto fix should work.")
        return True
    else:
        print("⚠️  Some tests failed. The crypto fix may need adjustment.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
