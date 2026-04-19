import json, urllib.request, os

os.chdir('/var/www/quanby-legal/backend')
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

# Get token for Christian
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

# Fetch vault items - all completed projects
url = DC_BASE+'/vault/items?user_type=ENTERPRISE_API&per_page=50&page=1&user_items_only=no&api_integrated_projects_only=no'
req2 = urllib.request.Request(url, headers={'Authorization': 'Bearer '+token, 'Accept': 'application/json'}, method='GET')
try:
    with urllib.request.urlopen(req2, timeout=15) as r2:
        vault = json.loads(r2.read().decode())
    items = vault.get('data', [])
    print(f'\nVault items: {len(items)}')
    for item in items:
        print(f'  uuid={item.get("uuid","?")} project_uuid={item.get("project_uuid","?")} status={item.get("status","?")} name={item.get("name","?")}')
    
    # Save vault data for inspection
    with open('/tmp/dc_vault.json', 'w') as f:
        json.dump(vault, f, indent=2)
    print('\nSaved to /tmp/dc_vault.json')
except Exception as e:
    err = ''
    try: err = e.read().decode()[:200]
    except: pass
    print('Vault fetch error:', e, err)
