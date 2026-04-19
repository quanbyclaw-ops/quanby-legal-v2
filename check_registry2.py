import json, subprocess

# Check users
with open('/var/www/quanby-legal/backend/data/users.json') as f:
    users = json.load(f)

print('=== Users ===')
for uid, u in users.items():
    print(u.get('email'), '| role:', u.get('role'), '| step:', u.get('onboarding_step'), '| cert:', u.get('certificate_status'))

# Check appointments
with open('/var/www/quanby-legal/backend/data/appointments.json') as f:
    apts = json.load(f)

print()
print('=== Appointments ===', len(apts), 'total')
for aid, a in apts.items():
    docs = a.get('session_documents', [])
    print(' ', aid[:12], '| session:', a.get('session_status'), '| docs:', len(docs), '| enp:', a.get('enp_id','?')[:12])

# Test the API directly
print()
print('=== Registry API test ===')
import urllib.request
try:
    req = urllib.request.Request('http://127.0.0.1:8080/api/registry/acts',
        headers={'Authorization': 'Bearer FAKE'})
    with urllib.request.urlopen(req, timeout=5) as r:
        print('Status:', r.status)
        print('Body:', r.read().decode()[:200])
except Exception as e:
    print('Error:', e)
