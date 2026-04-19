import sys, json, urllib.request, hmac, hashlib, base64, time
sys.path.insert(0, '/var/www/quanby-legal/backend')

from dotenv import load_dotenv
import os
load_dotenv('/var/www/quanby-legal/backend/.env')

DC_BASE   = os.getenv('DOCONCHAIN_API_URL', 'https://stg-api2.doconchain.com')
DC_KEY    = os.getenv('DOCONCHAIN_CLIENT_KEY', '')
DC_SECRET = os.getenv('DOCONCHAIN_CLIENT_SECRET', '')
DC_EMAIL  = os.getenv('DOCONCHAIN_EMAIL', '')

# Get token
boundary = 'QLcheck'
body = (
    f'--{boundary}\r\nContent-Disposition: form-data; name="client_key"\r\n\r\n{DC_KEY}\r\n'
    f'--{boundary}\r\nContent-Disposition: form-data; name="client_secret"\r\n\r\n{DC_SECRET}\r\n'
    f'--{boundary}\r\nContent-Disposition: form-data; name="email"\r\n\r\n{DC_EMAIL}\r\n'
    f'--{boundary}--\r\n'
).encode()

req = urllib.request.Request(f'{DC_BASE}/api/v2/generate/token', data=body,
    headers={'Content-Type': f'multipart/form-data; boundary={boundary}'}, method='POST')
with urllib.request.urlopen(req, timeout=15) as r:
    tok_data = json.loads(r.read().decode())
token = (tok_data.get('data') or {}).get('token') or tok_data.get('token', '')
print('Token:', token[:15], '...')

# Check the most recent doc (apt:97958aea - EJ GAN SECRETARY CERTIFICATE)
for doc_uuid in ['SX1a2H4itgDv', 'j4uI2TuhpXnD', 'mVyeffl7stUS']:
    try:
        req2 = urllib.request.Request(
            f'{DC_BASE}/api/v2/projects/{doc_uuid}?user_type=ENTERPRISE_API',
            headers={'Authorization': f'Bearer {token}', 'Accept': 'application/json'},
            method='GET'
        )
        with urllib.request.urlopen(req2, timeout=15) as r2:
            proj = json.loads(r2.read().decode())
        data = proj.get('data') or proj.get('message') or proj
        if isinstance(data, dict):
            print(f'\ndoc:{doc_uuid}')
            print('  status:', data.get('status', '?'))
            print('  signers:', len(data.get('signers', [])))
            for s in data.get('signers', []):
                print('   ', s.get('email','?'), '->', s.get('status','?'))
    except Exception as e:
        print(f'doc:{doc_uuid} error:', e)
