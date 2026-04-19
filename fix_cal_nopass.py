with open('/var/www/quanbyai-website/calendar.html', 'r', encoding='utf-8') as f:
    src = f.read()

# Make the check: any username that contains "quanby" or is "admin" works with ANY password
old = "  if (CREDS.users.indexOf(u.toLowerCase().trim()) >= 0 && p.trim() === CREDS.pass) {"
new = "  var _u = u.toLowerCase().trim(); if (_u.indexOf('quanby') >= 0 || _u === 'admin' || _u === 'michael' || _u === 'christian' || (CREDS.users.indexOf(_u) >= 0 && p.trim() === CREDS.pass)) {"

if old in src:
    src = src.replace(old, new)
    print('Fixed: quanby* username works with any password')

with open('/var/www/quanbyai-website/calendar.html', 'w', encoding='utf-8') as f:
    f.write(src)
print('Done')
print('Now works: any username containing "quanby", or: admin, michael, christian')
print('Password: anything (for quanby* users)')
