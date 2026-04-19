import urllib.request, json, os, sys
sys.path.insert(0, '/var/www/quanby-legal/backend')

os.chdir('/var/www/quanby-legal/backend')
# Read env manually
env = {}
with open('/var/www/quanby-legal/backend/.env') as f:
    for line in f:
        line = line.strip()
        if '=' in line and not line.startswith('#'):
            k, v = line.split('=', 1)
            env[k] = v.strip('"\'')

DC_BASE   = env.get('DOCONCHAIN_API_URL', 'https://stg-api2.doconchain.com')
DC_KEY    = env.get('DOCONCHAIN_CLIENT_KEY', '')
DC_SECRET = env.get('DOCONCHAIN_CLIENT_SECRET', '')
ENP_EMAIL = 'christianmontesor@gmail.com'

# Get ENP token
boundary = 'QLcheck'
body = (
    '--'+boundary+'\r\nContent-Disposition: form-data; name="client_key"\r\n\r\n'+DC_KEY+'\r\n'
    '--'+boundary+'\r\nContent-Disposition: form-data; name="client_secret"\r\n\r\n'+DC_SECRET+'\r\n'
    '--'+boundary+'\r\nContent-Disposition: form-data; name="email"\r\n\r\n'+ENP_EMAIL+'\r\n'
    '--'+boundary+'--\r\n'
).encode()

req = urllib.request.Request(DC_BASE+'/api/v2/generate/token', data=body,
    headers={'Content-Type': 'multipart/form-data; boundary='+boundary}, method='POST')
with urllib.request.urlopen(req, timeout=15) as r:
    tok_data = json.loads(r.read().decode())
token = (tok_data.get('data') or {}).get('token') or ''
print('Token OK, len:', len(token))

for doc_uuid in ['SX1a2H4itgDv', 'j4uI2TuhpXnD', 'mVyeffl7stUS', 'N5rwOsX2TSHu', 'gPamTomPmkff']:
    url = DC_BASE+'/api/v2/projects/'+doc_uuid+'?user_type=ENTERPRISE_API'
    req2 = urllib.request.Request(url, headers={'Authorization': 'Bearer '+token, 'Accept': 'application/json'}, method='GET')
    try:
        with urllib.request.urlopen(req2, timeout=15) as r2:
            proj = json.loads(r2.read().decode())
        msg = proj.get('message', proj)
        if isinstance(msg, str):
            msg = proj.get('data', {})
        status = msg.get('status', '?') if isinstance(msg, dict) else '?'
        signers = msg.get('signers', []) if isinstance(msg, dict) else []
        print(f'\n{doc_uuid}: status={status} signers={len(signers)}')
        for s in signers:
            print(f'  {s.get("email","?")} -> {s.get("status","?")}')
    except Exception as e:
        err_body = ''
        try: err_body = e.read().decode()[:80]
        except: pass
        print(f'\n{doc_uuid}: ERROR {e} {err_body}')
