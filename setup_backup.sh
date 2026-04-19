#!/bin/bash
mkdir -p /root/users_backup

# Take an immediate backup
cp /var/www/quanby-legal/backend/data/users.json /root/users_backup/users.$(date +%Y%m%d_%H).json
echo "Initial backup saved."

# Install cron job: backup every 6 hours, keep last 14 copies
CRON_JOB='0 */6 * * * cp /var/www/quanby-legal/backend/data/users.json /root/users_backup/users.$(date +\%Y\%m\%d_\%H).json && ls -t /root/users_backup/users.*.json | tail -n +15 | xargs rm -f 2>/dev/null'

# Remove old users backup crons and add fresh one
(crontab -l 2>/dev/null | grep -v 'users_backup'; echo "$CRON_JOB") | crontab -
echo "Cron installed:"
crontab -l | grep users_backup
