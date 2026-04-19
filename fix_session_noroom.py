with open('/var/www/quanby-legal/session.html', 'r', encoding='utf-8') as f:
    src = f.read()

old = """} else if (!ROOM_NAME) {
  // APT_ID present but no room — session not yet started by ENP
  // Redirect to appointments so ENP can start it
  document.getElementById('loading-text').textContent = 'Session not started yet…';
  document.getElementById('loading-screen').innerHTML =
    '<div style="text-align:center;padding:2rem;">' +
    '<div style="font-size:2rem;margin-bottom:1rem">⏳</div>' +
    '<div style="color:var(--text);font-size:1rem;margin-bottom:.5rem;font-weight:600;">Session not started yet</div>' +
    '<div style="color:var(--muted);font-size:.85rem;margin-bottom:1.5rem;">The ENP has not started this session. Please go back and start the session from your appointments.</div>' +
    '<a href="/appointments" style="display:inline-block;padding:.6rem 1.5rem;background:rgba(20,184,166,.15);border:1px solid rgba(20,184,166,.4);border-radius:8px;color:var(--teal);font-size:.9rem;text-decoration:none;">← Back to Appointments</a>' +
    '</div>';
} else {
  init();
}"""

new = """} else if (!ROOM_NAME) {
  // APT_ID present but no room — try to fetch room_name from the API first
  // This handles old links and cases where room wasn't included in the URL
  (async function() {
    try {
      await fetch('/api/auth/refresh', { method: 'POST', credentials: 'include' });
      const _r = await fetch('/api/sessions/' + APT_ID, { credentials: 'include' });
      if (_r.ok) {
        const _info = await _r.json();
        const _roomName = _info.room_name || _info.session_room_name || '';
        const _status = _info.session_status || '';
        if (_roomName && _status === 'active') {
          // Session IS active — redirect with room param and continue
          const _newUrl = '/session?apt=' + encodeURIComponent(APT_ID) + '&room=' + encodeURIComponent(_roomName);
          window.location.replace(_newUrl);
          return;
        }
      }
    } catch(e) { /* fall through to error */ }
    // Truly not started — show the message
    document.getElementById('loading-text').textContent = 'Session not started yet…';
    document.getElementById('loading-screen').innerHTML =
      '<div style="text-align:center;padding:2rem;">' +
      '<div style="font-size:2rem;margin-bottom:1rem">⏳</div>' +
      '<div style="color:var(--text);font-size:1rem;margin-bottom:.5rem;font-weight:600;">Session not started yet</div>' +
      '<div style="color:var(--muted);font-size:.85rem;margin-bottom:1.5rem;">The ENP has not started this session yet. Please wait or ask the ENP to start the session.</div>' +
      '<a href="/appointments" style="display:inline-block;padding:.6rem 1.5rem;background:rgba(20,184,166,.15);border:1px solid rgba(20,184,166,.4);border-radius:8px;color:var(--teal);font-size:.9rem;text-decoration:none;">← Back to Appointments</a>' +
      '</div>';
  })();
} else {
  init();
}"""

if old in src:
    src = src.replace(old, new)
    with open('/var/www/quanby-legal/session.html', 'w', encoding='utf-8') as f:
        f.write(src)
    print('session.html patched — no-room case now auto-fetches room_name from API')
else:
    print('Pattern not found')
    idx = src.find('ROOM_NAME')
    print('ROOM_NAME at:', idx)
    print('Context:', src[max(0,idx-50):idx+200])
