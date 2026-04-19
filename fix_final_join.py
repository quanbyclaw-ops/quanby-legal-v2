import re

# ─── Fix 1: lobby.html — always put token in URL (most reliable) ──────────────
with open('/var/www/quanby-legal/lobby.html', 'r', encoding='utf-8') as f:
    lobby = f.read()

old_navigate = '''    // Store token in sessionStorage (avoids URL length limits with JWT)
    try {
      sessionStorage.setItem('ql_lk_token', jd.token);
      sessionStorage.setItem('ql_lk_user', jd.user_name || '');
      sessionStorage.setItem('ql_lk_role', jd.user_role || '');
      sessionStorage.setItem('ql_lk_apt', APT_ID);
    } catch(e) { console.warn('sessionStorage failed:', e); }
    const url = `/session?apt=${encodeURIComponent(APT_ID)}&room=${encodeURIComponent(room)}&from_lobby=1`;
    window.location.href = url;'''

new_navigate = '''    // Store in sessionStorage (fallback for browsers that support it)
    try {
      sessionStorage.setItem('ql_lk_token', jd.token);
      sessionStorage.setItem('ql_lk_user', jd.user_name || '');
      sessionStorage.setItem('ql_lk_role', jd.user_role || '');
      sessionStorage.setItem('ql_lk_apt', APT_ID);
    } catch(e) {}
    // Always put token in URL as primary method (most reliable)
    const url = `/session?apt=${encodeURIComponent(APT_ID)}&room=${encodeURIComponent(room)}&from_lobby=1&lk_token=${encodeURIComponent(jd.token)}&lk_user=${encodeURIComponent(jd.user_name||'')}&lk_role=${encodeURIComponent(jd.user_role||'')}`;
    window.location.href = url;'''

if old_navigate in lobby:
    lobby = lobby.replace(old_navigate, new_navigate)
    with open('/var/www/quanby-legal/lobby.html', 'w', encoding='utf-8') as f:
        f.write(lobby)
    print('lobby.html: token in URL (primary) + sessionStorage (fallback)')
else:
    print('lobby.html: pattern not found')

# ─── Fix 2: session.html — completely rewrite FROM_LOBBY to be bulletproof ────
with open('/var/www/quanby-legal/session.html', 'r', encoding='utf-8') as f:
    ses = f.read()

# Find and replace the entire FROM_LOBBY block
old_from_lobby_start = '''  // FROM_LOBBY fast-path
  if (FROM_LOBBY) {
    console.log('[Session] FROM_LOBBY=1 APT_ID=' + APT_ID + ' ROOM_NAME=' + ROOM_NAME + ' has_token=' + !!LK_TOKEN);

    // If lobby pre-fetched the LiveKit token, use it directly — no auth calls needed
    if (LK_TOKEN) {
      try {
        console.log('[Session] Using pre-fetched token, connecting to LiveKit...');
        setLoading('Joining meeting…');
        const _role = LK_ROLE || 'Client';
        const _uname = LK_USER || 'User';

        // Load session info BEFORE connecting (postJoinSetup needs it)
        console.log('[Session] Loading session info...');
        try {
          const _siRes = await fetch('/api/sessions/' + APT_ID, { credentials: 'include' });
          if (_siRes.ok) {
            _sessionInfo = await _siRes.json();
            _currentAptId = APT_ID;
            console.log('[Session] Session info loaded OK');
          } else {
            console.warn('[Session] Could not load session info, status=' + _siRes.status);
          }
        } catch(e) { console.warn('[Session] Session info fetch error:', e); }

        _room = new LivekitClient.Room({ adaptiveStream: true, dynacast: true });
        setupRoomEvents(_room, _uname, _role);
        console.log('[Session] Connecting to LiveKit...');
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

new_from_lobby = '''  // FROM_LOBBY fast-path — token comes from URL (primary) or sessionStorage (fallback)
  if (FROM_LOBBY) {
    console.log('[Session] FROM_LOBBY token=' + LK_TOKEN.slice(0,20) + '... user=' + LK_USER + ' role=' + LK_ROLE);
    if (!LK_TOKEN) {
      showError('No session token found. Please go back to the lobby and click Join Session again.');
      return;
    }
    setLoading('Joining meeting…');
    try {
      // Load session info (needed for postJoinSetup UI)
      try {
        const _si = await fetch('/api/sessions/' + APT_ID, { credentials: 'include' });
        if (_si.ok) { _sessionInfo = await _si.json(); _currentAptId = APT_ID; }
      } catch(e) { console.warn('[Session] session info fetch failed (non-fatal):', e); }

      console.log('[Session] Connecting to LiveKit room...');
      _room = new LivekitClient.Room({ adaptiveStream: true, dynacast: true });
      const _role = LK_ROLE || 'Client';
      const _uname = LK_USER || 'Participant';
      setupRoomEvents(_room, _uname, _role);
      await _room.connect('wss://quanby-lms-k4aq44qe.livekit.cloud', LK_TOKEN, { autoSubscribe: true });
      console.log('[Session] LiveKit connected! state=' + _room.state);

      _room.remoteParticipants.forEach(function(p) {
        addParticipantTile(p);
        p.trackPublications.forEach(function(pub) {
          if (pub.track && pub.isSubscribed) attachTrack(pub.track, p);
        });
      });

      try { await _room.localParticipant.enableCameraAndMicrophone(); } catch(e) {
        console.warn('[Session] Camera/mic failed:', e);
      }
      hideLoading();
      postJoinSetup(_uname, _role, _role);
      if (_role === 'ENP') loadDcToken();
    } catch(e) {
      console.error('[Session] Join failed:', e);
      showError('Could not connect to meeting: ' + (e.message || 'Unknown error') +
        '<br><br><a href="/appointments" style="color:var(--teal)">← Back to Appointments</a>');
    }
    return;
  }'''

if old_from_lobby_start in ses:
    ses = ses.replace(old_from_lobby_start, new_from_lobby)
    print('session.html: FROM_LOBBY rewritten cleanly')
else:
    print('session.html: FROM_LOBBY pattern not found — trying regex')
    # Try to find and replace using a looser match
    new_ses = re.sub(
        r'  // FROM_LOBBY fast-path.*?    return;\s+  \}',
        new_from_lobby,
        ses,
        count=1,
        flags=re.DOTALL
    )
    if new_ses != ses:
        ses = new_ses
        print('session.html: FROM_LOBBY replaced via regex')
    else:
        print('session.html: FAILED to replace FROM_LOBBY block')

with open('/var/www/quanby-legal/session.html', 'w', encoding='utf-8') as f:
    f.write(ses)
print('Done')
