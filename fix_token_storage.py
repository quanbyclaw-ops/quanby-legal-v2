# Use sessionStorage to pass the token instead of URL params
# This avoids URL length limits and encoding issues with JWT

with open('/var/www/quanby-legal/lobby.html', 'r', encoding='utf-8') as f:
    lobby = f.read()

old_navigate = '''    const url = `/session?apt=${encodeURIComponent(APT_ID)}&room=${encodeURIComponent(room)}&from_lobby=1&lk_token=${encodeURIComponent(jd.token)}&lk_user=${encodeURIComponent(jd.user_name)}&lk_role=${encodeURIComponent(jd.user_role)}`;
    window.location.href = url;'''

new_navigate = '''    // Store token in sessionStorage (avoids URL length limits with JWT)
    try {
      sessionStorage.setItem('ql_lk_token', jd.token);
      sessionStorage.setItem('ql_lk_user', jd.user_name || '');
      sessionStorage.setItem('ql_lk_role', jd.user_role || '');
      sessionStorage.setItem('ql_lk_apt', APT_ID);
    } catch(e) { console.warn('sessionStorage failed:', e); }
    const url = `/session?apt=${encodeURIComponent(APT_ID)}&room=${encodeURIComponent(room)}&from_lobby=1`;
    window.location.href = url;'''

if old_navigate in lobby:
    lobby = lobby.replace(old_navigate, new_navigate)
    with open('/var/www/quanby-legal/lobby.html', 'w', encoding='utf-8') as f:
        f.write(lobby)
    print('lobby.html: token stored in sessionStorage')
else:
    print('lobby.html: navigate pattern not found')

# Update session.html to read from sessionStorage
with open('/var/www/quanby-legal/session.html', 'r', encoding='utf-8') as f:
    ses = f.read()

old_params = '''// Pre-fetched LiveKit token from lobby (avoids re-auth on session.html)
const LK_TOKEN    = params.get('lk_token') || '';
const LK_USER     = params.get('lk_user') || '';
const LK_ROLE     = params.get('lk_role') || '';'''

new_params = '''// Pre-fetched LiveKit token from lobby — stored in sessionStorage to avoid URL length limits
var LK_TOKEN = '', LK_USER = '', LK_ROLE = '';
try {
  var _storedApt = sessionStorage.getItem('ql_lk_apt') || '';
  if (_storedApt === (params.get('apt') || '')) {
    LK_TOKEN = sessionStorage.getItem('ql_lk_token') || '';
    LK_USER  = sessionStorage.getItem('ql_lk_user')  || '';
    LK_ROLE  = sessionStorage.getItem('ql_lk_role')  || '';
    // Clear after reading — single use
    if (LK_TOKEN) {
      sessionStorage.removeItem('ql_lk_token');
      sessionStorage.removeItem('ql_lk_user');
      sessionStorage.removeItem('ql_lk_role');
      sessionStorage.removeItem('ql_lk_apt');
      console.log('[Session] Got pre-fetched token from sessionStorage, len=' + LK_TOKEN.length);
    }
  }
} catch(e) { console.warn('[Session] sessionStorage read failed:', e); }'''

if old_params in ses:
    ses = ses.replace(old_params, new_params)
    with open('/var/www/quanby-legal/session.html', 'w', encoding='utf-8') as f:
        f.write(ses)
    print('session.html: reads token from sessionStorage')
else:
    print('session.html: params pattern not found')
