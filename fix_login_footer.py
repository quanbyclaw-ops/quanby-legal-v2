files = [
    '/var/www/bcs-ims/resources/views/auth/login.blade.php',
    '/var/www/opapru-edms/resources/views/auth/login.blade.php',
]

old = '''          <small style="color:#475569;">
            <i class="bi bi-shield-lock me-1"></i>
            Authorized users only
          </small>'''

new = '''          <small style="color:#475569;">
            <i class="bi bi-shield-lock me-1"></i>
            Authorized users only<br>
            Quanby Solutions, Inc.
          </small>'''

for path in files:
    with open(path, 'r', encoding='utf-8') as f:
        src = f.read()
    if old in src:
        src = src.replace(old, new)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(src)
        print('Fixed:', path.split('/')[-4])
    else:
        # Try alternate (already has Authorized users only on one line)
        old2 = '            Authorized users only &mdash; Quanby Solutions, Inc.'
        new2 = '            Authorized users only<br>\n            Quanby Solutions, Inc.'
        if old2 in src:
            src = src.replace(old2, new2)
            with open(path, 'w', encoding='utf-8') as f:
                f.write(src)
            print('Fixed (alt):', path.split('/')[-4])
        else:
            print('Pattern not found in:', path)
            import re
            m = re.search(r'Authorized users only[^\n]*', src)
            if m: print('  Current:', repr(m.group()))
