#!/data/data/com.termux/files/usr/bin/bash
pkg install -y cronie termux-services 2>/dev/null || true

PROJECT_DIR="$HOME/Naukri-automation"

# Install crontab using standard POSIX crontab command
echo "0 9 * * * cd $PROJECT_DIR && python daily_runner.py >> $PROJECT_DIR/daily_runs.log 2>&1" > "$HOME/naukri_cron_tmp"
crontab "$HOME/naukri_cron_tmp"
rm -f "$HOME/naukri_cron_tmp"

# Setup auto-start script for Termux:Boot
mkdir -p "$HOME/.termux/boot"
cat << 'EOF' > "$HOME/.termux/boot/start_naukri_cron.sh"
#!/data/data/com.termux/files/usr/bin/bash
termux-wake-lock
crond
EOF
chmod +x "$HOME/.termux/boot/start_naukri_cron.sh"

# Start background cron daemon
killall crond 2>/dev/null || true
crond
termux-wake-lock 2>/dev/null || true

echo ""
echo "=== CRONTAB VERIFICATION ==="
crontab -l
echo ""
echo "Cron daemon started successfully!"
