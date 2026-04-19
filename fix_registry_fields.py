import json

with open('/var/www/quanby-legal/backend/data/notarial_registry.json') as f:
    reg = json.load(f)
with open('/var/www/quanby-legal/backend/data/appointments.json') as f:
    apts = json.load(f)
with open('/var/www/quanby-legal/backend/data/users.json') as f:
    users = json.load(f)

user_map = {u['id']: u for u in users.values()}

for act in reg['acts']:
    apt_id = act.get('apt_id', '')
    apt = apts.get(apt_id, {})
    enp = user_map.get(act.get('enp_id', ''), {})
    profile = enp.get('profile') or {}

    # Principal from client info
    if not act.get('principal'):
        act['principal'] = apt.get('client_name') or act.get('client_name', '')
    act['principal_name'] = act.get('principal') or act.get('client_name', '')

    # ENP profile fields
    if not act.get('roll_no'):
        act['roll_no'] = profile.get('roll_no', '')
    if not act.get('commission_no'):
        act['commission_no'] = profile.get('commission_no', '')
    if not act.get('location'):
        act['location'] = profile.get('notary_address') or profile.get('city_province') or 'Legazpi City, Albay'

    # DC UUID from appointment docs
    if not act.get('dc_project_uuid'):
        docs = apt.get('session_documents', [])
        if docs:
            act['dc_project_uuid'] = docs[0].get('doconchain_project_uuid') or docs[0].get('project_uuid', '')

    # Act type and dates
    if not act.get('act_type'):
        act['act_type'] = act.get('notarization_type', 'ACKNOWLEDGMENT')
    if not act.get('executed_at'):
        act['executed_at'] = act.get('session_ended_at') or act.get('created_at', '')

    dc = act.get('dc_project_uuid', '') or ''
    print('Act', act['id'][:8], '| principal:', act.get('principal_name'), '| roll:', act.get('roll_no'), '| dc:', dc[:12])

with open('/var/www/quanby-legal/backend/data/notarial_registry.json', 'w') as f:
    json.dump(reg, f, indent=2)
print('Registry updated with full data')
