import json

# Fix 1: registry.json — add 'id' field matching what the API expects
with open('/var/www/quanby-legal/backend/data/notarial_registry.json') as f:
    reg = json.load(f)

acts = reg.get('acts', [])
changed = 0
for act in acts:
    if 'id' not in act:
        act['id'] = act.get('act_id', '')
        changed += 1
    # Also add missing fields the API/UI expects
    if 'principal' not in act:
        act['principal'] = act.get('client_name', '')
    if 'roll_no' not in act:
        act['roll_no'] = ''
    if 'commission_no' not in act:
        act['commission_no'] = ''
    if 'nrid' not in act:
        act['nrid'] = ''
    if 'nrn' not in act:
        act['nrn'] = ''
    if 'sc_synced_at' not in act:
        act['sc_synced_at'] = None
    if 'sc_note' not in act:
        act['sc_note'] = ''
    if 'registry_no' not in act:
        act['registry_no'] = ''
    if 'fee' not in act:
        act['fee'] = ''

with open('/var/www/quanby-legal/backend/data/notarial_registry.json', 'w') as f:
    json.dump(reg, f, indent=2)
print(f'Fixed {changed} acts: added "id" and missing fields')

# Verify
with open('/var/www/quanby-legal/backend/data/notarial_registry.json') as f:
    reg2 = json.load(f)
print('Acts:', len(reg2['acts']))
print('First act id:', reg2['acts'][0].get('id', 'MISSING'))
print('Keys:', sorted(reg2['acts'][0].keys()))
