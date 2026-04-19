import json, sys, os
sys.path.insert(0, '/var/www/quanby-legal/backend')

# Check the ended appointment doc
with open('/var/www/quanby-legal/backend/data/appointments.json') as f:
    apts = json.load(f)

apt_id = 'dbe70548-1de7-452b-9f04-15a3f84ce1ae'
apt = apts.get(apt_id, {})
docs = apt.get('session_documents', [])
enp_id = apt.get('enp_id', '')

print('Appointment:', apt_id[:12])
print('ENP ID:', enp_id[:12])
print('Session status:', apt.get('session_status'))
print('Docs:', len(docs))
for d in docs:
    dc_uuid = d.get('doconchain_project_uuid') or d.get('project_uuid', 'none')
    print('  doc:', d.get('doc_name', '?'), '| dc_uuid:', dc_uuid[:15] if dc_uuid else 'None')
    print('  signers:', len(d.get('signers', [])))
    print('  sig_requests:', len(d.get('signature_requests', [])))
    for sr in d.get('signature_requests', []):
        print('   ', sr.get('email'), '->', sr.get('status'))

print()
print('Triggering registry population...')
os.environ.setdefault('DOCONCHAIN_API_URL', 'https://stg-api2.doconchain.com')
os.environ.setdefault('DOCONCHAIN_APP_URL', 'https://stg-app.doconchain.com')

# Import and run the populate function directly
import importlib
main = importlib.import_module('main')
main._populate_registry_bg(apt_id, enp_id)

# Check result
try:
    with open('/var/www/quanby-legal/backend/data/notarial_registry.json') as f:
        reg = json.load(f)
    print()
    print('Registry now has', len(reg.get('acts', [])), 'acts')
    for a in reg.get('acts', []):
        print(' ', a.get('doc_name', '?'), '| status:', a.get('dc_status', '?'), '| enp:', a.get('enp_id', '?')[:12])
except FileNotFoundError:
    print('Registry file still not created — DC docs may not be completed yet')
