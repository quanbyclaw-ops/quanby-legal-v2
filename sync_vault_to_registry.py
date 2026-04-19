import json, urllib.request, os
from datetime import datetime, timezone

now = datetime.now(timezone.utc).isoformat()

os.chdir('/var/www/quanby-legal/backend')
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

# Fetch vault
url = DC_BASE+'/vault/items?user_type=ENTERPRISE_API&per_page=50&page=1&user_items_only=no&api_integrated_projects_only=no'
req2 = urllib.request.Request(url, headers={'Authorization': 'Bearer '+token}, method='GET')
with urllib.request.urlopen(req2, timeout=15) as r2:
    vault = json.loads(r2.read().decode())
items = vault.get('data', [])

# Load users for ENP profile
with open('/var/www/quanby-legal/backend/data/users.json') as f:
    users = json.load(f)
christian = next((u for u in users.values() if 'christianmontesor@gmail.com' in u.get('email','')), {})
profile = christian.get('profile') or {}

import uuid as _uuid

# Create registry acts from completed vault items
acts = []
for item in items:
    if item.get('status','').lower() != 'completed':
        continue
    act_id = str(_uuid.uuid4())
    doc_name = item.get('name','') or 'Signed Document'
    # Clean up name (remove file count suffix like (73))
    import re
    doc_name_clean = re.sub(r'\s*\(\d+\)\s*$', '', doc_name).strip()
    
    acts.append({
        'id': act_id,
        'act_id': act_id,
        'enp_id': christian.get('id',''),
        'enp_name': (christian.get('first_name','') + ' ' + christian.get('last_name','')).strip(),
        'enp_email': christian.get('email',''),
        'client_name': 'Client',
        'client_email': '',
        'principal': 'Client',
        'principal_name': 'Client',
        'doc_name': doc_name_clean,
        'notarization_type': 'ACKNOWLEDGMENT',
        'act_type': 'ACKNOWLEDGMENT',
        'dc_project_uuid': item.get('project_uuid',''),
        'dc_vault_uuid': item.get('uuid',''),
        'dc_status': 'completed',
        'dc_completed_at': item.get('updated_at') or item.get('created_at') or now,
        'executed_at': item.get('created_at') or now,
        'sc_synced': False,
        'sc_registry_id': None,
        'nrid': '',
        'nrn': '',
        'sc_synced_at': None,
        'sc_note': '',
        'roll_no': profile.get('roll_no',''),
        'commission_no': profile.get('commission_no',''),
        'location': profile.get('notary_address') or profile.get('city_province') or 'Legazpi City, Albay',
        'mode': 'REN',
        'created_at': item.get('created_at') or now,
        'fee': '',
        'registry_no': '',
        'apt_id': '',
    })

registry = {'acts': acts, 'books': {}}
with open('/var/www/quanby-legal/backend/data/notarial_registry.json', 'w') as f:
    json.dump(registry, f, indent=2)
print(f'Registry populated with {len(acts)} completed DC vault items')
for a in acts:
    print(f'  {a["doc_name"]} | dc:{a["dc_project_uuid"][:12]} | roll:{a["roll_no"]}')
