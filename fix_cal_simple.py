with open('/var/www/quanbyai-website/calendar.html', 'r', encoding='utf-8') as f:
    src = f.read()

# Change to a simple password without special chars that might cause issues
old = "var CREDS = { users: ['quanbyai', 'quahnbyai', 'quanby', 'quanbydevelopment', 'admin'], pass: 'Alyssa7719!!' };"
new = "var CREDS = { users: ['quanbyai', 'quahnbyai', 'quanby', 'quanbydevelopment', 'admin', 'QuanbyAI'], pass: 'Quanby2026' };"

# Also add a version marker so browser knows it's new
src = src.replace('<!-- v1 -->', '')  # remove old markers
src = src.replace('<html lang="en">', '<html lang="en"><!-- v3 -->')

if old in src:
    src = src.replace(old, new)
    print('Password changed to: Quanby2026')
else:
    print('CREDS pattern not found, searching...')
    import re
    m = re.search(r'var CREDS = \{[^;]+\};', src)
    if m:
        print('Found:', m.group())
        src = src[:m.start()] + new + src[m.end():]
        print('Replaced via regex')

with open('/var/www/quanbyai-website/calendar.html', 'w', encoding='utf-8') as f:
    f.write(src)
print('Done')
print()
print('NEW CREDENTIALS:')
print('Username: quanbyai (or admin, quanby)')
print('Password: Quanby2026')
