with open('/var/www/quanby-legal/session.html', 'r', encoding='utf-8') as f:
    src = f.read()

old = '''  // If we have room + apt but no token, get token directly (bypass auth/me)
  if (ROOM_NAME && APT_ID && !LK_TOKEN) {'''

new = '''  // If we have apt but no token, get token directly (bypass auth/me)
  if (APT_ID && !LK_TOKEN) {
    var _roomForJoin = ROOM_NAME;'''

if old in src:
    src = src.replace(old, new)
    # Also fix ROOM_NAME -> _roomForJoin in the join call
    src = src.replace(
        "body: JSON.stringify({ room_name: ROOM_NAME, apt_id: APT_ID })",
        "body: JSON.stringify({ room_name: _roomForJoin || ROOM_NAME, apt_id: APT_ID })"
    )
    with open('/var/www/quanby-legal/session.html', 'w', encoding='utf-8') as f:
        f.write(src)
    print('Fixed: APT_ID alone (no ROOM_NAME required) triggers self-join')
else:
    print('Pattern not found — checking current state')
    idx = src.find('If we have')
    print('Context:', src[idx:idx+100] if idx > 0 else 'NOT FOUND')
