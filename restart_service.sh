#!/bin/bash
echo "Force killing all uvicorn processes..."
pkill -9 -f 'uvicorn main:app' 2>/dev/null
kill -9 $(pgrep -f 'uvicorn') 2>/dev/null
sleep 2
echo "Starting quanby-legal..."
systemctl start quanby-legal
sleep 4
systemctl is-active quanby-legal
echo "Health check:"
curl -s --max-time 5 http://127.0.0.1:8080/api/health
