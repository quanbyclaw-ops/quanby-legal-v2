import json

# Check registry file
with open('/var/www/quanby-legal/backend/data/notarial_registry.json') as f:
    r = json.load(f)

acts = r.get('acts', [])
books = r.get('books', {})
print('acts:', len(acts))
print('books:', len(books))
for a in acts[:5]:
    print(' enp:', a.get('enp_id','?')[:12], '| doc:', a.get('doc_name','?')[:30], '| status:', a.get('dc_status','?'))

# Check all appointments for ended sessions with docs
with open('/var/www/quanby-legal/backend/data/appointments.json') as f:
    apts = json.load(f)

ended = [(aid, a) for aid, a in apts.items() if a.get('session_status') == 'ended']
print()
print('Ended sessions:', len(ended))
for aid, a in ended:
    docs = a.get('session_documents', [])
    print(' apt:', aid[:12], '| enp:', a.get('enp_id','?')[:12], '| docs:', len(docs))
    for d in docs:
        dc_uuid = d.get('doconchain_project_uuid') or d.get('project_uuid', '?')
        print('   doc:', d.get('doc_name','?')[:30], '| dc_uuid:', dc_uuid[:12] if dc_uuid else 'None')

# Check if the registry API will return anything for ENP users
with open('/var/www/quanby-legal/backend/data/users.json') as f:
    users = json.load(f)

attorneys = [(uid, u) for uid, u in users.items() if u.get('role') == 'attorney']
print()
print('Attorney user IDs:')
for uid, u in attorneys:
    print(' ', uid[:12], u.get('email'), '| cert:', u.get('certificate_status'))
    matching = [a for a in acts if a.get('enp_id') == uid]
    print('   acts in registry:', len(matching))
