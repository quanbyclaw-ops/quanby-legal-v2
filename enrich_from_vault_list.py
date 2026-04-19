import json, urllib.request, re, uuid as _uuid_mod
from datetime import datetime, timezone

now = datetime.now(timezone.utc).isoformat()

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

# Fetch all vault items
url = DC_BASE+'/vault/items?user_type=ENTERPRISE_API&per_page=50&page=1&user_items_only=no&api_integrated_projects_only=no'
req2 = urllib.request.Request(url, headers={'Authorization': 'Bearer '+token}, method='GET')
with urllib.request.urlopen(req2, timeout=15) as r2:
    vault_items = json.loads(r2.read().decode()).get('data', [])

# Load local data
with open('/var/www/quanby-legal/backend/data/appointments.json') as f:
    apts = json.load(f)
with open('/var/www/quanby-legal/backend/data/users.json') as f:
    users = json.load(f)

christian = next((u for u in users.values() if 'christianmontesor@gmail.com' in u.get('email','')), {})
profile = christian.get('profile') or {}

# Build appointment lookup by dc_project_uuid
apt_by_dc = {}
for aid, apt in apts.items():
    for doc in apt.get('session_documents', []):
        dc_uuid = doc.get('doconchain_project_uuid') or doc.get('project_uuid', '')
        if dc_uuid:
            apt_by_dc[dc_uuid] = (aid, apt, doc)

# Rebuild registry from vault items with full data
acts = []
for item in vault_items:
    if item.get('status','').lower() != 'completed':
        continue
    
    act_id = str(_uuid_mod.uuid4())
    vault_uuid = item.get('uuid','')
    proj_uuid = item.get('project_uuid','')
    
    raw_name = item.get('name','') or 'Document'
    doc_name = re.sub(r'\s*\(\d+\)\s*$', '', raw_name).strip()
    
    # Find matching appointment
    apt_id = ''
    client_name = ''
    client_email = ''
    notarization_type = 'ACKNOWLEDGMENT'
    
    if proj_uuid in apt_by_dc:
        apt_id, apt, doc = apt_by_dc[proj_uuid]
        client_name = apt.get('client_name','')
        client_email = apt.get('client_email','')
        notarization_type = doc.get('notarization_type','ACKNOWLEDGMENT')
        doc_name = doc.get('doc_name') or doc.get('name') or doc_name
    
    # Dates from vault item
    created_at = item.get('created_at','') or now
    updated_at = item.get('updated_at','') or created_at
    
    acts.append({
        'id': act_id,
        'act_id': act_id,
        'apt_id': apt_id,
        'enp_id': christian.get('id',''),
        'enp_name': (christian.get('first_name','') + ' ' + christian.get('last_name','')).strip(),
        'enp_email': christian.get('email',''),
        'client_name': client_name or 'Signer',
        'client_email': client_email,
        'principal': client_name or 'Signer',
        'principal_name': client_name or 'Signer',
        'witness_name': '',
        'doc_name': doc_name,
        'notarization_type': notarization_type,
        'act_type': notarization_type,
        'dc_project_uuid': proj_uuid,
        'dc_vault_uuid': vault_uuid,
        'dc_reference_no': item.get('reference_number','') or '',
        'dc_status': 'completed',
        'dc_completed_at': updated_at,
        'dc_file_url': '',
        'dc_file_name': '',
        'executed_at': updated_at[:10] if updated_at else now[:10],
        'sc_synced': False,
        'sc_registry_id': None,
        'nrid': '',
        'nrn': '',
        'sc_synced_at': None,
        'sc_note': '',
        'roll_no': profile.get('roll_no',''),
        'commission_no': profile.get('commission_no',''),
        'notary_address': profile.get('notary_address',''),
        'city_province': profile.get('city_province',''),
        'location': profile.get('notary_address') or profile.get('city_province') or 'Legazpi City, Albay',
        'mode': 'REN',
        'fee': '',
        'registry_no': '',
        'created_at': created_at,
    })

with open('/var/www/quanby-legal/backend/data/notarial_registry.json', 'w') as f:
    json.dump({'acts': acts, 'books': {}}, f, indent=2)

print(f'Registry rebuilt: {len(acts)} acts')
for a in acts:
    print(f'  {a["doc_name"][:30]:<30} | apt:{a["apt_id"][:8] if a["apt_id"] else "---"} | principal:{a["principal_name"][:20]:<20} | dc:{a["dc_project_uuid"][:12]}')
