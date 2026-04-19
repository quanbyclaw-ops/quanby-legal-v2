import json

# Check current fee values
with open('/var/www/quanby-legal/backend/data/notarial_registry.json') as f:
    reg = json.load(f)

print('Current fees:')
for a in reg['acts'][:5]:
    print(' ', a.get('doc_name','?'), '| fee:', repr(a.get('fee','')), '| type:', a.get('notarization_type','?'))

# Fee schedule per SC/Philippine notarial practice
FEE_MAP = {
    'ACKNOWLEDGMENT': '₱100',
    'JURAT': '₱100',
    'AFFIRMATION': '₱100',
    'SIGNATURE_WITNESSING': '₱100',
    'OATH': '₱100',
    'COPY_CERTIFICATION': '₱50',
}

updated = 0
for act in reg['acts']:
    if not act.get('fee'):
        nt = act.get('notarization_type','').upper() or act.get('act_type','').upper()
        act['fee'] = FEE_MAP.get(nt, '₱100')
        updated += 1

with open('/var/www/quanby-legal/backend/data/notarial_registry.json', 'w') as f:
    json.dump(reg, f, indent=2)

print(f'Updated {updated} acts with fee')
