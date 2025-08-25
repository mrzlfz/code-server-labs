#!/usr/bin/env python3
"""
Test script to verify pyngrok import fixes
"""

import sys
import subprocess
import os

def test_pyngrok_import():
    """Test pyngrok import functionality"""
    print("🧪 Testing pyngrok import fixes...")
    
    # Test 1: Import the main script
    print("\n1. Testing main script import...")
    try:
        sys.path.append('.')
        import code_server_colab_setup
        print("✅ Main script imported successfully")
    except Exception as e:
        print(f"❌ Failed to import main script: {e}")
        return False
    
    # Test 2: Test _import_pyngrok function
    print("\n2. Testing _import_pyngrok function...")
    try:
        result = code_server_colab_setup._import_pyngrok()
        print(f"✅ _import_pyngrok function works, result: {result}")
    except Exception as e:
        print(f"❌ _import_pyngrok function failed: {e}")
        return False
    
    # Test 3: Check global variables
    print("\n3. Checking global variables...")
    try:
        print(f"PYNGROK_AVAILABLE: {code_server_colab_setup.PYNGROK_AVAILABLE}")
        print(f"ngrok is None: {code_server_colab_setup.ngrok is None}")
        print(f"conf is None: {code_server_colab_setup.conf is None}")
        print("✅ Global variables accessible")
    except Exception as e:
        print(f"❌ Global variables check failed: {e}")
        return False
    
    # Test 4: Test CodeServerSetup initialization
    print("\n4. Testing CodeServerSetup initialization...")
    try:
        app = code_server_colab_setup.CodeServerSetup()
        print("✅ CodeServerSetup initialized successfully")
    except Exception as e:
        print(f"❌ CodeServerSetup initialization failed: {e}")
        return False
    
    # Test 5: Test setup_ngrok method (without actually setting up)
    print("\n5. Testing setup_ngrok method availability...")
    try:
        # Just check if method exists and is callable
        if hasattr(app, 'setup_ngrok') and callable(getattr(app, 'setup_ngrok')):
            print("✅ setup_ngrok method is available")
        else:
            print("❌ setup_ngrok method not found")
            return False
    except Exception as e:
        print(f"❌ setup_ngrok method check failed: {e}")
        return False
    
    # Test 6: Test _start_ngrok_tunnel method availability
    print("\n6. Testing _start_ngrok_tunnel method availability...")
    try:
        if hasattr(app, '_start_ngrok_tunnel') and callable(getattr(app, '_start_ngrok_tunnel')):
            print("✅ _start_ngrok_tunnel method is available")
        else:
            print("❌ _start_ngrok_tunnel method not found")
            return False
    except Exception as e:
        print(f"❌ _start_ngrok_tunnel method check failed: {e}")
        return False
    
    return True

def test_pyngrok_installation():
    """Test pyngrok installation process"""
    print("\n🔧 Testing pyngrok installation process...")
    
    try:
        # Try to install pyngrok
        result = subprocess.run([
            sys.executable, "-m", "pip", "install", "pyngrok", "--quiet"
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ pyngrok installation successful")
            
            # Test import after installation
            try:
                import code_server_colab_setup
                result = code_server_colab_setup._import_pyngrok()
                print(f"✅ Import after installation: {result}")
                
                if result:
                    print(f"✅ PYNGROK_AVAILABLE now: {code_server_colab_setup.PYNGROK_AVAILABLE}")
                    print(f"✅ ngrok available: {code_server_colab_setup.ngrok is not None}")
                    print(f"✅ conf available: {code_server_colab_setup.conf is not None}")
                
                return True
            except Exception as e:
                print(f"❌ Import test after installation failed: {e}")
                return False
        else:
            print(f"❌ pyngrok installation failed: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Installation test failed: {e}")
        return False

def test_error_handling():
    """Test error handling when pyngrok is not available"""
    print("\n🛡️ Testing error handling...")
    
    try:
        import code_server_colab_setup
        app = code_server_colab_setup.CodeServerSetup()
        
        # Test _start_ngrok_tunnel when pyngrok not available
        print("Testing _start_ngrok_tunnel with unavailable pyngrok...")
        
        # Temporarily set pyngrok as unavailable
        original_available = code_server_colab_setup.PYNGROK_AVAILABLE
        original_ngrok = code_server_colab_setup.ngrok
        original_conf = code_server_colab_setup.conf
        
        code_server_colab_setup.PYNGROK_AVAILABLE = False
        code_server_colab_setup.ngrok = None
        code_server_colab_setup.conf = None
        
        # This should handle the error gracefully
        app._start_ngrok_tunnel()
        print("✅ Error handling works correctly")
        
        # Restore original values
        code_server_colab_setup.PYNGROK_AVAILABLE = original_available
        code_server_colab_setup.ngrok = original_ngrok
        code_server_colab_setup.conf = original_conf
        
        return True
        
    except Exception as e:
        print(f"❌ Error handling test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 Starting pyngrok fix verification tests...")
    
    tests = [
        ("Import Tests", test_pyngrok_import),
        ("Installation Tests", test_pyngrok_installation),
        ("Error Handling Tests", test_error_handling)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n{'='*50}")
        print(f"Running {test_name}")
        print('='*50)
        
        try:
            result = test_func()
            results.append((test_name, result))
            
            if result:
                print(f"\n✅ {test_name} PASSED")
            else:
                print(f"\n❌ {test_name} FAILED")
                
        except Exception as e:
            print(f"\n💥 {test_name} CRASHED: {e}")
            results.append((test_name, False))
    
    # Summary
    print(f"\n{'='*50}")
    print("TEST SUMMARY")
    print('='*50)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name}: {status}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The pyngrok fix is working correctly.")
        return True
    else:
        print("⚠️ Some tests failed. Please check the output above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
