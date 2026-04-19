with open('/var/www/quanby-legal/session.html', 'r', encoding='utf-8') as f:
    ses = f.read()

old = '''        setLoading('Joining meeting…');
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
        if (_role === 'ENP') loadDcToken();'''

new = '''        setLoading('Joining meeting…');
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
        if (_role === 'ENP') loadDcToken();'''

if old in ses:
    ses = ses.replace(old, new)
    with open('/var/www/quanby-legal/session.html', 'w', encoding='utf-8') as f:
        f.write(ses)
    print('Fixed: session info loaded before LiveKit connect')
else:
    print('Pattern not found')
