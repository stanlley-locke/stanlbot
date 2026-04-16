#!/usr/bin/env bash
set -e

echo "Deploying StanlBot to EC2..."
sudo apt update && sudo apt install -y python3.11 python3.11-venv git htop jq

# Setup application directory
APP_DIR="/opt/stanlbot"
mkdir -p "$APP_DIR" "$APP_DIR/storage/backups" "$APP_DIR/logs" "$APP_DIR/data/translations" "$APP_DIR/data/trivia"

# Create virtual environment
cd "$APP_DIR"
python3.11 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Permissions
sudo chown -R $(whoami):$(whoami) "$APP_DIR"
chmod 700 storage
chmod +x scripts/*.sh

# Install systemd service
sudo cp systemd/stanlbot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable stanlbot
sudo systemctl restart stanlbot

echo "Deployment complete."
echo "Check status: sudo systemctl status stanlbot"
echo "View logs: sudo journalctl -u stanlbot -f --no-pager"