import json, urllib.request

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

boundary = 'QLcheck'
body = ('--'+boundary+'\r\nContent-Disposition: form-data; name="client_key"\r\n\r\n'+DC_KEY+'\r\n'
        '--'+boundary+'\r\nContent-Disposition: form-data; name="client_secret"\r\n\r\n'+DC_SECRET+'\r\n'
        '--'+boundary+'\r\nContent-Disposition: form-data; name="email"\r\n\r\n'+ENP_EMAIL+'\r\n'
        '--'+boundary+'--\r\n').encode()
req = urllib.request.Request(DC_BASE+'/api/v2/generate/token', data=body,
    headers={'Content-Type': 'multipart/form-data; boundary='+boundary}, method='POST')
with urllib.request.urlopen(req, timeout=15) as r:
    token = (json.loads(r.read().decode()).get('data') or {}).get('token', '')

# Get reference numbers and update registry
with open('/var/www/quanby-legal/backend/data/notarial_registry.json') as f:
    reg = json.load(f)

updated = 0
for act in reg['acts']:
    proj_uuid = act.get('dc_project_uuid', '')
    if not proj_uuid:
        continue
    # Fetch project details for reference number
    url = DC_BASE+'/api/v2/projects/'+proj_uuid+'?user_type=ENTERPRISE_API'
    req2 = urllib.request.Request(url, headers={'Authorization': 'Bearer '+token}, method='GET')
    try:
        with urllib.request.urlopen(req2, timeout=10) as r2:
            proj = json.loads(r2.read().decode())
        data = proj.get('data', {})
        ref_no = data.get('reference_number', '')
        signers = data.get('signers', [])
        # Get principal name from first signer
        if signers and not act.get('principal_name') or act.get('principal_name') == 'Signer':
            act['principal_name'] = signers[0].get('name', '') or signers[0].get('email', '')
            act['principal'] = act['principal_name']
            act['client_name'] = act['principal_name']
            act['client_email'] = signers[0].get('email', '')
        if ref_no:
            act['dc_reference_no'] = ref_no
            updated += 1
            print(f'  {proj_uuid[:12]}: ref={ref_no} principal={act.get("principal_name","?")}')
    except Exception as e:
        print(f'  {proj_uuid[:12]}: SKIP {str(e)[:60]}')

with open('/var/www/quanby-legal/backend/data/notarial_registry.json', 'w') as f:
    json.dump(reg, f, indent=2)
print(f'Updated {updated} acts with reference numbers')
