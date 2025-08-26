# VSCode Server Troubleshooting Guide

## 🚨 Common Issue: Stuck at Authentication Choice

### Problem
VSCode Server gets stuck at the authentication method selection:
```
📝 * Visual Studio Code Server
📝 * License terms...
📝 ? How would you like to log in to Visual Studio Code? ›
📝 ❯ Microsoft Account
📝   GitHub Account
```

### Why This Happens
VSCode Server requires you to choose between Microsoft Account or GitHub Account for authentication, but the interactive prompt needs user input.

## ✅ **SOLUTION IMPLEMENTED!**

The script now **automatically handles** the authentication choice prompt!

### 🚀 How It Works Now

#### Step 1: Choose Authentication Method
When you start VSCode Server, you'll be prompted:
```
🔐 Authentication Method Selection:
1. Microsoft Account
2. GitHub Account
👉 Choose authentication method (1 or 2):
```

#### Step 2: Automatic Prompt Handling
- Script detects the VSCode authentication choice prompt
- Automatically sends your selection to the process
- No more getting stuck at the selection screen!

#### Step 3: Complete Browser Authentication
Watch for output like:
```
📝 To grant access to the server, please log into https://github.com/login/device
📝 and use code: XXXX-XXXX
```

#### Step 4: Complete Authentication
1. Open the provided URL in your browser
2. Enter the device code if prompted
3. Sign in with your chosen account (Microsoft/GitHub)
4. Grant permissions to VSCode Server

#### Step 5: Get Your Tunnel URL
```
📝 Open this link in your browser https://vscode.dev/tunnel/your-tunnel-name
✅ Tunnel established successfully!
```

### 🔧 Improved Startup Process

The updated VSCode Server startup now:
- ✅ Shows real-time output
- ✅ Detects authentication URLs
- ✅ Provides better user guidance
- ✅ Continues running in background
- ✅ Allows checking progress

### 📋 What to Expect

1. **License Display** (10-15 seconds)
   ```
   📝 * Visual Studio Code Server
   📝 * License terms...
   ```

2. **Authentication Prompt** (appears after license)
   ```
   📝 To grant access to the server, please log into...
   📝 https://github.com/login/device
   📝 and use code: XXXX-XXXX
   ```

3. **Tunnel Creation** (after authentication)
   ```
   📝 Open this link in your browser https://vscode.dev/tunnel/your-tunnel-name
   ```

### 🎯 Success Indicators

You'll know it's working when you see:
- ✅ Authentication URL appears
- ✅ Device code is provided
- ✅ Tunnel URL is generated
- ✅ "Open this link in your browser" message

### 🔍 Debugging Commands

If you need to debug manually:

```bash
# Check if process is running
ps aux | grep "code.*tunnel"

# Check process output (if you have the PID)
tail -f /proc/PID/fd/1

# Kill stuck process
pkill -f "code.*tunnel"
```

### 🆘 If Still Stuck

1. **Stop the process**:
   ```bash
   # Use menu option 3: Stop VSCode Server
   ```

2. **Check your internet connection**

3. **Try again**:
   ```bash
   # Use menu option 2: Start VSCode Server
   ```

4. **Use alternative**:
   ```bash
   # Switch back to Code Server if needed
   # Menu option 8: Switch to Code Server
   ```

### 💡 Pro Tips

1. **Keep the terminal open** - Don't close it during authentication
2. **Use a modern browser** - Chrome, Firefox, Edge work best
3. **Check popup blockers** - Authentication might open new tabs
4. **Be patient** - First-time setup takes longer
5. **Use the status checker** - Menu option 6 shows progress

### 🔄 Alternative: Manual Tunnel Creation

If the automated process fails, you can create tunnels manually:

```bash
# Navigate to VSCode CLI location
cd ~/.local/bin

# Create tunnel manually
./code tunnel --name my-tunnel --accept-server-license-terms

# Follow the authentication prompts
```

### 📞 Getting Help

If you're still having issues:
1. Check the logs (Menu option 10)
2. Try the "Check Server Output" option (Menu option 6)
3. Restart the process (Menu option 4)
4. Switch to Code Server as fallback (Menu option 8)
