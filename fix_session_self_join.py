with open('/var/www/quanby-legal/session.html', 'r', encoding='utf-8') as f:
    ses = f.read()

old = '''  // FROM_LOBBY fast-path — token comes from URL (primary) or sessionStorage (fallback)
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

new = '''  // FROM_LOBBY fast-path — connects to LiveKit directly
  if (FROM_LOBBY) {
    setLoading('Joining meeting…');
    console.log('[Session] FROM_LOBBY apt=' + APT_ID + ' room=' + ROOM_NAME + ' has_token=' + !!LK_TOKEN);
    try {
      // Step 1: Get token — use URL token if available, otherwise call join API
      var _lkToken = LK_TOKEN, _lkUser = LK_USER, _lkRole = LK_ROLE;

      if (!_lkToken) {
        console.log('[Session] No URL token — calling /api/sessions/join...');
        // Refresh first
        try { await fetch('/api/auth/refresh', { method:'POST', credentials:'include' }); } catch(e) {}
        var _jr = await fetch('/api/sessions/join', {
          method: 'POST', credentials: 'include',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ room_name: ROOM_NAME, apt_id: APT_ID })
        });
        console.log('[Session] join API status:', _jr.status);
        if (!_jr.ok) {
          var _je = await _jr.json().catch(function(){return {};});
          showError((_je.detail || 'Could not join session ('+_jr.status+')') +
            '<br><br><a href="/appointments" style="color:var(--teal)">← Back to Appointments</a>');
          return;
        }
        var _jd = await _jr.json();
        _lkToken = _jd.token; _lkUser = _jd.user_name; _lkRole = _jd.user_role;
        console.log('[Session] Got token from API, user=' + _lkUser + ' role=' + _lkRole);
      }

      // Step 2: Load session info for UI
      try {
        var _si = await fetch('/api/sessions/' + APT_ID, { credentials: 'include' });
        if (_si.ok) { _sessionInfo = await _si.json(); _currentAptId = APT_ID; }
      } catch(e) { console.warn('[Session] session info non-fatal:', e); }

      // Step 3: Connect to LiveKit
      console.log('[Session] Connecting to LiveKit...');
      _room = new LivekitClient.Room({ adaptiveStream: true, dynacast: true });
      var _role = _lkRole || 'Client';
      var _uname = _lkUser || 'Participant';
      setupRoomEvents(_room, _uname, _role);
      await _room.connect('wss://quanby-lms-k4aq44qe.livekit.cloud', _lkToken, { autoSubscribe: true });
      console.log('[Session] LiveKit connected! state=' + _room.state);

      _room.remoteParticipants.forEach(function(p) {
        addParticipantTile(p);
        p.trackPublications.forEach(function(pub) {
          if (pub.track && pub.isSubscribed) attachTrack(pub.track, p);
        });
      });
      try { await _room.localParticipant.enableCameraAndMicrophone(); } catch(e) {
        console.warn('[Session] Camera/mic error (non-fatal):', e);
      }
      hideLoading();
      postJoinSetup(_uname, _role, _role);
      if (_role === 'ENP') loadDcToken();
    } catch(e) {
      console.error('[Session] Join error:', e);
      showError('Could not connect: ' + (e.message || String(e)) +
        '<br><br><a href="/appointments" style="color:var(--teal)">← Back to Appointments</a>');
    }
    return;
  }'''

if old in ses:
    ses = ses.replace(old, new)
    print('Replaced FROM_LOBBY block — now self-joins if no token in URL')
else:
    print('Pattern not found — trying regex replace')
    import re
    new_ses, n = re.subn(
        r'  // FROM_LOBBY fast-path.*?    return;\s+  \}',
        new,
        ses, count=1, flags=re.DOTALL
    )
    if n:
        ses = new_ses
        print('Replaced via regex')
    else:
        print('FAILED')

with open('/var/www/quanby-legal/session.html', 'w', encoding='utf-8') as f:
    f.write(ses)
print('Done')
