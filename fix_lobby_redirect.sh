#!/bin/bash
set -e

# 1. Fix appointments.html - replace /lobby with /session
sed -i 's|/lobby?apt=|/session?apt=|g' /var/www/quanby-legal/appointments.html
echo "appointments.html: $(grep -c '/session?apt=' /var/www/quanby-legal/appointments.html) session refs, $(grep -c '/lobby' /var/www/quanby-legal/appointments.html) lobby refs remaining"

# 2. Fix nginx - update /lobby route to serve session.html
sed -i 's|try_files /lobby.html /index.html;|try_files /session.html /index.html;|' /etc/nginx/sites-enabled/quanby-legal
echo "nginx lobby route:"
grep -A2 'location = /lobby' /etc/nginx/sites-enabled/quanby-legal

# 3. Reload nginx
nginx -t && nginx -s reload && echo "nginx reloaded OK"
