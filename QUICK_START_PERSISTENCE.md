# Quick Start: Persistence & Security

## What Was Implemented

### 🔄 Auto-Start on Boot
- After you login, CCTV Agent automatically registers itself with Windows
- Next time you restart your computer, CCTV Agent will start automatically
- Status message shows: `"✓ Auto-start enabled"`

### 🔒 Password-Protected Exit
- When you try to close the app (click X button), a password dialog appears
- You must enter your credentials to exit
- This prevents accidental or unauthorized termination

### 🖥️ Persistent Background Monitoring
- App runs in system tray when minimized
- Cloud streaming continues even if app is minimized
- Can restore from tray menu at any time

---

## How to Test

### Test 1: Login and Auto-Start Registration
```
1. Run: dist/CCTVAgent.exe
2. Login with your credentials
3. You should see: "✓ Auto-start enabled" in status bar
4. Close the app (will require password)
```

### Test 2: Verify Windows Startup
```
1. Restart your computer
2. After boot, CCTV Agent should start automatically
3. Check system tray for CCTV icon
```

### Test 3: Exit Authentication
```
1. Click the X button to close app
2. A dialog appears asking for password
3. Enter your password to confirm exit
4. App closes
```

### Test 4: Disable Auto-Start (Optional)
```
Settings > Advanced > Auto-start toggle
(Feature for future release)
```

---

## File Structure

```
cctv_agent/
├── core/
│   ├── startup_manager.py      ← NEW: Handles Windows registry
│   ├── config_manager.py       ← UPDATED: Stores username
│   └── ...
├── ui/
│   ├── exit_auth_dialog.py     ← NEW: Exit password dialog
│   ├── main_window.py          ← UPDATED: Integrates auth
│   └── ...
└── main_gui.py                 ← UPDATED: Trigger for build
```

---

## Technical Details

### Windows Registry Entry
- **Location**: `HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Run`
- **Entry Name**: `CCTVAgent`
- **Entry Value**: Full path to `dist/CCTVAgent.exe`
- **User Level**: Current user only (no admin required)

### Config File
- **Location**: `~/CCTVAgent/config.json`
- **New Field**: `user.username` - Stores logged-in username
- **Used For**: Display in exit auth dialog so user knows who's logged in

### Exit Dialog
- **Triggered**: When user clicks X button
- **Shows**: Logged-in username (read-only)
- **Asks**: Password to confirm exit
- **Purpose**: Prevent unauthorized termination

---

## Expected Behavior

### On Fresh Start
1. ✓ Login dialog appears
2. ✓ User enters credentials
3. ✓ "Auto-start enabled" message
4. ✓ Old instances killed
5. ✓ App runs normally

### On System Reboot
1. ✓ App starts automatically
2. ✓ No login needed (credentials cached)
3. ✓ Loads to main window or tray
4. ✓ Cloud streams resume

### On Exit Attempt
1. ✓ User clicks X button
2. ✓ Exit dialog appears with password field
3. ✓ User must enter password
4. ✓ If correct: App exits
5. ✓ If cancelled: App remains open

---

## Build Status

✅ **CCTVAgent.exe Updated** (April 18, 00:09:59)

All new features included:
- ✅ Auto-start registration
- ✅ Exit authentication dialog
- ✅ Username storage in config
- ✅ StartupManager module
- ✅ ExitAuthDialog UI

---

## Known Limitations

⚠️ **Password Verification**
- Exit dialog currently validates locally
- Should be enhanced to verify against backend in future
- Works as "require password to proceed" security measure

⚠️ **Admin Users**
- Users with admin/root access can still terminate via registry or task manager
- System is designed to prevent casual/unauthorized termination

---

## Next Steps

1. **Test the build** - Run dist/CCTVAgent.exe
2. **Verify login works** - Check credentials are saved
3. **Test exit protection** - Try to close app
4. **Reboot test** - Restart and verify auto-start
5. **Check registry** - Confirm Windows startup entry created

---

## Questions?

If exit dialog doesn't appear or auto-start doesn't work:
1. Check build timestamp: `dist/CCTVAgent.exe` should be from April 18, 00:09+
2. Check config: `~/CCTVAgent/config.json` should have username field
3. Check logs: `~/CCTVAgent/logs/app.log` for error messages
