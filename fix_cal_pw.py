with open('/var/www/quanbyai-website/calendar.html', 'r', encoding='utf-8') as f:
    src = f.read()

old = "  var _u = u.toLowerCase().trim(); if (_u.indexOf('quanby') >= 0 || _u === 'admin' || _u === 'michael' || _u === 'christian' || (CREDS.users.indexOf(_u) >= 0 && p.trim() === CREDS.pass)) {"
new = "  var _u = u.toLowerCase().trim(); var _pw = 'Alyssa7719!!'; if ((_u.indexOf('quanby') >= 0 || _u === 'admin' || _u === 'michael' || _u === 'christian') && p.trim() === _pw) {"

if old in src:
    src = src.replace(old, new)
    print('Password set to Alyssa7719!!')

with open('/var/www/quanbyai-website/calendar.html', 'w', encoding='utf-8') as f:
    f.write(src)
