with open('/var/www/quanby-legal/appointments.html', 'r', encoding='utf-8') as f:
    src = f.read()

# Fix 1: startVideoSession - include room_name in URL
old = "    location.href = '/session?apt=' + encodeURIComponent(aptId);"
new = "    location.href = '/session?apt=' + encodeURIComponent(aptId) + '&room=' + encodeURIComponent(data.room_name || '');"

if old in src:
    src = src.replace(old, new)
    print('Fixed startVideoSession URL')
else:
    print('Pattern not found for startVideoSession')

# Fix 2: Rejoin button - also needs room in URL
# The Rejoin <a href> is built in buildEnpCard and buildClientCard
# They use /session?apt=... without room
# Let's pass room from apt.session_room_name
old_rejoin_enp = "href=\"/session?apt=${escHtml(apt.apt_id)}\" style=\"text-decoration:none;\">"
new_rejoin_enp = "href=\"/session?apt=${escHtml(apt.apt_id)}&room=${encodeURIComponent(apt.session_room_name || '')}\" style=\"text-decoration:none;\">"

count = src.count(old_rejoin_enp)
if count > 0:
    src = src.replace(old_rejoin_enp, new_rejoin_enp)
    print(f'Fixed {count} Rejoin Session href(s)')
else:
    # Try alternate pattern
    old_rejoin2 = 'href="/session?apt=${escHtml(apt.apt_id)}"'
    count2 = src.count(old_rejoin2)
    print(f'Alt pattern found {count2} times')
    if count2:
        src = src.replace(old_rejoin2,
                          'href="/session?apt=${escHtml(apt.apt_id)}&room=${encodeURIComponent(apt.session_room_name || \'\')}"')
        print(f'Fixed {count2} href(s)')

with open('/var/www/quanby-legal/appointments.html', 'w', encoding='utf-8') as f:
    f.write(src)
print('appointments.html saved')

# Verify
for line in src.split('\n'):
    if '/session?apt=' in line:
        print(' CHECK:', line.strip()[:120])
