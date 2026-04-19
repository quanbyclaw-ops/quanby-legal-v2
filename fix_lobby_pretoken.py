with open('/var/www/quanby-legal/lobby.html', 'r', encoding='utf-8') as f:
    src = f.read()

old = '''async function doJoin() {
  const btn = document.getElementById('btn-join');
  btn.disabled = true;
  btn.innerHTML = '<div style="width:18px;height:18px;border:2px solid rgba(0,0,0,.2);border-top-color:#0a0e1a;border-radius:50%;animation:spin .7s linear infinite"></div> Entering…';

  // Stop camera before navigating
  if (_stream) { _stream.getTracks().forEach(t => t.stop()); _stream = null; }

  // Final refresh before navigation
  try { await fetch('/api/auth/refresh', { method: 'POST', credentials: 'include' }); } catch(e) {}

  const room = (_sessionInfo && _sessionInfo.room_name) ? _sessionInfo.room_name : ROOM_NAME;
  const url = GUEST_TK
    ? `/session?apt=${encodeURIComponent(APT_ID)}&room=${encodeURIComponent(room)}&guest_token=${encodeURIComponent(GUEST_TK)}&from_lobby=1`
    : `/session?apt=${encodeURIComponent(APT_ID)}&room=${encodeURIComponent(room)}&from_lobby=1`;

  window.location.href = url;
}'''

new = '''async function doJoin() {
  const btn = document.getElementById('btn-join');
  btn.disabled = true;
  btn.innerHTML = '<div style="width:18px;height:18px;border:2px solid rgba(0,0,0,.2);border-top-color:#0a0e1a;border-radius:50%;animation:spin .7s linear infinite"></div> Getting token…';

  // Stop camera before navigating
  if (_stream) { _stream.getTracks().forEach(t => t.stop()); _stream = null; }

  // Refresh token
  try { await fetch('/api/auth/refresh', { method: 'POST', credentials: 'include' }); } catch(e) {}

  const room = (_sessionInfo && _sessionInfo.room_name) ? _sessionInfo.room_name : ROOM_NAME;

  if (GUEST_TK) {
    // Guest: pass guest token directly
    window.location.href = `/session?apt=${encodeURIComponent(APT_ID)}&room=${encodeURIComponent(room)}&guest_token=${encodeURIComponent(GUEST_TK)}&from_lobby=1`;
    return;
  }

  // Pre-fetch LiveKit token HERE in the lobby while cookies are definitely fresh
  btn.innerHTML = '<div style="width:18px;height:18px;border:2px solid rgba(0,0,0,.2);border-top-color:#0a0e1a;border-radius:50%;animation:spin .7s linear infinite"></div> Joining…';
  try {
    const joinRes = await fetch('/api/sessions/join', {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ room_name: room, apt_id: APT_ID }),
    });
    if (!joinRes.ok) {
      const errData = await joinRes.json().catch(() => ({}));
      const errMsg = errData.detail || ('Join failed: HTTP ' + joinRes.status);
      document.getElementById('join-hint').textContent = '❌ ' + errMsg;
      document.getElementById('join-hint').style.color = '#f87171';
      btn.disabled = false;
      btn.innerHTML = '🎥 Join Session';
      return;
    }
    const jd = await joinRes.json();
    // Pass pre-fetched token to session.html via URL — no auth needed on arrival
    const url = `/session?apt=${encodeURIComponent(APT_ID)}&room=${encodeURIComponent(room)}&from_lobby=1&lk_token=${encodeURIComponent(jd.token)}&lk_user=${encodeURIComponent(jd.user_name)}&lk_role=${encodeURIComponent(jd.user_role)}`;
    window.location.href = url;
  } catch(e) {
    document.getElementById('join-hint').textContent = '❌ Network error. Try again.';
    document.getElementById('join-hint').style.color = '#f87171';
    btn.disabled = false;
    btn.innerHTML = '🎥 Join Session';
  }
}'''

if old in src:
    src = src.replace(old, new)
    with open('/var/www/quanby-legal/lobby.html', 'w', encoding='utf-8') as f:
        f.write(src)
    print('lobby.html: doJoin now pre-fetches LiveKit token')
else:
    print('Pattern not found')
