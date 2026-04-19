import json, urllib.request, os, re
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
print('Token OK, len:', len(token))

# Load current registry and appointments/users
with open('/var/www/quanby-legal/backend/data/notarial_registry.json') as f:
    reg = json.load(f)
with open('/var/www/quanby-legal/backend/data/appointments.json') as f:
    apts = json.load(f)
with open('/var/www/quanby-legal/backend/data/users.json') as f:
    users = json.load(f)

christian = next((u for u in users.values() if 'christianmontesor@gmail.com' in u.get('email','')), {})
profile = christian.get('profile') or {}

# Build lookup: dc_project_uuid -> appointment
apt_by_dc = {}
for aid, apt in apts.items():
    for doc in apt.get('session_documents', []):
        dc_uuid = doc.get('doconchain_project_uuid') or doc.get('project_uuid', '')
        if dc_uuid:
            apt_by_dc[dc_uuid] = (aid, apt, doc)

# Enrich each registry act
enriched = 0
for act in reg['acts']:
    dc_project_uuid = act.get('dc_project_uuid', '')
    vault_uuid = act.get('dc_vault_uuid', '')
    
    if not vault_uuid:
        continue
    
    # Fetch specific vault item for full details
    url = DC_BASE+'/vault/items/'+vault_uuid+'?user_type=ENTERPRISE_API'
    req2 = urllib.request.Request(url, headers={'Authorization': 'Bearer '+token, 'Accept': 'application/json'}, method='GET')
    try:
        with urllib.request.urlopen(req2, timeout=15) as r2:
            detail = json.loads(r2.read().decode())
        data = detail.get('data', {})
        
        # Update dc_project_uuid from detail (may be more complete)
        proj_uuid = data.get('project_uuid', '') or data.get('uuid', '') or dc_project_uuid
        act['dc_project_uuid'] = proj_uuid
        
        # Reference number from DC
        ref_no = data.get('reference_number', '') or ''
        act['dc_reference_no'] = ref_no
        
        # Signers → principal and witness
        signers = data.get('signers', [])
        principals = [s for s in signers if s.get('status','').lower() in ('signed','completed','next group','pending')]
        
        if principals:
            act['principal_name'] = principals[0].get('name','') or principals[0].get('email','')
            act['principal'] = act['principal_name']
            act['client_name'] = act['principal_name']
            act['client_email'] = principals[0].get('email','')
        
        if len(principals) > 1:
            act['witness_name'] = principals[1].get('name','') or principals[1].get('email','')
        
        # Completed at
        completed_at = data.get('completed_at', '') or data.get('updated_at', '')
        if completed_at:
            act['dc_completed_at'] = completed_at
            act['executed_at'] = completed_at[:10] if completed_at else now[:10]
        
        # Try to match appointment
        if proj_uuid and proj_uuid in apt_by_dc:
            aid, apt, doc = apt_by_dc[proj_uuid]
            act['apt_id'] = aid
            act['client_name'] = apt.get('client_name','') or act.get('client_name','')
            act['client_email'] = apt.get('client_email','') or act.get('client_email','')
            act['principal'] = act['client_name']
            act['principal_name'] = act['client_name']
            act['notarization_type'] = doc.get('notarization_type','ACKNOWLEDGMENT')
            act['act_type'] = act['notarization_type']
        
        # File URL for download
        files = data.get('files', [])
        if files:
            act['dc_file_url'] = files[0].get('file_url','')
            act['dc_file_name'] = files[0].get('file_name','')
        
        # Doc name from DC
        if data.get('name'):
            clean_name = re.sub(r'\s*\(\d+\)\s*$', '', data['name']).strip()
            if clean_name:
                act['doc_name'] = clean_name
        
        enriched += 1
        print(f'  Enriched: {act["doc_name"]} | principal={act.get("principal_name","?")} | dc_uuid={proj_uuid[:12]} | ref={ref_no} | signers={len(signers)}')
    except Exception as e:
        err = ''
        try: err = str(e.read().decode()[:80])
        except: pass
        print(f'  Error fetching {vault_uuid[:12]}: {e} {err}')

with open('/var/www/quanby-legal/backend/data/notarial_registry.json', 'w') as f:
    json.dump(reg, f, indent=2)
print(f'\nEnriched {enriched}/{len(reg["acts"])} acts')
