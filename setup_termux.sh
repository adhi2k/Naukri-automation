#!/data/data/com.termux/files/usr/bin/bash
# ==============================================================================
#  NopeRi - 100% Automated Android Termux Setup Script
#  Configures daily background auto-apply with Zero Manual Effort
# ==============================================================================

set -e

echo ""
echo "================================================================="
echo "   🚀 NOPERI ANDROID TERMUX AUTOMATION INSTALLER"
echo "================================================================="
echo ""

# 1. Update Termux Package Repositories
echo "[1/6] Updating Termux packages..."
pkg update -y && pkg upgrade -y

# 2. Install Required System Packages
echo "[2/6] Installing Python, Git, and Cron scheduler..."
pkg install -y python git cronie termux-api termux-services

# 3. Prevent Android from killing Termux in background (Wake Lock)
echo "[3/6] Acquiring Termux WakeLock for background execution..."
termux-wake-lock

# 4. Install Python Dependencies
echo "[4/6] Installing Python packages..."
pip install --upgrade pip
pip install requests urllib3 python-dotenv pycryptodome colorama

# Try installing curl_cffi if wheel is available (optional)
pip install curl_cffi || echo "Standard requests fallback active (100% functional on Android)"

# 5. Setup Termux Boot Auto-Start Directory
echo "[5/6] Setting up Termux Boot auto-start..."
mkdir -p ~/.termux/boot
cat << 'EOF' > ~/.termux/boot/start_noperi_cron.sh
#!/data/data/com.termux/files/usr/bin/bash
termux-wake-lock
crond
EOF
chmod +x ~/.termux/boot/start_noperi_cron.sh

# 6. Configure Daily 09:00 AM Cron Schedule
echo "[6/6] Scheduling daily 09:00 AM automation..."
PROJECT_DIR="$(pwd)"
CRON_JOB="0 9 * * * cd $PROJECT_DIR && python daily_runner.py >> $PROJECT_DIR/daily_runs.log 2>&1"

# Write crontab
(crontab -l 2>/dev/null | grep -v "daily_runner.py" ; echo "$CRON_JOB") | crontab -

# Start Cron Daemon
crond 2>/dev/null || true

echo ""
echo "================================================================="
echo "  ✅ NOPERI MOBILE AUTOMATION IS READY & ACTIVE!"
echo "================================================================="
echo "  📅 Schedule:  Runs everyday at 09:00 AM silently in background"
echo "  ⚡ AI Engine: Groq Cloud LPU (0% phone CPU/battery)"
echo "  📱 Alerts:    Delivered directly to your phone via ntfy"
echo "  📝 Logs:      Saved to $PROJECT_DIR/daily_runs.log"
echo "================================================================="
echo ""
echo "To test run right now, run:"
echo "    python verify_system.py"
echo ""
