with open('/var/www/quanby-legal/appointments.html', 'r', encoding='utf-8') as f:
    src = f.read()

# Find ALL /session?apt= occurrences
for i, line in enumerate(src.split('\n'), 1):
    if '/session?apt=' in line:
        print(f'L{i}: {line.strip()[:120]}')

# Fix the remaining one without room
old = '<a class="btn-session-join" href="/session?apt=${escHtml(apt.apt_id)}">'
new = '<a class="btn-session-join" href="/session?apt=${escHtml(apt.apt_id)}&room=${encodeURIComponent(apt.session_room_name || \'\')}">'

if old in src:
    src = src.replace(old, new)
    print('Fixed remaining client rejoin href')
    with open('/var/www/quanby-legal/appointments.html', 'w', encoding='utf-8') as f:
        f.write(src)
    print('Saved')
else:
    print('No more bare /session?apt= hrefs found')
