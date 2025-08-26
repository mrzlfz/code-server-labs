# VSCode Server Authentication Guide

## 🔐 What You're Seeing

When you start VSCode Server, you'll see output like this:
```
📝 [2025-08-26 03:36:49] info Using GitHub for authentication, run `code tunnel user login --provider <provider>` option to change this.
```

This means VSCode Server is starting the authentication process.

## 🎯 What to Expect Next

### Step 1: Authentication URL
Look for output containing an authentication URL:
```
📝 To grant access to the server, please log into https://github.com/login/device
📝 and use code: XXXX-XXXX
```

### Step 2: Device Code
You'll get a device code that looks like:
```
📝 User code: XXXX-XXXX
```

### Step 3: Browser Authentication
1. **Open the URL** in your browser (e.g., https://github.com/login/device)
2. **Enter the device code** when prompted
3. **Sign in** with your GitHub/Microsoft account
4. **Authorize** VSCode Server access

### Step 4: Tunnel Creation
After successful authentication:
```
📝 Open this link in your browser https://vscode.dev/tunnel/your-tunnel-name
✅ Tunnel established successfully!
```

## 🚀 How to Use the Fixed Version

### Current Status
The script now:
- ✅ **Monitors output continuously** for authentication URLs
- ✅ **Detects authentication prompts** automatically
- ✅ **Provides clear feedback** about what's happening
- ✅ **Extended monitoring** for up to 2 minutes
- ✅ **Better URL detection** for GitHub/Microsoft authentication

### What You Should Do

1. **Start VSCode Server** and choose your authentication method
2. **Watch the output** for authentication URLs
3. **Look for lines containing**:
   - `github.com/login/device`
   - `microsoft.com/devicelogin`
   - `User code:` or `device code:`
4. **Open the URL** in your browser
5. **Complete authentication** with your account
6. **Wait for tunnel URL** to appear

## 🔍 Monitoring Progress

Use the **"Check Server Output"** menu option (option 6) to:
- See real-time output from VSCode Server
- Check for authentication URLs you might have missed
- Monitor tunnel creation progress

## 💡 Pro Tips

### If You Don't See Authentication URL
1. **Wait longer** - authentication can take 1-2 minutes
2. **Use "Check Server Output"** to see recent messages
3. **Look carefully** - URLs might be in the middle of other text
4. **Check for device codes** - they're usually near the URLs

### Common Authentication URLs
- **GitHub**: `https://github.com/login/device`
- **Microsoft**: `https://microsoft.com/devicelogin`
- **VSCode**: `https://login.microsoftonline.com/...`

### If Authentication Fails
1. **Restart the process** (menu option 4)
2. **Try different authentication method** (switch between Microsoft/GitHub)
3. **Check internet connection**
4. **Clear browser cookies** for the authentication site

## 🎉 Success Indicators

You'll know it's working when you see:
```
📝 ✓ Tunnel successfully created
📝 Open this link in your browser https://vscode.dev/tunnel/colab-xxxxx
✅ Tunnel established successfully!
🌐 Access URL: https://vscode.dev/tunnel/colab-xxxxx
```

## 🔧 Manual Authentication (If Needed)

If the automatic process doesn't work, you can authenticate manually:

```bash
# Navigate to VSCode CLI
cd ~/.local/bin

# Login with specific provider
./code tunnel user login --provider github
# or
./code tunnel user login --provider microsoft

# Then create tunnel
./code tunnel --name my-tunnel
```

## 📞 Still Having Issues?

1. **Check the logs** (menu option 10)
2. **Use "Check Server Output"** (menu option 6)
3. **Try restarting** (menu option 4)
4. **Switch authentication method** (restart and choose different option)
5. **Use Code Server instead** (menu option 8) as fallback

The key is to **be patient** and **watch for authentication URLs** in the output!
