import json

with open('/var/www/quanby-legal/backend/data/users.json') as f:
    users = json.load(f)

for uid, u in users.items():
    if 'christian' in u.get('email', '').lower():
        print('email:', u.get('email'))
        print('role:', u.get('role'))
        print('cert:', u.get('certificate_status'))
        print('step:', u.get('onboarding_step'))
        print('retake:', u.get('retake_count', 0))
        print('id:', uid[:16])
