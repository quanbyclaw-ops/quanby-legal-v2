import json
from datetime import datetime, timezone

now = datetime.now(timezone.utc).isoformat()

# Known good state from worktrees
worktree_users = {}
for wt in ['mobile-nav', 'theme-switcher', 'account-settings']:
    try:
        with open(f'/var/www/qlegal-worktrees/{wt}/backend/data/users.json') as f:
            d = json.load(f)
        for uid, u in d.items():
            email = (u.get('email') or '').lower()
            if email not in [v.get('email','').lower() for v in worktree_users.values()]:
                worktree_users[uid] = u
    except Exception as e:
        print('wt error:', e)

with open('/var/www/quanby-legal/backend/data/users.json') as f:
    users = json.load(f)

existing_emails = {(u.get('email') or '').lower(): uid for uid, u in users.items()}

# Restore missing users from worktrees
for uid, u in worktree_users.items():
    email = (u.get('email') or '').lower()
    if email not in existing_emails:
        print('Restoring:', email)
        users[uid] = u
        existing_emails[email] = uid

# Role/step/cert map
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
        # Clear retake blocks so exam works again
        u['retake_count'] = 0
        u['retake_payment_confirmed'] = False
        u['test_result'] = None
        if not u.get('kyc_verified_at'):
            u['kyc_verified_at'] = now
        if not u.get('certified_at'):
            u['certified_at'] = now
        users[uid] = u
        print(f'Fixed: {email} -> {role}/{step} retake_count=0')

with open('/var/www/quanby-legal/backend/data/users.json', 'w') as f:
    json.dump(users, f, indent=2, ensure_ascii=False)

print(f'\nTotal: {len(users)} users saved')
for uid, u in users.items():
    print(f'  {u.get("email")} | {u.get("role")} | {u.get("onboarding_step")} | retake={u.get("retake_count",0)}')
