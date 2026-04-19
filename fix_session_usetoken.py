with open('/var/www/quanby-legal/session.html', 'r', encoding='utf-8') as f:
    src = f.read()

# Add lk_token, lk_user, lk_role to URL params parsing
old_params = '''const params      = new URLSearchParams(location.search);
const ROOM_NAME      = params.get('room') || '';
const FROM_LOBBY     = params.get('from_lobby') === '1';
const APT_ID      = params.get('apt') || '';
const GUEST_TOKEN = params.get('guest_token') || '';'''

new_params = '''const params      = new URLSearchParams(location.search);
const ROOM_NAME      = params.get('room') || '';
const FROM_LOBBY     = params.get('from_lobby') === '1';
const APT_ID      = params.get('apt') || '';
const GUEST_TOKEN = params.get('guest_token') || '';
// Pre-fetched LiveKit token from lobby (avoids re-auth on session.html)
const LK_TOKEN    = params.get('lk_token') || '';
const LK_USER     = params.get('lk_user') || '';
const LK_ROLE     = params.get('lk_role') || '';'''

if old_params in src:
    src = src.replace(old_params, new_params)
    print('session.html: LK_TOKEN params added')
else:
    print('params pattern not found')

# Update FROM_LOBBY fast-path to use pre-fetched token if available
old_from_lobby = '''  // FROM_LOBBY fast-path
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

new_from_lobby = '''  // FROM_LOBBY fast-path
  if (FROM_LOBBY) {
    console.log('[Session] FROM_LOBBY=1 APT_ID=' + APT_ID + ' ROOM_NAME=' + ROOM_NAME + ' has_token=' + !!LK_TOKEN);

    // If lobby pre-fetched the LiveKit token, use it directly — no auth calls needed
    if (LK_TOKEN) {
      try {
        console.log('[Session] Using pre-fetched token, connecting to LiveKit...');
        setLoading('Joining meeting…');
        _room = new LivekitClient.Room({ adaptiveStream: true, dynacast: true });
        const _role = LK_ROLE || 'Client';
        const _uname = LK_USER || 'User';

        // Load session info in background for UI (non-blocking)
        fetch('/api/sessions/' + APT_ID, { credentials: 'include' })
          .then(function(r) { if (r.ok) return r.json(); })
          .then(function(s) { if (s) { _sessionInfo = s; _currentAptId = APT_ID; } })
          .catch(function() {});

        setupRoomEvents(_room, _uname, _role);
        await _room.connect('wss://quanby-lms-k4aq44qe.livekit.cloud', LK_TOKEN, { autoSubscribe: true });
        console.log('[Session] Connected! room state=' + _room.state);

        _room.remoteParticipants.forEach(function(participant) {
          addParticipantTile(participant);
          participant.trackPublications.forEach(function(pub) {
            if (pub.track && pub.isSubscribed) attachTrack(pub.track, participant);
          });
        });
        await _room.localParticipant.enableCameraAndMicrophone();
        hideLoading();
        postJoinSetup(_uname, _role, _role);
        if (_role === 'ENP') loadDcToken();
      } catch(e) {
        console.error('[Session] LiveKit connect failed:', e);
        showError('Could not connect to meeting: ' + (e.message || String(e)) + '. Please go back and try again.');
      }
      return;
    }

    // Fallback: no pre-fetched token, do full auth
    try {
      try { await fetch('/api/auth/refresh', { method: 'POST', credentials: 'include' }); } catch(e) {}
      const _fRes = await fetch('/api/auth/me', { credentials: 'include' });
      console.log('[Session] auth/me status:', _fRes.status);
      if (!_fRes.ok) {
        showError('Session expired. Please go back to Appointments and rejoin.');
        return;
      }
      const _fMe = await _fRes.json();
      _me = _fMe;
      const _sRes = await fetch('/api/sessions/' + APT_ID, { credentials: 'include' });
      if (!_sRes.ok) { showError('Session not found.'); return; }
      _sessionInfo = await _sRes.json();
      _currentAptId = APT_ID;
      if (_sessionInfo.session_status !== 'active') {
        showError('Session is not active. Please start the session from Appointments.');
        return;
      }
      const _isEnp = _fMe.id === _sessionInfo.enp_id;
      hideLoading();
      await joinSession(_fMe, _isEnp ? 'ENP' : 'Client');
    } catch(e) {
      console.error('[Session] FROM_LOBBY fallback error:', e);
      showError('Error: ' + (e.message || String(e)));
    }
    return;
  }'''

if old_from_lobby in src:
    src = src.replace(old_from_lobby, new_from_lobby)
    print('session.html: FROM_LOBBY uses pre-fetched token')
else:
    print('FROM_LOBBY pattern not found')

with open('/var/www/quanby-legal/session.html', 'w', encoding='utf-8') as f:
    f.write(src)
print('Done')
