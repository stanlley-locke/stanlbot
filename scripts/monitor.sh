#!/usr/bin/env bash
echo "StanlBot System Monitor"
echo "========================"
echo "CPU Load: $(top -bn1 | grep "Cpu(s)" | awk '{print $2"%"}')"
echo "RAM Usage: $(free -h | awk '/^Mem:/{print $3"/"$2 " ("$3%$2")"}')"
echo "Swap Usage: $(free -h | awk '/^Swap:/{print $3"/"$2}')"
echo "DB Size: $(du -sh storage/bot.db 2>/dev/null || echo "0B")"
echo "Log Size: $(du -sh logs/ 2>/dev/null || echo "0B")"
echo "========================"
systemctl status stanlbot --no-pager
echo "Recent Errors (last 5):"
journalctl -u stanlbot --priority=err --since "1 hour ago" --no-pager | tail -n 5