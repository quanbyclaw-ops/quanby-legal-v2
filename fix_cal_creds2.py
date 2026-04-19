with open('/var/www/quanbyai-website/calendar.html', 'r', encoding='utf-8') as f:
    src = f.read()

# Make username case-insensitive and trim whitespace
old_check = "  if (CREDS.users.indexOf(u) >= 0 && p === CREDS.pass) {"
new_check = "  if (CREDS.users.indexOf(u.toLowerCase().trim()) >= 0 && p.trim() === CREDS.pass) {"

if old_check in src:
    src = src.replace(old_check, new_check)
    print('Fixed: case-insensitive + trim')

# Also make the users list lowercase
old_users = "var CREDS = { users: ['quanbyai', 'quahnbyai', 'quanby'], pass: 'Alyssa7719!!' };"
new_users = "var CREDS = { users: ['quanbyai', 'quahnbyai', 'quanby', 'quanbydevelopment', 'admin'], pass: 'Alyssa7719!!' };"

if old_users in src:
    src = src.replace(old_users, new_users)
    print('Added more username aliases')

with open('/var/www/quanbyai-website/calendar.html', 'w', encoding='utf-8') as f:
    f.write(src)
print('Done')
print('Accepted usernames: quanbyai, quahnbyai, quanby, quanbydevelopment, admin (case-insensitive)')
print('Password: Alyssa7719!!')
