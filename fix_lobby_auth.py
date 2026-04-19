with open('/var/www/quanby-legal/lobby.html', 'r', encoding='utf-8') as f:
    src = f.read()

# Fix 1: Add token refresh before navigation in joinNow()
old_join = '''async function joinNow() {
  if (!_locPassed || (!_livenessPassed && !_livenessBypassed)) return;
  const btn = document.getElementById('btn-join');
  btn.disabled = true; btn.textContent = '⏳ Entering session…';
  if (_previewStream) { _previewStream.getTracks().forEach(t => t.stop()); _previewStream = null; }
  const room = _sessionInfo.room_name || ROOM_NAME;
  location.href = GUEST_TOKEN
    ? `/session?room=${encodeURIComponent(room)}&apt=${encodeURIComponent(APT_ID)}&guest_token=${encodeURIComponent(GUEST_TOKEN)}&from_lobby=1`
    : `/session?room=${encodeURIComponent(room)}&apt=${encodeURIComponent(APT_ID)}&from_lobby=1`;
}'''

new_join = '''async function joinNow() {
  if (!_locPassed || (!_livenessPassed && !_livenessBypassed)) return;
  const btn = document.getElementById('btn-join');
  btn.disabled = true; btn.textContent = '⏳ Entering session…';
  if (_previewStream) { _previewStream.getTracks().forEach(t => t.stop()); _previewStream = null; }
  // Refresh token immediately before navigation so session.html auth check succeeds
  try { await fetch('/api/auth/refresh', { method: 'POST', credentials: 'include' }); } catch(e) {}
  const room = _sessionInfo.room_name || ROOM_NAME;
  location.href = GUEST_TOKEN
    ? `/session?room=${encodeURIComponent(room)}&apt=${encodeURIComponent(APT_ID)}&guest_token=${encodeURIComponent(GUEST_TOKEN)}&from_lobby=1`
    : `/session?room=${encodeURIComponent(room)}&apt=${encodeURIComponent(APT_ID)}&from_lobby=1`;
}'''

if old_join in src:
    src = src.replace(old_join, new_join)
    print('lobby.html: token refresh added to joinNow()')
else:
    print('joinNow pattern not found')

with open('/var/www/quanby-legal/lobby.html', 'w', encoding='utf-8') as f:
    f.write(src)

# Fix 2: session.html auth failure — show error instead of reloading (stops the loop)
with open('/var/www/quanby-legal/session.html', 'r', encoding='utf-8') as f:
    ses = f.read()

old_auth_fail = '''    if (!r.ok) { QLAuth._handleReauth(); return; }
    me = await r.json();
    _me = me;
  } catch(e) { console.warn('[Session] auth failed', e); QLAuth._handleReauth(); return; }'''

new_auth_fail = '''    if (!r.ok) {
      // Show visible error instead of reloading (prevents infinite reload loop)
      document.getElementById('loading-screen').innerHTML = [
        '<div style="text-align:center;padding:2rem;">',
        '<div style="font-size:2rem;margin-bottom:1rem">🔒</div>',
        '<div style="color:var(--text);font-size:1rem;margin-bottom:.5rem;font-weight:600;">Session Expired</div>',
        '<div style="color:var(--muted);font-size:.85rem;margin-bottom:1.5rem;">Your session expired. Please sign in again to join the meeting.</div>',
        '<a href="/?sso=1" style="display:inline-block;padding:.6rem 1.5rem;background:linear-gradient(135deg,#c9a84c,#e0c06a);color:#0a0e1a;font-weight:700;border-radius:8px;text-decoration:none;font-size:.9rem;">Sign In &rarr;</a>',
        '<div style="margin-top:.75rem;"><a href="/appointments" style="color:var(--teal);font-size:.85rem;">← Back to Appointments</a></div>',
        '</div>'
      ].join('');
      return;
    }
    me = await r.json();
    _me = me;
  } catch(e) {
    console.warn('[Session] auth failed', e);
    document.getElementById('loading-screen').innerHTML = [
      '<div style="text-align:center;padding:2rem;">',
      '<div style="font-size:2rem;margin-bottom:1rem">⚠️</div>',
      '<div style="color:var(--text);font-size:1rem;margin-bottom:.5rem;font-weight:600;">Authentication Error</div>',
      '<div style="color:var(--muted);font-size:.85rem;margin-bottom:1.5rem;">Could not verify your identity. Please try signing in again.</div>',
      '<a href="/?sso=1" style="display:inline-block;padding:.6rem 1.5rem;background:linear-gradient(135deg,#c9a84c,#e0c06a);color:#0a0e1a;font-weight:700;border-radius:8px;text-decoration:none;font-size:.9rem;">Sign In &rarr;</a>',
      '</div>'
    ].join('');
    return;
  }'''

if old_auth_fail in ses:
    ses = ses.replace(old_auth_fail, new_auth_fail)
    print('session.html: auth failure shows error instead of reloading')
else:
    print('session.html: auth fail pattern not found')

with open('/var/www/quanby-legal/session.html', 'w', encoding='utf-8') as f:
    f.write(ses)
print('Done')
