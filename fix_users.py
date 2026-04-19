import json
from datetime import datetime, timezone

now = datetime.now(timezone.utc).isoformat()

with open('/var/www/quanby-legal/backend/data/users.json') as f:
    users = json.load(f)

print('Current users:', len(users))
for uid, u in users.items():
    print(' ', uid[:8], u.get('email'), '| role:', u.get('role'), '| step:', u.get('onboarding_step'))

# Known emails from worktrees that are missing from live users.json
known_missing = [
    'quanbyclaw@gmail.com',
    'mj.balcueva.3@gmail.com',
    'michael@quanbyit.com',
]

# Get existing emails
existing_emails = {u.get('email','').lower() for u in users.values()}

print('\nMissing accounts to restore:', [e for e in known_missing if e not in existing_emails])

# Load from a worktree to get their basic data
with open('/var/www/qlegal-worktrees/mobile-nav/backend/data/users.json') as f:
    wt_users = json.load(f)

# Merge missing users from worktree into live users.json
restored = 0
for uid, u in wt_users.items():
    email = (u.get('email') or '').lower()
    if email not in existing_emails:
        print('Restoring:', email)
        users[uid] = u
        existing_emails.add(email)
        restored += 1

print('Restored', restored, 'missing accounts')

# Now fix ALL users' roles/steps properly
role_map = {
    'christianmontesor@gmail.com': ('attorney', 'certified', 'certified', 'active'),
    'quanbyclaw@gmail.com':        ('attorney', 'certified', 'certified', 'active'),
    'michael@quanbyit.com':        ('attorney', 'certified', 'certified', 'active'),
    'mj.balcueva.3@gmail.com':     ('client',  'certified', 'certified', None),
    '07101471@dwc-legazpi.edu':    ('client',  'certified', 'certified', None),
    'afbstolentinas@gmail.com':    ('client',  'certified', 'certified', None),
}

for uid, u in users.items():
    email = (u.get('email') or '').lower()
    if email in role_map:
        role, step, cert, sc = role_map[email]
        u['role'] = role
        u['onboarding_step'] = step
        u['certificate_status'] = cert
        if sc:
            u['sc_commission_status'] = sc
        u['liveness_verified'] = True
        if not u.get('kyc_verified_at'):
            u['kyc_verified_at'] = now
        if not u.get('certified_at'):
            u['certified_at'] = now
        users[uid] = u
        print('Fixed:', email, '->', role, step)

with open('/var/www/quanby-legal/backend/data/users.json', 'w') as f:
    json.dump(users, f, indent=2, ensure_ascii=False)

print('\nFinal users.json:')
for uid, u in users.items():
    print(' ', u.get('email'), '| role:', u.get('role'), '| step:', u.get('onboarding_step'), '| cert:', u.get('certificate_status'))

print('\nDone. Total:', len(users), 'accounts')
