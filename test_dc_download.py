import json, urllib.request, os

env = {}
with open('/var/www/quanby-legal/backend/.env') as f:
    for line in f:
        line = line.strip()
        if '=' in line and not line.startswith('#'):
            k, v = line.split('=', 1)
            env[k] = v.strip('"\'')

DC_BASE = env.get('DOCONCHAIN_API_URL', 'https://stg-api2.doconchain.com')
DC_APP  = env.get('DOCONCHAIN_APP_URL', 'https://stg-app.doconchain.com')
DC_KEY  = env.get('DOCONCHAIN_CLIENT_KEY', '')
DC_SECRET = env.get('DOCONCHAIN_CLIENT_SECRET', '')
ENP_EMAIL = 'christianmontesor@gmail.com'

# Get token
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
    token = (json.loads(r.read().decode()).get('data') or {}).get('token', '')
print('Token OK')

# Test various DC endpoints to find direct PDF download
vault_uuid = 'f6f97e89-710b-4105-ba5b-276373751d99'
project_uuid = 'Gs2t3qmFjMARP4p'

endpoints = [
    f'/vault/items/{vault_uuid}/download?user_type=ENTERPRISE_API',
    f'/vault/download/{vault_uuid}?user_type=ENTERPRISE_API',
    f'/api/v2/projects/{project_uuid}/download?user_type=ENTERPRISE_API',
    f'/api/v2/projects/{project_uuid}/files?user_type=ENTERPRISE_API',
    f'/vault/items/{vault_uuid}/files?user_type=ENTERPRISE_API',
]

for path in endpoints:
    url = DC_BASE + path
    req = urllib.request.Request(url, headers={'Authorization': 'Bearer '+token, 'Accept': 'application/json'}, method='GET')
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            body_text = r.read().decode()
            ct = r.headers.get('Content-Type','')
            print(f'SUCCESS {path}: CT={ct} body={body_text[:200]}')
    except Exception as e:
        err = ''
        try: err = e.read().decode()[:100]
        except: pass
        print(f'FAIL {path}: {e.code if hasattr(e,"code") else ""} {err[:80]}')
