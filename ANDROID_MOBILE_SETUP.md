# 📱 100% Automated Android Setup Guide (Zero Manual Work)

Run Naukri Automation Agent completely in the background on your **Android Phone**!
- **0% Phone Battery / RAM** (All AI scoring happens in the cloud via Groq LPU).
- **Runs everyday at 09:00 AM automatically** using real mobile data/Wi-Fi.
- **Never gets IP blocked** by Naukri.
- **Instant mobile alerts** via `ntfy`.

---

## 🚀 Step 1: Install Termux & Termux:Boot on Android

> [!IMPORTANT]
> **Do NOT install Termux from Google Play Store** (the Play Store version is outdated).
> Install from **F-Droid** or official GitHub releases:

1. **Install Termux**: [Download Termux APK](https://f-droid.org/repo/com.termux_1020.apk) *(or from [F-Droid](https://f-droid.org/packages/com.termux/))*.
2. **Install Termux:Boot**: [Download Termux:Boot APK](https://f-droid.org/repo/com.termux.boot_7.apk) *(Enables silent auto-start whenever you restart your phone)*.

---

## ⚡ Step 2: Run the 1-Command Automated Installer

Open the **Termux** app on your phone, copy and paste this command, then press **Enter**:

```bash
pkg update -y && pkg install -y git && git clone https://github.com/adhi2k/Naukri-automation.git ~/Naukri-automation && cd ~/Naukri-automation && bash setup_termux.sh
```

---

## ⚙️ Step 3: Configure `.env` on Your Phone

Inside Termux, create or copy your `.env` file:

```bash
cd ~/Naukri-automation
nano .env
```

Paste your `.env` settings:
```env
USERNAME=YourNaukri_Email
PASSWORD=YourNaukri_Password

AUTO_APPLY=true
DAILY_APPLY_LIMIT=20
AI_SCORE_LIMIT=15

# --- CLOUD AI RESUME SCORER (GROQ LPU) ---
GROQ_API_KEY=gsk_your_groq_api_key_here
GROQ_MODEL=qwen/qwen3.8-27b

# --- GOOGLE SHEET WEBHOOK ---
GOOGLE_SHEET_WEBHOOK_URL=https://script.google.com/macros/s/YOUR_SCRIPT_ID/exec
GOOGLE_SHEET_TAB_NAME=Applied_Jobs
GOOGLE_SHEET_QUEUE_TAB=Job_Queue

# --- MOBILE NOTIFICATION ---
NTFY_TOPIC=noperi_your_unique_topic
```

*(Press `Ctrl + O` then `Enter` to save, and `Ctrl + X` to exit nano)*.

---

## 🔋 Step 4: Disable Battery Optimization (Crucial)

To ensure Android does not put Termux to sleep:
1. Go to your Phone's **Settings** > **Apps** > **Termux**.
2. Tap **Battery** > Select **"Unrestricted"** / **"Don't Optimize"**.
3. Open the **Termux:Boot** app once from your app drawer to register the boot permissions.

---

## ✅ Step 5: Verify Everything is Working

Test the diagnostic suite on your phone:
```bash
python verify_system.py
```

You should see:
```text
=================================================================
  SYSTEM DIAGNOSTIC SUMMARY
=================================================================
  Environment            : WORKING PERFECTLY
  AI Engine (Groq LPU)   : WORKING PERFECTLY (Latency: 0.15s)
  Naukri Auth            : WORKING PERFECTLY
  Profile Bump           : WORKING PERFECTLY
  Google Sheets          : WORKING PERFECTLY
  Mobile Alert           : WORKING PERFECTLY
=================================================================
```

---

## 🎉 You're All Done!
- **Every Morning at 09:00 AM**: Your phone will automatically run in the background, bump your profile timestamp, apply to matching jobs, log to your Google Sheet, and send you a notification.
- **No manual commands or laptop required!**
