import json

worktrees = ['mobile-nav', 'theme-switcher', 'account-settings']
best = None
best_count = 0

for wt in worktrees:
    path = '/var/www/qlegal-worktrees/' + wt + '/backend/data/users.json'
    try:
        with open(path) as f:
            users = json.load(f)
        count = len(users)
        print(wt, ':', count, 'users')
        for uid, u in users.items():
            print('  ', u.get('email'), '| role:', u.get('role'), '| step:', u.get('onboarding_step'), '| cert:', u.get('certificate_status'))
        if count > best_count:
            best_count = count
            best = (wt, path, users)
    except Exception as e:
        print(wt, 'ERROR:', e)

print()
if best:
    print('BEST SOURCE:', best[0], 'with', best_count, 'users')
