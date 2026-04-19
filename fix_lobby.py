import os

for fname in ['lobby.html', 'dashboard.html', 'browse.html', 'registry.html', 'profile.html']:
    path = '/var/www/quanby-legal/' + fname
    if not os.path.exists(path):
        continue
    with open(path, 'r', encoding='utf-8') as f:
        src = f.read()
    # Replace bare redirect-to-root on auth failure with handleReauth
    old = "location.href = '/';"
    new = "QLAuth._handleReauth();"
    count = src.count(old)
    if count > 0:
        # Only replace in auth-failure contexts, not in signOut
        # Safe: replace all occurrences that aren't in signOut functions
        lines = src.split('\n')
        new_lines = []
        for line in lines:
            if old in line and 'signOut' not in line and 'logout' not in line.lower() and 'sign_out' not in line:
                line = line.replace(old, new)
            new_lines.append(line)
        new_src = '\n'.join(new_lines)
        replaced = src.count(old) - new_src.count(old)
        if replaced > 0:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(new_src)
            print(f'{fname}: replaced {replaced} auth redirect(s)')
        else:
            print(f'{fname}: no replacements needed')
    else:
        print(f'{fname}: no bare redirects found')
