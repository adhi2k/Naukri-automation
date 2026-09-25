#!/data/data/com.termux/files/usr/bin/bash
# Ensure cronie package is installed
pkg install -y cronie termux-services 2>/dev/null || true

# Ensure spool directories exist
SPOOL_DIR="/data/data/com.termux/files/usr/var/spool/cron/crontabs"
mkdir -p "$SPOOL_DIR"

USER_NAME="$(whoami)"
PROJECT_DIR="/data/data/com.termux/files/home/Naukri-automation"

# Write the crontab entry for 09:00 AM daily
cat << EOF > "$SPOOL_DIR/$USER_NAME"
0 9 * * * cd $PROJECT_DIR && python daily_runner.py >> $PROJECT_DIR/daily_runs.log 2>&1
EOF

chmod 600 "$SPOOL_DIR/$USER_NAME"

# Start the crond daemon
killall crond 2>/dev/null || true
crond

# Enable wake lock so Android doesn't kill it in sleep
termux-wake-lock 2>/dev/null || true

echo "Active Crontab:"
crontab -l
echo ""
echo "Crond service started successfully!"
