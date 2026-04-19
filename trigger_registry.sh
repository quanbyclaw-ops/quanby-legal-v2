#!/bin/bash
# Get a valid cookie by logging in as christian
echo "=== Checking DC document status ==="
source /var/www/quanby-legal/venv/bin/activate

python3 << 'PYEOF'
import sys, json, urllib.request, urllib.error
sys.path.insert(0, '/var/www/quanby-legal/backend')

# Load env
from dotenv import load_dotenv
import os
load_dotenv('/var/www/quanby-legal/backend/.env')

DC_BASE = os.getenv('DOCONCHAIN_API_URL', 'https://stg-api2.doconchain.com')
DC_CLIENT_KEY = os.getenv('DOCONCHAIN_CLIENT_KEY', '')
DC_CLIENT_SECRET = os.getenv('DOCONCHAIN_CLIENT_SECRET', '')
DC_EMAIL = os.getenv('DOCONCHAIN_EMAIL', '')

enp_email = 'christianmontesor@gmail.com'
doc_uuid = 'gPamTomPmkffDwe'

print('DC_BASE:', DC_BASE)
print('Getting token for:', enp_email)

# Get token
boundary = 'QLcheck'
body = (
    f'--{boundary}\r\nContent-Disposition: form-data; name="client_key"\r\n\r\n{DC_CLIENT_KEY}\r\n'
    f'--{boundary}\r\nContent-Disposition: form-data; name="client_secret"\r\n\r\n{DC_CLIENT_SECRET}\r\n'
    f'--{boundary}\r\nContent-Disposition: form-data; name="email"\r\n\r\n{enp_email}\r\n'
    f'--{boundary}--\r\n'
).encode()

req = urllib.request.Request(f'{DC_BASE}/api/v2/generate/token', data=body,
    headers={'Content-Type': f'multipart/form-data; boundary={boundary}'}, method='POST')
with urllib.request.urlopen(req, timeout=15) as r:
    tok_data = json.loads(r.read().decode())
token = (tok_data.get('data') or {}).get('token') or tok_data.get('token', '')
print('Token:', token[:15], '...')

# Check doc status on DC
try:
    req2 = urllib.request.Request(
        f'{DC_BASE}/api/v2/projects/{doc_uuid}?user_type=ENTERPRISE_API',
        headers={'Authorization': f'Bearer {token}', 'Accept': 'application/json'},
        method='GET'
    )
    with urllib.request.urlopen(req2, timeout=15) as r2:
        proj = json.loads(r2.read().decode())
    data = proj.get('data') or proj
    print('Project status:', data.get('status', '?'))
    print('Completed at:', data.get('completed_at', 'not completed'))
    signers = data.get('signers', [])
    print('Signers:', len(signers))
    for s in signers:
        print(' ', s.get('email', '?'), '->', s.get('status', '?'))
except Exception as e:
    print('DC check error:', e)

PYEOF
