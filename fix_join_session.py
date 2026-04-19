with open('/var/www/quanby-legal/session.html', 'r', encoding='utf-8') as f:
    src = f.read()

old_join = '''async function joinSession(me, userRole) {
  const btn = document.getElementById('btn-join-session');
  btn.disabled = true; btn.textContent = 'Connecting…';

  // Stop preview stream
  if (_previewStream) { _previewStream.getTracks().forEach(t => t.stop()); _previewStream = null; }

  document.getElementById('prejoin').style.display = 'none';
  setLoading('Connecting to session…');

  let token, userName, role;
  try {
    if (GUEST_TOKEN) {
      token    = GUEST_TOKEN;
      userName = 'Guest';
      role     = 'WITNESS';
    } else {
      // Use authoritative room_name from session info (not URL param) so both sides always land in same room
      const roomName = (_sessionInfo && _sessionInfo.room_name) ? _sessionInfo.room_name : ROOM_NAME;
      const r = await fetch('/api/sessions/join', {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ room_name: roomName, apt_id: APT_ID }),
      });
      if (!r.ok) { const e = await r.json(); showError(e.detail || 'Failed to join session.'); return; }
      const data = await r.json();
      token    = data.token;
      userName = data.user_name;
      role     = data.user_role;
    }
  } catch(e) { showError('Network error. Could not join session.'); return; }'''

new_join = '''async function joinSession(me, userRole) {
  const btn = document.getElementById('btn-join-session');
  btn.disabled = true;
  btn.innerHTML = '<div style="width:16px;height:16px;border:2px solid rgba(255,255,255,.3);border-top-color:#fff;border-radius:50%;animation:spin .7s linear infinite;display:inline-block;vertical-align:middle;margin-right:.5rem;"></div> Connecting…';

  // Preflight auth refresh — critical for InPrivate/fresh sessions
  try { await fetch('/api/auth/refresh', { method: 'POST', credentials: 'include' }); } catch(e) {}

  // Stop preview stream
  if (_previewStream) { _previewStream.getTracks().forEach(function(t){ t.stop(); }); _previewStream = null; }

  document.getElementById('prejoin').style.display = 'none';
  setLoading('Connecting to session…');

  function _restorePrejoin(errMsg) {
    // Don't redirect — show error on the prejoin and re-enable the button
    document.getElementById('prejoin').style.display = 'flex';
    hideLoading();
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = '🎥 Join Session';
    }
    if (errMsg) {
      var _errEl = document.createElement('div');
      _errEl.style.cssText = 'color:#f87171;font-size:.8rem;text-align:center;margin-top:.5rem;padding:.4rem .75rem;background:rgba(248,113,113,.1);border-radius:6px;';
      _errEl.textContent = '⚠️ ' + errMsg;
      var _joinBtn = document.getElementById('btn-join-session');
      if (_joinBtn && _joinBtn.parentNode) {
        var existing = _joinBtn.parentNode.querySelector('.join-err');
        if (existing) existing.remove();
        _errEl.className = 'join-err';
        _joinBtn.parentNode.insertBefore(_errEl, _joinBtn.nextSibling);
      }
    }
  }

  let token, userName, role;
  try {
    if (GUEST_TOKEN) {
      token    = GUEST_TOKEN;
      userName = 'Guest';
      role     = 'WITNESS';
    } else {
      // Use authoritative room_name from session info (not URL param)
      const roomName = (_sessionInfo && _sessionInfo.room_name) ? _sessionInfo.room_name : ROOM_NAME;
      // Use authFetch which auto-retries on 401 with token refresh
      const r = await QLAuth.authFetch('/api/sessions/join', {
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
      role     = data.user_role;
    }
  } catch(e) { _restorePrejoin('Network error. Please check your connection.'); return; }'''

if old_join in src:
    src = src.replace(old_join, new_join)
    print('joinSession patched — auth refresh + restore prejoin on error')
else:
    print('Pattern not found')

with open('/var/www/quanby-legal/session.html', 'w', encoding='utf-8') as f:
    f.write(src)
print('Done')
