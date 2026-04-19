with open('/var/www/quanby-legal/session.html', 'r', encoding='utf-8') as f:
    ses = f.read()

old = '''// Pre-fetched LiveKit token from lobby — stored in sessionStorage to avoid URL length limits
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

new = '''// Pre-fetched LiveKit token — read from URL params first, then sessionStorage fallback
var LK_TOKEN = params.get('lk_token') || '';
var LK_USER  = params.get('lk_user')  || '';
var LK_ROLE  = params.get('lk_role')  || '';
if (LK_TOKEN) {
  console.log('[Session] Got pre-fetched token from URL, len=' + LK_TOKEN.length);
} else {
  try {
    var _storedApt = sessionStorage.getItem('ql_lk_apt') || '';
    if (_storedApt === (params.get('apt') || '')) {
      LK_TOKEN = sessionStorage.getItem('ql_lk_token') || '';
      LK_USER  = sessionStorage.getItem('ql_lk_user')  || '';
      LK_ROLE  = sessionStorage.getItem('ql_lk_role')  || '';
      if (LK_TOKEN) {
        sessionStorage.removeItem('ql_lk_token');
        sessionStorage.removeItem('ql_lk_user');
        sessionStorage.removeItem('ql_lk_role');
        sessionStorage.removeItem('ql_lk_apt');
        console.log('[Session] Got pre-fetched token from sessionStorage, len=' + LK_TOKEN.length);
      }
    }
  } catch(e) { console.warn('[Session] sessionStorage read failed:', e); }
}'''

if old in ses:
    ses = ses.replace(old, new)
    print('Fixed: reads from URL first, sessionStorage fallback')
else:
    print('Pattern not found — checking current state')
    idx = ses.find('LK_TOKEN')
    print('Context:', ses[max(0,idx-50):idx+300])

with open('/var/www/quanby-legal/session.html', 'w', encoding='utf-8') as f:
    f.write(ses)
