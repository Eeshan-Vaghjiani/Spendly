# 📱 How to Open and Run the Flutter App in Android Studio

## Step 1: Open the Project in Android Studio

1. **Launch Android Studio**

2. **Open the Flutter project:**
   - Click **"Open"** (or File → Open)
   - Navigate to: `D:\ICS\YEAR 4\sem1\IS\model related\mobile`
   - Select the **`mobile`** folder
   - Click **"OK"**

3. **Wait for indexing:**
   - Android Studio will index the project (progress bar at bottom)
   - Wait for "Dart Analysis" to complete
   - This takes 1-2 minutes first time

---

## Step 2: Set Up Flutter SDK (If Needed)

If Android Studio says "Flutter SDK not found":

1. Go to **File → Settings** (or **Ctrl+Alt+S**)
2. Navigate to **Languages & Frameworks → Flutter**
3. Set Flutter SDK path (usually `C:\src\flutter` or where you installed Flutter)
4. Click **Apply** then **OK**

---

## Step 3: Configure API URL

The app needs to know where your backend is running.

### Option A: Using Run Configuration (Recommended)

1. Click the **dropdown next to Run button** (top-right)
2. Click **"Edit Configurations..."**
3. Under **"Additional run args"**, add:
   ```
   --dart-define=API_BASE_URL=http://10.0.2.2:5000/api/v1
   ```
4. Click **Apply** then **OK**

### Option B: Using Terminal (Alternative)

Open terminal in Android Studio (Alt+F12) and run:
```bash
flutter run --dart-define=API_BASE_URL=http://10.0.2.2:5000/api/v1
```

---

## Step 4: Start an Emulator or Connect Device

### Option A: Android Emulator (Easiest)

1. Click **Device Manager** icon (phone icon in toolbar)
2. If no emulator exists:
   - Click **"Create Device"**
   - Select **Pixel 5** or any device
   - Select **Android 11 (API 30)** or higher
   - Click **Finish**
3. Click **▶️ Play button** next to your emulator to start it
4. Wait for emulator to boot (1-2 minutes first time)

### Option B: Physical Android Phone

1. **Enable Developer Mode on phone:**
   - Go to Settings → About Phone
   - Tap "Build Number" 7 times
   - Go back to Settings → System → Developer Options
   - Enable **USB Debugging**

2. **Connect phone via USB cable**

3. **Allow USB debugging** when prompted on phone

4. Phone should appear in Android Studio device dropdown

---

## Step 5: Run the App

1. **Make sure your backend is running:**
   - Check: http://localhost:5000/api/v1/health should work

2. **Click the green ▶️ Run button** in Android Studio
   - Or press **Shift+F10**

3. **Wait for app to build and install** (2-3 minutes first time)

4. **App will launch on your device/emulator!**

---

## 📱 Using the App

### Login Screen:
- **Email:** `demo@example.com`
- **Password:** `LocalDemoPassword123!`

### What You Can Do:
- ✅ View transactions
- ✅ Add new transactions
- ✅ See spending forecast (7-day prediction using LSTM)
- ✅ View anomaly alerts (detected by Isolation Forest)
- ✅ Check budget recommendations

---

## 🐛 Troubleshooting

### Problem: "Flutter SDK not found"
**Solution:**
1. Open terminal and run: `flutter doctor`
2. Follow instructions to complete setup
3. In Android Studio: File → Settings → Languages & Frameworks → Flutter
4. Set Flutter SDK path

### Problem: "Dart Analysis failed"
**Solution:**
1. In terminal: `cd mobile`
2. Run: `flutter pub get`
3. Wait for packages to download
4. Restart Android Studio

### Problem: App can't connect to backend
**Check the API URL based on your setup:**

| Setup | API_BASE_URL |
|-------|--------------|
| **Android Emulator** | `http://10.0.2.2:5000/api/v1` ✅ |
| **iOS Simulator** | `http://127.0.0.1:5000/api/v1` |
| **Physical Phone (same WiFi)** | `http://192.168.x.x:5000/api/v1` |

To find your computer's IP:
```powershell
ipconfig
# Look for "IPv4 Address" under your WiFi adapter
```

### Problem: "Connection refused" or "Network error"
**Solutions:**
1. **Check backend is running:**
   - Open browser: http://localhost:5000/api/v1/health
   - Should show: `{"status": "healthy"}`
   - If not, run: `docker compose up -d`

2. **Check Windows Firewall:**
   - Windows might be blocking port 5000
   - Allow Python through firewall

3. **For Physical Device:**
   - Make sure phone and computer are on same WiFi
   - Use computer's IP instead of localhost

### Problem: Build errors in Android Studio
**Solution:**
```bash
# Open terminal in Android Studio
cd mobile

# Clean build
flutter clean

# Get dependencies
flutter pub get

# Try again
flutter run --dart-define=API_BASE_URL=http://10.0.2.2:5000/api/v1
```

---

## 🎯 Quick Start Checklist

- [ ] Backend is running (check http://localhost:5000/api/v1/health)
- [ ] Android Studio is open
- [ ] Opened `mobile` folder in Android Studio
- [ ] Flutter SDK is configured
- [ ] Emulator is running OR phone is connected
- [ ] Added `--dart-define=API_BASE_URL=http://10.0.2.2:5000/api/v1` to run config
- [ ] Clicked Run button (▶️)
- [ ] App installed on device
- [ ] Login with: demo@example.com / LocalDemoPassword123!

---

## 📸 What the App Looks Like

The app should have:
- 🔐 **Login Screen** - Enter demo credentials
- 💰 **Transactions List** - See all your transactions
- ➕ **Add Transaction** - Create new expense/income
- 📊 **Dashboard** - View spending analytics
- 🔮 **Forecast** - 7-day spending prediction (LSTM model)
- ⚠️ **Anomalies** - Unusual transactions detected (Isolation Forest)
- 💡 **Recommendations** - Budget advice and tips

---

## 🔧 Alternative: Run from Command Line

If Android Studio is giving trouble, you can run directly from terminal:

```bash
# Navigate to mobile folder
cd "D:\ICS\YEAR 4\sem1\IS\model related\mobile"

# Get dependencies
flutter pub get

# List available devices
flutter devices

# Run on specific device
flutter run -d <device-id> --dart-define=API_BASE_URL=http://10.0.2.2:5000/api/v1

# Or just run (will prompt to select device)
flutter run --dart-define=API_BASE_URL=http://10.0.2.2:5000/api/v1
```

---

## ✅ Success Indicators

You'll know it's working when:
1. ✅ App builds without errors
2. ✅ App launches on emulator/phone
3. ✅ Login screen appears
4. ✅ Can login with demo credentials
5. ✅ Can see dashboard with data
6. ✅ Can add transactions
7. ✅ Can view forecast predictions

---

## 📞 Need Help?

If stuck:
1. Check `APP_STATUS.md` - Make sure backend is healthy
2. Run `flutter doctor` - Check Flutter setup
3. Check Android Studio logs (bottom panel)
4. Try cleaning: `flutter clean && flutter pub get`

**Your personal finance app should now be running on your Android device!** 📱💰
