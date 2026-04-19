with open('/var/www/quanbyai-website/calendar.html', 'r', encoding='utf-8') as f:
    src = f.read()

# Accept both spellings of username, and the correct password
old = "var CREDS = { user: 'quanbyai', pass: 'Alyssa7719!!' };"
new = "var CREDS = { users: ['quanbyai', 'quahnbyai', 'quanby'], pass: 'Alyssa7719!!' };"

old_check = "if (u === CREDS.user && p === CREDS.pass) {"
new_check = "if (CREDS.users.indexOf(u) >= 0 && p === CREDS.pass) {"

if old in src:
    src = src.replace(old, new)
    print('Fixed CREDS')
else:
    print('CREDS pattern not found')

if old_check in src:
    src = src.replace(old_check, new_check)
    print('Fixed check')
else:
    print('Check pattern not found')

with open('/var/www/quanbyai-website/calendar.html', 'w', encoding='utf-8') as f:
    f.write(src)
print('Done')
