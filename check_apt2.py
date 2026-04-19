import json

with open('/var/www/quanby-legal/backend/data/appointments.json') as f:
    apts = json.load(f)

apt_id = '8dde6dae-7dfc-4cae-81c8-072d3f064b22'
apt = apts.get(apt_id, {})
print('status:', apt.get('status'))
print('session_status:', apt.get('session_status'))
print('session_room_name:', apt.get('session_room_name'))
print('room_name key:', apt.get('room_name', 'NOT SET'))

# Also check what /api/sessions/apt_id returns
import urllib.request
req = urllib.request.Request(
    f'http://127.0.0.1:8080/api/sessions/{apt_id}',
    headers={'Authorization': 'Bearer FAKE'}
)
try:
    with urllib.request.urlopen(req, timeout=5) as r:
        d = json.loads(r.read().decode())
        print('API room_name:', d.get('room_name'))
        print('API session_status:', d.get('session_status'))
except Exception as e:
    print('API call (expected 401):', str(e)[:80])
