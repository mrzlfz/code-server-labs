#!/usr/bin/env python3
"""
Test Node.js environment setup for crypto compatibility
"""

import subprocess
import sys
import os
from pathlib import Path

def test_node_environment():
    """Test Node.js environment with crypto polyfill."""
    print("🧪 Testing Node.js Environment Setup")
    print("=" * 40)
    
    # Path to the polyfill
    polyfill_file = Path.home() / ".local" / "share" / "code-server" / "polyfills" / "crypto-polyfill.js"
    
    if not polyfill_file.exists():
        print("❌ Crypto polyfill file not found!")
        return False
    
    print(f"✅ Crypto polyfill found: {polyfill_file}")
    
    # Set up environment similar to what code-server would use
    env = os.environ.copy()
    
    # Node.js options (without the problematic --loader)
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
    
    print(f"🔧 NODE_OPTIONS: {env['NODE_OPTIONS']}")
    
    # Test script that simulates extension loading
    test_script = '''
    console.log('[Test] Starting Node.js environment test...');
    
    // Test crypto module availability
    try {
        const crypto = require('crypto');
        console.log('[Test] ✅ Crypto module loaded successfully');
        
        // Test basic crypto functions
        const randomBytes = crypto.randomBytes(16);
        console.log('[Test] ✅ randomBytes works:', randomBytes.length, 'bytes');
        
        const hash = crypto.createHash('sha256');
        hash.update('test');
        const digest = hash.digest('hex');
        console.log('[Test] ✅ createHash works:', digest.substring(0, 16) + '...');
        
        console.log('[Test] 🎉 All crypto functions working!');
        
    } catch (error) {
        console.error('[Test] ❌ Crypto test failed:', error.message);
        process.exit(1);
    }
    
    console.log('[Test] ✅ Node.js environment test completed successfully');
    '''
    
    try:
        # Run the test with the configured environment
        result = subprocess.run(
            ['node', '-e', test_script],
            env=env,
            capture_output=True,
            text=True,
            timeout=15
        )
        
        if result.returncode == 0:
            print("\n📊 Environment Test Results:")
            print(result.stdout)
            return True
        else:
            print("\n❌ Environment Test Failed:")
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ Test timed out")
        return False
    except FileNotFoundError:
        print("❌ Node.js not found. Please install Node.js.")
        return False
    except Exception as e:
        print(f"❌ Test error: {e}")
        return False

if __name__ == "__main__":
    print("🔧 Node.js Environment Test")
    print("=" * 50)
    
    success = test_node_environment()
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 Node.js environment is configured correctly!")
        print("💡 Code Server should now start without ES module errors.")
    else:
        print("⚠️  Node.js environment needs attention.")
        print("💡 Check the error messages above for details.")
