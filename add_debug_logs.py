with open('/var/www/quanby-legal/session.html', 'r', encoding='utf-8') as f:
    src = f.read()

old = '''  // FROM_LOBBY fast-path: lobby already verified auth + session.
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
  }'''

new = '''  // FROM_LOBBY fast-path
  if (FROM_LOBBY) {
    console.log('[Session] FROM_LOBBY=1 detected, APT_ID=' + APT_ID + ' ROOM_NAME=' + ROOM_NAME);
    try {
      console.log('[Session] Step 1: refreshing token...');
      try {
        const _ref = await fetch('/api/auth/refresh', { method: 'POST', credentials: 'include' });
        console.log('[Session] refresh status:', _ref.status);
      } catch(e) { console.warn('[Session] refresh fetch failed:', e); }

      console.log('[Session] Step 2: fetching /api/auth/me...');
      const _fRes = await fetch('/api/auth/me', { credentials: 'include' });
      console.log('[Session] auth/me status:', _fRes.status);
      if (!_fRes.ok) {
        const _fText = await _fRes.text();
        console.error('[Session] auth/me FAILED body:', _fText);
        showError('Session expired (HTTP ' + _fRes.status + '). Please go back to Appointments and rejoin.');
        return;
      }
      const _fMe = await _fRes.json();
      console.log('[Session] auth/me OK, user:', _fMe.email, 'role:', _fMe.role);
      _me = _fMe;

      console.log('[Session] Step 3: fetching /api/sessions/' + APT_ID);
      const _sRes = await fetch('/api/sessions/' + APT_ID, { credentials: 'include' });
      console.log('[Session] session status:', _sRes.status);
      if (!_sRes.ok) {
        const _sText = await _sRes.text();
        console.error('[Session] sessions API FAILED body:', _sText);
        showError('Session not found (HTTP ' + _sRes.status + ').');
        return;
      }
      _sessionInfo = await _sRes.json();
      console.log('[Session] session_status:', _sessionInfo.session_status, 'room_name:', _sessionInfo.room_name);
      _currentAptId = APT_ID;

      if (_sessionInfo.session_status !== 'active') {
        showError('Session is not active (status: ' + _sessionInfo.session_status + '). The ENP must start the session first.');
        return;
      }

      const _isEnp = _fMe.id === _sessionInfo.enp_id;
      const _uRole = _isEnp ? 'ENP' : 'Client';
      console.log('[Session] Step 4: calling joinSession, isENP=' + _isEnp + ' role=' + _uRole);
      hideLoading();
      await joinSession(_fMe, _uRole);
      console.log('[Session] joinSession returned successfully');
    } catch(e) {
      console.error('[Session] FROM_LOBBY fast-path threw:', e);
      showError('Error joining session: ' + (e.message || String(e)));
    }
    return;
  }'''

if old in src:
    src = src.replace(old, new)
    with open('/var/www/quanby-legal/session.html', 'w', encoding='utf-8') as f:
        f.write(src)
    print('Debug logs injected into FROM_LOBBY path')
else:
    print('Pattern not found — checking...')
    idx = src.find('FROM_LOBBY fast-path')
    print('Found at:', idx)
    if idx > 0:
        print('Context:', src[idx:idx+300])
