with open('/var/www/quanby-legal/appointments.html', 'r', encoding='utf-8') as f:
    src = f.read()

replacements = [
    (
        '<a class="btn-session-join" href="/lobby?apt=${escHtml(apt.apt_id)}">',
        '<a class="btn-session-join" href="/lobby?apt=${escHtml(apt.apt_id)}&room=${encodeURIComponent(apt.session_room_name||\'\')}">'
    ),
    (
        '<a class="btn-session-join" href="/lobby?apt=${escHtml(apt.apt_id)}" style="text-decoration:none;">',
        '<a class="btn-session-join" href="/lobby?apt=${escHtml(apt.apt_id)}&room=${encodeURIComponent(apt.session_room_name||\'\')}" style="text-decoration:none;">'
    ),
    (
        "    location.href = '/lobby?apt=' + encodeURIComponent(aptId);",
        "    location.href = '/lobby?apt=' + encodeURIComponent(aptId) + '&room=' + encodeURIComponent(data.room_name || '');"
    ),
]

count = 0
for old, new in replacements:
    if old in src:
        src = src.replace(old, new)
        count += 1
        print('Fixed:', old[:60])
    else:
        print('Not found:', old[:60])

with open('/var/www/quanby-legal/appointments.html', 'w', encoding='utf-8') as f:
    f.write(src)
print('Total:', count, 'fixes')
