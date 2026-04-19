with open('/var/www/quanby-legal/session.html', 'r', encoding='utf-8') as f:
    src = f.read()

old = '''async function init() {
  setLoading('Checking authentication…');

  // Guest flow (witness/observer via invite link)
  if (GUEST_TOKEN) {
    await startPrejoin(null, 'Guest', 'WITNESS');
    return;
  }

  // Auth check'''

new = '''async function init() {
  setLoading('Checking authentication…');

  // Guest flow (witness/observer via invite link)
  if (GUEST_TOKEN) {
    await startPrejoin(null, 'Guest', 'WITNESS');
    return;
  }

  // FROM_LOBBY fast-path: lobby already verified auth + session.
  // Do a quick auth/me with short timeout — if it fails, show error (not reload).
  if (FROM_LOBBY) {
    try {
      // Refresh once more then get user
      try { await fetch('/api/auth/refresh', { method: 'POST', credentials: 'include' }); } catch(e) {}
      const _fRes = await fetch('/api/auth/me', { credentials: 'include' });
      if (!_fRes.ok) {
        showError('Session expired. Please <a href="/appointments" style="color:var(--teal)">go back to Appointments</a> and rejoin.');
        return;
      }
      const _fMe = await _fRes.json();
      _me = _fMe;
      // Load session info
      const _sRes = await fetch('/api/sessions/' + APT_ID, { credentials: 'include' });
      if (!_sRes.ok) { showError('Session not found or not authorized.'); return; }
      _sessionInfo = await _sRes.json();
      _currentAptId = APT_ID;
      if (_sessionInfo.session_status !== 'active') {
        showError('Session is not active. Please start the session from your appointments page.');
        return;
      }
      const _isEnp = _fMe.id === _sessionInfo.enp_id;
      const _uRole = _isEnp ? 'ENP' : 'Client';
      hideLoading();
      await joinSession(_fMe, _uRole);
    } catch(e) {
      showError('Could not connect to session: ' + (e.message || 'unknown error'));
    }
    return;
  }

  // Auth check'''

if old in src:
    src = src.replace(old, new)
    with open('/var/www/quanby-legal/session.html', 'w', encoding='utf-8') as f:
        f.write(src)
    print('FROM_LOBBY fast-path injected')
else:
    print('Pattern not found')
    idx = src.find('async function init()')
    print('init() at:', idx)
    print('Context:', src[idx:idx+300])
