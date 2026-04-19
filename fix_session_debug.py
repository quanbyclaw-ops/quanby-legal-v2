with open('/var/www/quanby-legal/session.html', 'r') as f:
    src = f.read()

# Find the init() function and add debug at start
old = '''async function init() {
  console.log('[INIT] Starting. FROM_LOBBY=' + FROM_LOBBY + ' APT_ID=' + APT_ID + ' LK_TOKEN_LEN=' + LK_TOKEN.length + ' ROOM=' + ROOM_NAME);
  setLoading('Checking authentication\u2026');'''

new = '''async function init() {
  console.log('[INIT] Starting. FROM_LOBBY=' + FROM_LOBBY + ' APT_ID=' + APT_ID + ' LK_TOKEN_LEN=' + LK_TOKEN.length + ' ROOM=' + ROOM_NAME);
  setLoading('Token=' + LK_TOKEN.length + ' Room=' + (ROOM_NAME||'NONE') + ' Lobby=' + FROM_LOBBY);'''

if old in src:
    src = src.replace(old, new)
    print('Debug added to init()')
else:
    # Try simpler - just find init and add one log
    idx = src.find('async function init() {')
    if idx >= 0:
        # Add debug line showing token status at top of loading screen
        add = "\n  document.getElementById('loading-text').textContent = 'Debug: token_len=' + LK_TOKEN.length + ' room=' + ROOM_NAME + ' from_lobby=' + FROM_LOBBY;"
        src = src[:idx + len('async function init() {')] + add + src[idx + len('async function init() {'):]
        print('Debug added via index')
    else:
        print('init() not found')

with open('/var/www/quanby-legal/session.html', 'w') as f:
    f.write(src)
