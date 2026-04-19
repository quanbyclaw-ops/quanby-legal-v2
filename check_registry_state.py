import json, os

# Check notarial registry file
reg_path = '/var/www/quanby-legal/backend/data/notarial_registry.json'
if os.path.exists(reg_path):
    with open(reg_path) as f:
        reg = json.load(f)
    acts = reg.get('acts', [])
    print(f'Registry acts: {len(acts)}')
    for a in acts[:5]:
        print(' ', a.get('doc_name','?'), '| dc_status:', a.get('dc_status','?'))
else:
    print('notarial_registry.json does not exist')

# Check ended sessions with documents
with open('/var/www/quanby-legal/backend/data/appointments.json') as f:
    apts = json.load(f)

ended_with_docs = [(k,v) for k,v in apts.items() if v.get('session_status')=='ended' and v.get('session_documents')]
print(f'\nEnded sessions with docs: {len(ended_with_docs)}')
for aid, apt in ended_with_docs:
    for doc in apt.get('session_documents', []):
        dc_uuid = doc.get('doconchain_project_uuid') or doc.get('project_uuid','?')
        signers = doc.get('signers', [])
        signed = [s for s in signers if s.get('signed')]
        print(f'  apt:{aid[:8]} doc:{doc.get("doc_name","?")} dc:{dc_uuid[:12] if dc_uuid else "None"} signers:{len(signers)} signed:{len(signed)} plotting_done:{doc.get("plotting_done")}')
