# 🔧 **PASSWORD ARGUMENT FIX - CODE SERVER START ISSUE**

## 🚨 **MASALAH YANG DITEMUKAN**

Dari output user:
```
Error: [2025-08-25T15:34:09.426Z] error --password can only be set in the config file or passed in via $PASSWORD
```

### **Root Cause Analysis:**
1. **Invalid Command Line Arguments**: Code Server tidak menerima `--password` sebagai command line argument
2. **Wrong Startup Method**: Method `_force_restart_with_env()` menggunakan command line arguments yang tidak valid
3. **Environment Variable Required**: Code Server memerlukan `$PASSWORD` environment variable, bukan `--password` argument

### **Command yang Gagal:**
```bash
/root/.local/bin/code-server --bind-addr 0.0.0.0:8888 --auth password --password colab123 --disable-telemetry /content
```

## ✅ **FIX YANG DIIMPLEMENTASIKAN**

### **🔧 BEFORE (Broken):**
```python
def _force_restart_with_env(self):
    # Prepare environment with EXTENSIONS_GALLERY
    env = os.environ.copy()
    env['EXTENSIONS_GALLERY'] = extensions_gallery
    
    # ❌ Invalid command line arguments
    cmd = [
        str(BIN_DIR / "code-server"),
        "--bind-addr", f"0.0.0.0:{port}",
        "--auth", "password",
        "--password", password,  # ❌ Not allowed
        "--disable-telemetry",
        "/content"
    ]
    
    process = subprocess.Popen(cmd, env=env, ...)
```

### **🔧 AFTER (Fixed):**
```python
def _force_restart_with_env(self):
    # Clear terminal to avoid control character issues
    self._clear_terminal()
    
    # Prepare environment with EXTENSIONS_GALLERY and PASSWORD
    env = os.environ.copy()
    env['EXTENSIONS_GALLERY'] = extensions_gallery
    env['PASSWORD'] = password  # ✅ Use environment variable
    
    # ✅ Use same approach as regular start_code_server
    code_server_bin = BIN_DIR / "code-server"
    
    process = subprocess.Popen(
        [str(code_server_bin)],  # ✅ No command line arguments
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True
    )
```

## 🚀 **CARA MENGGUNAKAN FIX**

### **🔥 IMMEDIATE SOLUTION:**

#### **Step 1: Reconfigure Microsoft Marketplace**
```bash
python code_server_colab_setup.py
# → 8. 🏪 Extension Registry
# → 2. Microsoft Visual Studio Marketplace
# → Ketika ditanya "Force restart Code Server now? (y/N)": ketik 'y'
```

#### **Step 2: Verify No More Password Errors**
Output seharusnya menunjukkan:
```
🔄 Force Restart with Environment Variables
🏪 Target registry: Microsoft Marketplace
📋 Environment variable: {"serviceUrl": "https://marketplace.visualstudio.com/_apis/public/gallery"...
▶️  Starting Code Server with current environment...
🚀 Starting Code Server with Microsoft Marketplace environment...
✅ Code Server restarted successfully!
✅ Microsoft Marketplace is active in Code Server process!
```

#### **Step 3: Test Extension Discovery**
1. 🌐 Open Code Server in browser
2. 🔍 Go to Extensions tab (Ctrl+Shift+X)
3. 🔎 Search "augment.vscode-augment"
4. ✅ Extension should now appear!

### **🔄 Alternative Method (If Still Fails):**

#### **Manual Environment Setup:**
```bash
# Set environment variables manually
export EXTENSIONS_GALLERY='{"serviceUrl":"https://marketplace.visualstudio.com/_apis/public/gallery","itemUrl":"https://marketplace.visualstudio.com/items","resourceUrlTemplate":"https://marketplace.visualstudio.com/_apis/public/gallery/publishers/{publisher}/vsextensions/{name}/{version}/vspackage"}'
export PASSWORD="colab123"

# Stop Code Server
python code_server_colab_setup.py → 3. Stop Code Server

# Start Code Server (will inherit environment variables)
python code_server_colab_setup.py → 2. Start Code Server
```

## 🔍 **TECHNICAL DETAILS**

### **Why Command Line Arguments Failed:**
- Code Server versi terbaru menggunakan security policy yang ketat
- Password tidak boleh di-pass via command line untuk security reasons
- Harus menggunakan environment variable `$PASSWORD` atau config file

### **Environment Variable Approach:**
```python
# ✅ Correct way to set password
env = os.environ.copy()
env['PASSWORD'] = password
env['EXTENSIONS_GALLERY'] = extensions_gallery

# ✅ Start without command line arguments
subprocess.Popen([str(code_server_bin)], env=env, ...)
```

### **Config File Alternative:**
Code Server juga bisa menggunakan config file:
```yaml
# ~/.config/code-server/config.yaml
bind-addr: 0.0.0.0:8080
auth: password
password: colab123
cert: false
```

## 🎯 **EXPECTED RESULTS**

### **Before Fix:**
```
❌ Error: --password can only be set in the config file or passed in via $PASSWORD
❌ Code Server fails to start
❌ Microsoft Marketplace not applied
❌ Terminal control characters causing confusion
```

### **After Fix:**
```
✅ Code Server starts successfully
✅ No password argument errors
✅ Microsoft Marketplace environment loaded
✅ Clean terminal output
✅ Extension discovery works
```

## 🚨 **TROUBLESHOOTING**

### **If Code Server Still Fails to Start:**

#### **1. Check Code Server Installation:**
```bash
ls -la ~/.local/bin/code-server
# Should show executable file
```

#### **2. Check Environment Variables:**
```bash
echo $EXTENSIONS_GALLERY
echo $PASSWORD
# Should show correct values
```

#### **3. Manual Start for Testing:**
```bash
export PASSWORD="colab123"
export EXTENSIONS_GALLERY='{"serviceUrl":"https://marketplace.visualstudio.com/_apis/public/gallery","itemUrl":"https://marketplace.visualstudio.com/items","resourceUrlTemplate":"https://marketplace.visualstudio.com/_apis/public/gallery/publishers/{publisher}/vsextensions/{name}/{version}/vspackage"}'
~/.local/bin/code-server
```

#### **4. Check Process Status:**
```bash
ps aux | grep code-server
# Should show running process
```

### **If Extensions Still Not Found:**

#### **1. Verify Environment in Process:**
```bash
python code_server_colab_setup.py → 8 → 4 (Debug Configuration)
# Look for: "✅ Microsoft Marketplace is active in Code Server process!"
```

#### **2. Clear Browser Cache:**
- Refresh Code Server page (Ctrl+F5)
- Clear browser cache and cookies
- Try incognito/private browsing mode

#### **3. Check Network Connectivity:**
```bash
curl -s "https://marketplace.visualstudio.com/_apis/public/gallery" | head -n 5
# Should return HTML/JSON response
```

## 💡 **KEY INSIGHTS**

### **Security Policy Change:**
- Code Server implemented stricter security policies
- Command line password arguments are now prohibited
- Environment variables are the preferred method

### **Process Environment Inheritance:**
- Environment variables must be set BEFORE process starts
- Running processes don't inherit new environment variables
- Force restart ensures new process gets updated environment

### **Configuration Consistency:**
- Use same startup method as regular `start_code_server()`
- Maintain consistency with existing codebase patterns
- Avoid custom command line arguments

---

**🎯 This fix resolves the password argument error and ensures Code Server starts correctly with Microsoft Marketplace environment variables!**
