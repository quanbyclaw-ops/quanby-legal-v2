import json, urllib.request, os

env = {}
with open('/var/www/quanby-legal/backend/.env') as f:
    for line in f:
        line = line.strip()
        if '=' in line and not line.startswith('#'):
            k, v = line.split('=', 1)
            env[k] = v.strip('"\'')

DC_BASE = env.get('DOCONCHAIN_API_URL', 'https://stg-api2.doconchain.com')
DC_KEY  = env.get('DOCONCHAIN_CLIENT_KEY', '')
DC_SECRET = env.get('DOCONCHAIN_CLIENT_SECRET', '')
ENP_EMAIL = 'christianmontesor@gmail.com'

# Get token
boundary = 'QLcheck'
body = ('--'+boundary+'\r\nContent-Disposition: form-data; name="client_key"\r\n\r\n'+DC_KEY+'\r\n'
        '--'+boundary+'\r\nContent-Disposition: form-data; name="client_secret"\r\n\r\n'+DC_SECRET+'\r\n'
        '--'+boundary+'\r\nContent-Disposition: form-data; name="email"\r\n\r\n'+ENP_EMAIL+'\r\n'
        '--'+boundary+'--\r\n').encode()
req = urllib.request.Request(DC_BASE+'/api/v2/generate/token', data=body,
    headers={'Content-Type': 'multipart/form-data; boundary='+boundary}, method='POST')
with urllib.request.urlopen(req, timeout=15) as r:
    token = (json.loads(r.read().decode()).get('data') or {}).get('token', '')

# Try to get the PDF from the FIRST completed vault item
vault_uuid = 'f6f97e89-710b-4105-ba5b-276373751d99'  # first completed item
project_uuid = 'Gs2t3qmFjMARP4p'

print('Trying various download approaches...')

# Approach 1: /api/v2/projects/{uuid}/download
attempts = [
    (DC_BASE+'/api/v2/projects/'+project_uuid+'/download?user_type=ENTERPRISE_API', 'GET', 'project download'),
    (DC_BASE+'/vault/items/'+vault_uuid+'/download?user_type=ENTERPRISE_API', 'GET', 'vault download'),
    (DC_BASE+'/api/v2/projects/'+project_uuid+'?user_type=ENTERPRISE_API', 'GET', 'project details'),
    (DC_BASE+'/vault/items/'+vault_uuid+'?user_type=ENTERPRISE_API', 'GET', 'vault item detail'),
]

for url, method, label in attempts:
    req2 = urllib.request.Request(url, headers={'Authorization': 'Bearer '+token, 'Accept': '*/*'}, method=method)
    try:
        with urllib.request.urlopen(req2, timeout=15) as r2:
            ct = r2.headers.get('Content-Type', '')
            data = r2.read()
            print(f'SUCCESS [{label}]: CT={ct} size={len(data)} first_bytes={data[:50]}')
            if b'%PDF' in data[:10] or b'PDF' in data[:10]:
                with open('/tmp/test_doc.pdf', 'wb') as f:
                    f.write(data)
                print('  -> Saved PDF to /tmp/test_doc.pdf!')
            else:
                try:
                    j = json.loads(data)
                    print('  -> JSON:', json.dumps(j, indent=2)[:300])
                except:
                    print('  -> Raw:', data[:200])
    except Exception as e:
        err = ''
        try: err = e.read().decode()[:100]
        except: pass
        print(f'FAIL [{label}]: {e.code if hasattr(e,"code") else ""} {err}')
