with open('/var/www/quanby-legal/session.html', 'r', encoding='utf-8') as f:
    src = f.read()

old_join_start = '''  // Preflight auth refresh — critical for InPrivate/fresh sessions
  try { await fetch('/api/auth/refresh', { method: 'POST', credentials: 'include' }); } catch(e) {}

  // Stop preview stream'''

new_join_start = '''  console.log('[joinSession] called, me=', me ? (typeof me === 'object' ? me.email : me) : 'null', 'userRole=' + userRole);
  // Preflight auth refresh — critical for InPrivate/fresh sessions
  try {
    const _jr = await fetch('/api/auth/refresh', { method: 'POST', credentials: 'include' });
    console.log('[joinSession] refresh status:', _jr.status);
  } catch(e) { console.warn('[joinSession] refresh failed:', e); }

  // Stop preview stream'''

old_join_api = '''      const _authFetch = (typeof QLAuth !== 'undefined' && QLAuth.authFetch) ? QLAuth.authFetch.bind(QLAuth) : function(u,o){ o.credentials='include'; return fetch(u,o); };
 const r = await _authFetch('/api/sessions/join', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ room_name: roomName, apt_id: APT_ID }),
      });
      if (!r.ok) {
        var errData = {};
        try { errData = await r.json(); } catch(je) {}
        var errMsg = errData.detail || ('Server error ' + r.status);
        _restorePrejoin(errMsg);
        return;
      }
      const data = await r.json();
      token    = data.token;
      userName = data.user_name;
      role     = data.user_role;'''

new_join_api = '''      const _authFetch = (typeof QLAuth !== 'undefined' && QLAuth.authFetch) ? QLAuth.authFetch.bind(QLAuth) : function(u,o){ o.credentials='include'; return fetch(u,o); };
      console.log('[joinSession] calling /api/sessions/join with room=' + roomName + ' apt=' + APT_ID);
      const r = await _authFetch('/api/sessions/join', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ room_name: roomName, apt_id: APT_ID }),
      });
      console.log('[joinSession] /api/sessions/join status:', r.status);
      if (!r.ok) {
        var errData = {};
        try { errData = await r.json(); } catch(je) {}
        var errMsg = errData.detail || ('Server error ' + r.status);
        console.error('[joinSession] join API failed:', errMsg);
        _restorePrejoin(errMsg);
        return;
      }
      const data = await r.json();
      console.log('[joinSession] got token, user_name=' + data.user_name + ' role=' + data.user_role);
      token    = data.token;
      userName = data.user_name;
      role     = data.user_role;'''

old_livekit = '''  setLoading('Joining LiveKit room…');
  try {
    _room = new LivekitClient.Room({
      adaptiveStream: true,
      dynacast: true,
    });
    setupRoomEvents(_room, userName, role);
    await _room.connect('wss://quanby-lms-k4aq44qe.livekit.cloud', token, {
      autoSubscribe: true,
    });'''

new_livekit = '''  setLoading('Joining LiveKit room…');
  console.log('[joinSession] connecting to LiveKit, token length=' + (token ? token.length : 0));
  try {
    _room = new LivekitClient.Room({
      adaptiveStream: true,
      dynacast: true,
    });
    setupRoomEvents(_room, userName, role);
    console.log('[joinSession] room.connect starting...');
    await _room.connect('wss://quanby-lms-k4aq44qe.livekit.cloud', token, {
      autoSubscribe: true,
    });
    console.log('[joinSession] room.connect SUCCESS, state=' + _room.state);'''

changed = 0
if old_join_start in src:
    src = src.replace(old_join_start, new_join_start); changed += 1; print('joinSession start debug added')
else:
    print('joinSession start pattern not found')

if old_join_api in src:
    src = src.replace(old_join_api, new_join_api); changed += 1; print('joinSession API debug added')
else:
    print('joinSession API pattern not found')

if old_livekit in src:
    src = src.replace(old_livekit, new_livekit); changed += 1; print('LiveKit connect debug added')
else:
    print('LiveKit connect pattern not found')

print(f'Total changes: {changed}')

with open('/var/www/quanby-legal/session.html', 'w', encoding='utf-8') as f:
    f.write(src)
