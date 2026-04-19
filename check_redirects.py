import subprocess, os

# Check for bare / redirects in quanby-legal pages
files = [
    '/var/www/quanby-legal/appointments.html',
    '/var/www/quanby-legal/lobby.html',
    '/var/www/quanby-legal/session.html',
    '/var/www/quanby-legal/assets/ql-auth.js',
]

for path in files:
    try:
        with open(path) as f:
            lines = f.readlines()
        hits = [(i+1, l.strip()) for i, l in enumerate(lines)
                if ("location.href = '/'" in l or "location.href='/'" in l or "location.href = \"/\"" in l)
                and 'logout' not in l.lower() and 'signout' not in l.lower() and 'sign_out' not in l.lower()]
        if hits:
            print(f'\n{path}: {len(hits)} redirect(s) to /')
            for ln, text in hits:
                print(f'  L{ln}: {text[:100]}')
        else:
            print(f'{path}: OK (no bare / redirects)')
    except Exception as e:
        print(f'{path}: ERROR {e}')
