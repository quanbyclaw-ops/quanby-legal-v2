#!/bin/bash
# Verify and fix appointments.html session links
echo "lobby refs:"
grep -c '/lobby' /var/www/quanby-legal/appointments.html || echo 0

echo "session refs:"
grep -c '/session?apt=' /var/www/quanby-legal/appointments.html || echo 0

# Fix startVideoSession location.href if still using lobby
sed -i "s|/lobby?apt=' + encodeURIComponent(aptId)|/session?apt=' + encodeURIComponent(aptId)|g" /var/www/quanby-legal/appointments.html

echo "After fix - session refs:"
grep -c '/session?apt=' /var/www/quanby-legal/appointments.html || echo 0

# Also remove stale lobby.html if exists (nginx now serves session.html)
rm -f /var/www/quanby-legal/lobby.html
echo "lobby.html removed"

echo "nginx lobby route:"
grep -A2 'location = /lobby' /etc/nginx/sites-enabled/quanby-legal
