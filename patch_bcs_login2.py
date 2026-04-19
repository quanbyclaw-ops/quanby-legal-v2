with open('/var/www/bcs-ims/resources/views/auth/login.blade.php', 'rb') as f:
    raw = f.read()

# Replace the garbled title bytes directly
old_title = b'<title>Login \xc3\xa2\xe2\x82\xac\xe2\x80\x9d DENR Inventory Management System</title>'
new_title = b'<title>Login &mdash; Quanby Procurement</title>'
raw = raw.replace(old_title, new_title)

with open('/var/www/bcs-ims/resources/views/auth/login.blade.php', 'wb') as f:
    f.write(raw)

# Verify
with open('/var/www/bcs-ims/resources/views/auth/login.blade.php', 'r', encoding='utf-8', errors='replace') as f:
    content = f.read()

remaining = [l.strip() for l in content.split('\n') if ('DENR' in l or 'denr.gov' in l or 'Environment' in l)]
if remaining:
    print('Still has DENR refs:')
    for r in remaining:
        print(' ', r)
else:
    print('All DENR references removed from login page')

# Check title
for l in content.split('\n'):
    if '<title>' in l:
        print('Title:', l.strip())
