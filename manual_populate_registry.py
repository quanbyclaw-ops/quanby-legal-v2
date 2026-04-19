import json, uuid
from datetime import datetime, timezone

now = datetime.now(timezone.utc).isoformat()

with open('/var/www/quanby-legal/backend/data/appointments.json') as f:
    apts = json.load(f)

with open('/var/www/quanby-legal/backend/data/users.json') as f:
    users = json.load(f)

user_map = {u['id']: u for u in users.values()}

acts = []
for aid, apt in apts.items():
    if apt.get('session_status') not in ('ended',):
        continue
    docs = apt.get('session_documents', [])
    if not docs:
        continue
    enp = user_map.get(apt.get('enp_id', ''), {})
    client_name = apt.get('client_name', 'Unknown Client')
    for doc in docs:
        act_id = str(uuid.uuid4())
        acts.append({
            'act_id': act_id,
            'apt_id': aid,
            'enp_id': apt.get('enp_id', ''),
            'enp_name': apt.get('enp_name', enp.get('first_name','') + ' ' + enp.get('last_name','')).strip(),
            'enp_email': apt.get('enp_email', enp.get('email','')),
            'client_name': client_name,
            'client_email': apt.get('client_email', ''),
            'doc_name': doc.get('doc_name') or doc.get('name', 'Document'),
            'notarization_type': doc.get('notarization_type') or apt.get('notarization_type', 'ACKNOWLEDGMENT'),
            'dc_project_uuid': doc.get('doconchain_project_uuid') or doc.get('project_uuid', ''),
            'dc_status': 'staged',  # DC staging environment — project may have expired
            'dc_completed_at': None,
            'sc_synced': False,
            'sc_registry_id': None,
            'created_at': apt.get('session_ended_at') or apt.get('updated_at') or now,
            'session_ended_at': apt.get('session_ended_at', now),
            'mode': apt.get('mode', 'REN'),
            'note': 'Manually populated — DoconChain staging project may have expired',
        })

registry = {'acts': acts, 'books': {}}
with open('/var/www/quanby-legal/backend/data/notarial_registry.json', 'w') as f:
    json.dump(registry, f, indent=2)

print(f'Registry populated with {len(acts)} acts from {len([a for a in apts.values() if a.get("session_status")=="ended" and a.get("session_documents")])} ended sessions')
for a in acts:
    print(f'  {a["doc_name"]} | {a["client_name"]} | {a["notarization_type"]} | {a["dc_status"]}')
