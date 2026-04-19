with open('/var/www/quanby-legal/session.html', 'r', encoding='utf-8') as f:
    src = f.read()

# Find init() start and end
init_start = src.find('// ─── INIT ────')
init_end = src.find('\nasync function startPrejoin(')

if init_start < 0 or init_end < 0:
    print('Could not find init boundaries')
    print('init_start:', init_start, 'init_end:', init_end)
else:
    print(f'Replacing init() from {init_start} to {init_end}')
    
    new_init = '''// ─── INIT ─────────────────────────────────────────────────────────────────────
async function init() {
  setLoading('Connecting to session\u2026');

  if (GUEST_TOKEN) {
    await startPrejoin(null, 'Guest', 'WITNESS');
    return;
  }

  if (!APT_ID) {
    showError('Missing appointment ID.');
    return;
  }

  // Step 1: Refresh auth token
  try { await fetch('/api/auth/refresh', { method: 'POST', credentials: 'include' }); } catch(e) {}

  // Step 2: Get LiveKit token — use URL token, or call join API
  var _lkToken = LK_TOKEN;
  var _lkUser = LK_USER || '';
  var _lkRole = LK_ROLE || 'Client';
  var _lkRoom = ROOM_NAME;

  if (!_lkToken) {
    setLoading('Getting token\u2026');
    try {
      var _jr = await fetch('/api/sessions/join', {
        method: 'POST', credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ room_name: _lkRoom, apt_id: APT_ID })
      });
      if (!_jr.ok) {
        var _je = await _jr.json().catch(function(){return{};});
        showError((_je.detail || 'Join failed: HTTP ' + _jr.status) + '<br><a href="/appointments" style="color:#00d4c8">Back to Appointments</a>');
        return;
      }
      var _jd = await _jr.json();
      _lkToken = _jd.token;
      _lkUser  = _jd.user_name || '';
      _lkRole  = _jd.user_role || 'Client';
      _lkRoom  = _jd.room_name || _lkRoom;
    } catch(e) {
      showError('Network error: ' + e.message + '<br><a href="/appointments" style="color:#00d4c8">Back</a>');
      return;
    }
  }

  // Step 3: Load session info (non-blocking UI data)
  var _sessionLoaded = false;
  fetch('/api/sessions/' + APT_ID, { credentials: 'include' })
    .then(function(r) { return r.ok ? r.json() : null; })
    .then(function(s) {
      if (s) {
        _sessionInfo = s;
        _currentAptId = APT_ID;
        _sessionLoaded = true;
      }
    }).catch(function(){});

  // Step 4: Connect to LiveKit
  setLoading('Connecting\u2026');
  try {
    _room = new LivekitClient.Room({ adaptiveStream: true, dynacast: true });
    setupRoomEvents(_room, _lkUser, _lkRole);
    await _room.connect('wss://quanby-lms-k4aq44qe.livekit.cloud', _lkToken, { autoSubscribe: true });

    _room.remoteParticipants.forEach(function(p) {
      addParticipantTile(p);
      p.trackPublications.forEach(function(pub) {
        if (pub.track && pub.isSubscribed) attachTrack(pub.track, p);
      });
    });

    try { await _room.localParticipant.enableCameraAndMicrophone(); } catch(e) {}

    hideLoading();
    postJoinSetup(_lkUser, _lkRole, _lkRole);
    if (_lkRole === 'ENP') loadDcToken();

    // Load session UI after connect
    setTimeout(function() {
      if (_sessionInfo) {
        try { restoreSessionDocuments(); renderParticipantsList(); populateSignPanel(_lkRole === 'ENP'); } catch(e) {}
      }
    }, 1000);

  } catch(e) {
    showError('LiveKit error: ' + e.message + '<br>Please <a href="/appointments" style="color:#00d4c8">start a new session</a>.');
  }
}

'''
    src = src[:init_start] + new_init + src[init_end + 1:]  # +1 to skip the leading \n
    
    with open('/var/www/quanby-legal/session.html', 'w', encoding='utf-8') as f:
        f.write(src)
    print('init() replaced successfully')
