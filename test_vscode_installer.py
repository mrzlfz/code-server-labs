#!/usr/bin/env python3
"""
Test VSCode Server Installer
Script test untuk memverifikasi fungsi installer
"""

import os
import sys
import json
from pathlib import Path

def test_installer_import():
    """Test import installer module"""
    try:
        from vscode_server_installer import VSCodeServerInstaller
        print("✅ Import VSCodeServerInstaller: OK")
        return True
    except ImportError as e:
        print(f"❌ Import VSCodeServerInstaller: FAILED - {e}")
        return False

def test_installer_initialization():
    """Test installer initialization"""
    try:
        from vscode_server_installer import VSCodeServerInstaller
        installer = VSCodeServerInstaller()
        
        # Check directories created
        if installer.config_dir.exists():
            print("✅ Config directory created: OK")
        else:
            print("❌ Config directory: FAILED")
            return False
            
        if installer.install_dir.exists():
            print("✅ Install directory created: OK")
        else:
            print("❌ Install directory: FAILED")
            return False
            
        if installer.bin_dir.exists():
            print("✅ Bin directory created: OK")
        else:
            print("❌ Bin directory: FAILED")
            return False
        
        # Check config loading
        if isinstance(installer.config, dict):
            print("✅ Config loaded: OK")
        else:
            print("❌ Config loading: FAILED")
            return False
            
        return True
        
    except Exception as e:
        print(f"❌ Installer initialization: FAILED - {e}")
        return False

def test_config_management():
    """Test config save/load"""
    try:
        from vscode_server_installer import VSCodeServerInstaller
        installer = VSCodeServerInstaller()
        
        # Test config save
        original_config = installer.config.copy()
        installer.config["test_key"] = "test_value"
        installer.save_config()
        
        # Test config reload
        installer2 = VSCodeServerInstaller()
        if installer2.config.get("test_key") == "test_value":
            print("✅ Config save/load: OK")
            
            # Cleanup
            installer.config = original_config
            installer.save_config()
            return True
        else:
            print("❌ Config save/load: FAILED")
            return False
            
    except Exception as e:
        print(f"❌ Config management: FAILED - {e}")
        return False

def test_command_execution():
    """Test command execution method"""
    try:
        from vscode_server_installer import VSCodeServerInstaller
        installer = VSCodeServerInstaller()
        
        # Test simple command
        success, stdout, stderr = installer.run_command("echo 'test'", capture_output=True)
        
        if success and "test" in stdout:
            print("✅ Command execution: OK")
            return True
        else:
            print("❌ Command execution: FAILED")
            return False
            
    except Exception as e:
        print(f"❌ Command execution test: FAILED - {e}")
        return False

def test_extension_configuration():
    """Test extension configuration"""
    try:
        from vscode_server_installer import VSCodeServerInstaller
        installer = VSCodeServerInstaller()
        
        # Check default extensions
        extensions = installer.config.get("extensions", [])
        expected_extensions = [
            "ms-python.python",
            "ms-python.vscode-pylance",
            "ms-toolsai.jupyter"
        ]
        
        has_expected = all(ext in extensions for ext in expected_extensions)
        
        if has_expected:
            print("✅ Extension configuration: OK")
            return True
        else:
            print("❌ Extension configuration: FAILED")
            return False
            
    except Exception as e:
        print(f"❌ Extension configuration test: FAILED - {e}")
        return False

def show_system_info():
    """Show system information"""
    print("\n📋 System Information:")
    print("=" * 40)
    
    # Python version
    print(f"🐍 Python: {sys.version}")
    
    # OS info
    import platform
    print(f"💻 System: {platform.system()} {platform.release()}")
    print(f"🔧 Architecture: {platform.machine()}")
    
    # Home directory
    home = Path.home()
    print(f"🏠 Home: {home}")
    
    # Check if required packages available
    packages = ['requests', 'json', 'subprocess', 'pathlib']
    print(f"\n📦 Required Packages:")
    for pkg in packages:
        try:
            __import__(pkg)
            print(f"  ✅ {pkg}")
        except ImportError:
            print(f"  ❌ {pkg} - MISSING")

def main():
    """Run all tests"""
    print("🧪 VSCode Server Installer - Test Suite")
    print("=" * 50)
    
    tests = [
        ("Import Test", test_installer_import),
        ("Initialization Test", test_installer_initialization),
        ("Config Management Test", test_config_management),
        ("Command Execution Test", test_command_execution),
        ("Extension Configuration Test", test_extension_configuration)
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        print(f"\n🔍 Running {test_name}...")
        if test_func():
            passed += 1
        else:
            failed += 1
    
    print("\n" + "=" * 50)
    print("📊 TEST RESULTS:")
    print("=" * 50)
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print(f"📋 Total: {len(tests)}")
    
    if failed == 0:
        print("\n🎉 ALL TESTS PASSED! Installer siap digunakan.")
    else:
        print(f"\n⚠️  {failed} test(s) failed. Periksa error di atas.")
    
    # Show system info
    show_system_info()
    
    return failed == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)