import json
with open('/var/www/quanby-legal/backend/data/users.json') as f:
    users = json.load(f)

print('Total accounts:', len(users))
print()
for uid, u in users.items():
    email = (u.get('email') or '?')[:40]
    role = u.get('role') or 'NONE'
    step = u.get('onboarding_step') or 'NONE'
    cert = u.get('certificate_status') or 'NONE'
    print('  ' + email.ljust(40) + ' role=' + role.ljust(12) + ' step=' + step.ljust(15) + ' cert=' + cert)
