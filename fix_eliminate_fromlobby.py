with open('/var/www/quanby-legal/session.html', 'r', encoding='utf-8') as f:
    src = f.read()

# Replace entire FROM_LOBBY block in init() with a simpler approach:
# If LK_TOKEN is in URL AND ROOM_NAME is set, connect directly
old_from_lobby = '''  // FROM_LOBBY fast-path — connects to LiveKit directly
  if (FROM_LOBBY) {
    setLoading('Joining meeting\u2026');
    console.log('[Session] FROM_LOBBY apt=' + APT_ID + ' room=' + ROOM_NAME + ' has_token=' + !!LK_TOKEN);
    try {
      // Step 1: Get token — use URL token if available, otherwise call join API
      var _lkToken = LK_TOKEN, _lkUser = LK_USER, _lkRole = LK_ROLE;

      if (!_lkToken) {
        console.log('[Session] No URL token \u2014 calling /api/sessions/join...');
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

      // Load session info now (non-critical for connection, needed for UI)
      fetch('/api/sessions/' + APT_ID, { credentials: 'include' })
        .then(function(r){ return r.ok ? r.json() : null; })
        .then(function(s){ if (s) { _sessionInfo = s; _currentAptId = APT_ID; restoreSessionDocuments(); renderParticipantsList(); populateSignPanel(_role === 'ENP'); } })
        .catch(function(e){ console.warn('[Session] session info load failed:', e); });

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

new_from_lobby = '''  // Direct join: if LK_TOKEN in URL, connect immediately without any auth check
  if (LK_TOKEN && ROOM_NAME && APT_ID) {
    console.log('[Session] Direct join with pre-fetched token. room=' + ROOM_NAME);
    setLoading('Joining meeting\u2026');
    try {
      var _role = LK_ROLE || 'ENP';
      var _uname = LK_USER || 'Participant';

      _room = new LivekitClient.Room({ adaptiveStream: true, dynacast: true });
      setupRoomEvents(_room, _uname, _role);

      console.log('[Session] Connecting to wss://quanby-lms-k4aq44qe.livekit.cloud ...');
      await _room.connect('wss://quanby-lms-k4aq44qe.livekit.cloud', LK_TOKEN, { autoSubscribe: true });
      console.log('[Session] Connected! state=' + _room.state);

      _room.remoteParticipants.forEach(function(p) {
        addParticipantTile(p);
        p.trackPublications.forEach(function(pub) {
          if (pub.track && pub.isSubscribed) attachTrack(pub.track, p);
        });
      });

      try { await _room.localParticipant.enableCameraAndMicrophone(); } catch(camErr) {
        console.warn('[Session] Camera/mic:', camErr.message);
      }

      // Load session info in background
      fetch('/api/sessions/' + APT_ID, { credentials: 'include' })
        .then(function(r) { return r.ok ? r.json() : null; })
        .then(function(s) {
          if (s) {
            _sessionInfo = s; _currentAptId = APT_ID;
            if (_sessionInfo) { restoreSessionDocuments(); renderParticipantsList(); populateSignPanel(_role === 'ENP'); }
          }
        }).catch(function() {});

      hideLoading();
      postJoinSetup(_uname, _role, _role);
      if (_role === 'ENP') loadDcToken();
    } catch(connectErr) {
      console.error('[Session] LiveKit error:', connectErr);
      showError('Connection error: ' + connectErr.message + '<br><br>Please <a href="/appointments" style="color:#00d4c8">go back to Appointments</a> and start a new session.');
    }
    return;
  }

  // FROM_LOBBY without token — do auth then join
  if (FROM_LOBBY) {
    try {
      try { await fetch('/api/auth/refresh', { method:'POST', credentials:'include' }); } catch(e) {}
      var _jr = await fetch('/api/sessions/join', {
        method: 'POST', credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ room_name: ROOM_NAME, apt_id: APT_ID })
      });
      if (!_jr.ok) {
        var _je = await _jr.json().catch(function(){return {};});
        showError((_je.detail || 'Could not join: ' + _jr.status) + '<br><a href="/appointments" style="color:#00d4c8">← Back</a>');
        return;
      }
      var _jd = await _jr.json();
      // Reload with token in URL
      window.location.replace('/session?apt=' + APT_ID + '&room=' + ROOM_NAME + '&from_lobby=1&lk_token=' + encodeURIComponent(_jd.token) + '&lk_user=' + encodeURIComponent(_jd.user_name||'') + '&lk_role=' + encodeURIComponent(_jd.user_role||''));
    } catch(e) {
      showError('Error: ' + e.message + '<br><a href="/appointments" style="color:#00d4c8">← Back</a>');
    }
    return;
  }'''

if old_from_lobby in src:
    src = src.replace(old_from_lobby, new_from_lobby)
    print('FROM_LOBBY block replaced with clean direct-join logic')
else:
    print('Pattern not found — length check:', len(old_from_lobby))
    # Find approximate location
    idx = src.find('FROM_LOBBY fast-path')
    print('FROM_LOBBY fast-path at index:', idx)
    if idx > 0:
        print('Context:', src[idx:idx+100])

with open('/var/www/quanby-legal/session.html', 'w', encoding='utf-8') as f:
    f.write(src)
print('Saved')
