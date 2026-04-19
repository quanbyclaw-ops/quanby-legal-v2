with open('/var/www/quanby-legal/session.html', 'r', encoding='utf-8') as f:
    src = f.read()

# ─── 1. Replace prejoin CSS with full lobby CSS ───────────────────────────────
old_css = '''.prejoin{
  position:fixed;inset:0;background:var(--bg);z-index:40;
  display:flex;align-items:center;justify-content:center;
}
.prejoin-card{
  background:var(--surface);border:1px solid rgba(201,168,76,.25);
  border-radius:16px;padding:2rem;max-width:480px;width:90%;text-align:center;
}
.prejoin-logo{font-size:2rem;margin-bottom:1rem}
.prejoin-title{font-size:1.3rem;font-weight:700;color:var(--gold);margin-bottom:.4rem}
.prejoin-sub{font-size:.85rem;color:var(--muted);margin-bottom:1.5rem;line-height:1.5}
.preview-video{
  width:100%;height:180px;background:#000;border-radius:8px;
  margin-bottom:1.2rem;object-fit:cover;
}
.preview-placeholder{
  width:100%;height:180px;background:#111;border-radius:8px;
  margin-bottom:1.2rem;display:flex;align-items:center;justify-content:center;
  font-size:2.5rem;color:var(--muted);
}
.btn-join-session{
  width:100%;padding:.75rem;background:var(--gold);color:#000;
  font-size:1rem;font-weight:700;border:none;border-radius:8px;cursor:pointer;
  transition:opacity .15s;margin-bottom:.6rem;
}
.btn-join-session:hover{opacity:.85}
.btn-join-session:disabled{opacity:.5;cursor:not-allowed}
.prejoin-devices{display:flex;gap:.5rem;justify-content:center;margin-bottom:1rem;flex-wrap:wrap}
.device-toggle{
  background:rgba(255,255,255,.07);border:1px solid rgba(255,255,255,.12);
  border-radius:6px;padding:.35rem .7rem;font-size:.78rem;color:var(--text);
  cursor:pointer;display:flex;align-items:center;gap:.3rem;
}
.device-toggle.off{background:rgba(239,68,68,.15);border-color:rgba(239,68,68,.3);color:var(--red)}'''

new_css = '''/* ── Lobby / Pre-join ────────────────────────────────────────────────────── */
.prejoin {
  position: fixed; inset: 0; background: var(--bg); z-index: 40;
  display: flex; align-items: center; justify-content: center;
  padding: 1rem;
}
.prejoin-inner {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1.5rem;
  max-width: 880px;
  width: 100%;
  background: var(--surface);
  border: 1px solid rgba(201,168,76,.2);
  border-radius: 20px;
  overflow: hidden;
  box-shadow: 0 24px 64px rgba(0,0,0,.5);
}
@media (max-width: 680px) {
  .prejoin-inner { grid-template-columns: 1fr; }
  .lobby-right { border-left: none !important; border-top: 1px solid rgba(255,255,255,.08); }
}
.lobby-left { padding: 1.75rem; display: flex; flex-direction: column; gap: 1rem; }
.lobby-right {
  padding: 1.75rem; display: flex; flex-direction: column; gap: 1rem;
  border-left: 1px solid rgba(255,255,255,.07);
  background: rgba(0,0,0,.15);
}
.lobby-header { margin-bottom: .25rem; }
.lobby-title {
  font-size: 1.1rem; font-weight: 800; color: var(--gold); margin: 0 0 .2rem;
  display: flex; align-items: center; gap: .5rem;
}
.lobby-subtitle { font-size: .8rem; color: var(--muted); margin: 0; line-height: 1.5; }
.preview-wrap {
  position: relative; background: #0a0a0a; border-radius: 12px;
  overflow: hidden; aspect-ratio: 16/9;
}
.preview-video {
  width: 100%; height: 100%; object-fit: cover; display: none;
}
.preview-placeholder {
  width: 100%; height: 100%;
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  gap: .5rem; color: var(--muted); font-size: .8rem;
}
.preview-placeholder i { font-size: 2.5rem; }
.preview-label {
  position: absolute; bottom: .5rem; left: .75rem;
  background: rgba(0,0,0,.7); color: #fff; font-size: .72rem; font-weight: 600;
  padding: .2rem .6rem; border-radius: 6px;
}
.device-row { display: flex; gap: .6rem; }
.device-toggle {
  flex: 1; background: rgba(255,255,255,.06); border: 1px solid rgba(255,255,255,.12);
  border-radius: 8px; padding: .5rem .6rem; font-size: .78rem; color: var(--text);
  cursor: pointer; display: flex; align-items: center; justify-content: center; gap: .35rem;
  transition: all .15s;
}
.device-toggle:hover { background: rgba(255,255,255,.1); }
.device-toggle.off { background: rgba(239,68,68,.15); border-color: rgba(239,68,68,.3); color: #f87171; }
.btn-join-session {
  width: 100%; padding: .85rem; background: linear-gradient(135deg, #c9a84c, #e0c06a);
  color: #0a0e1a; font-size: 1rem; font-weight: 800; border: none; border-radius: 10px;
  cursor: pointer; transition: opacity .15s; letter-spacing: .02em;
  display: flex; align-items: center; justify-content: center; gap: .5rem;
}
.btn-join-session:hover { opacity: .88; }
.btn-join-session:disabled { opacity: .45; cursor: not-allowed; }
/* Lobby right panel sections */
.lobby-section { margin-bottom: .25rem; }
.lobby-section-title {
  font-size: .68rem; font-weight: 700; text-transform: uppercase; letter-spacing: .1em;
  color: rgba(148,163,184,.6); margin: 0 0 .6rem; display: flex; align-items: center; gap: .4rem;
}
.lobby-session-info {
  background: rgba(201,168,76,.06); border: 1px solid rgba(201,168,76,.2);
  border-radius: 10px; padding: .85rem 1rem; display: flex; flex-direction: column; gap: .45rem;
}
.lobby-info-row { display: flex; gap: .5rem; align-items: flex-start; font-size: .82rem; }
.lobby-info-label { color: var(--muted); flex-shrink: 0; width: 80px; }
.lobby-info-val { color: var(--text); font-weight: 600; }
/* Participants */
.lobby-participants { display: flex; flex-direction: column; gap: .5rem; }
.lobby-participant {
  display: flex; align-items: center; gap: .75rem;
  background: rgba(255,255,255,.04); border: 1px solid rgba(255,255,255,.07);
  border-radius: 10px; padding: .6rem .85rem;
}
.lobby-p-avatar {
  width: 34px; height: 34px; border-radius: 50%; flex-shrink: 0;
  background: linear-gradient(135deg, #7c3aed, #9d5ff3);
  display: flex; align-items: center; justify-content: center;
  font-size: .78rem; font-weight: 700; color: #fff;
  overflow: hidden;
}
.lobby-p-info { flex: 1; min-width: 0; }
.lobby-p-name { font-size: .84rem; font-weight: 600; color: var(--text); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.lobby-p-role { font-size: .7rem; color: var(--muted); }
.lobby-p-status { font-size: .7rem; font-weight: 600; }
.lobby-p-status.joined { color: #34d399; }
.lobby-p-status.waiting { color: #f59e0b; }
/* Geo / IP check */
.lobby-checks { display: flex; flex-direction: column; gap: .4rem; }
.lobby-check {
  display: flex; align-items: center; gap: .6rem; font-size: .8rem;
  padding: .4rem .7rem; border-radius: 7px; background: rgba(255,255,255,.03);
}
.lobby-check i { font-size: .85rem; flex-shrink: 0; }
.lobby-check.ok { color: #34d399; }
.lobby-check.warn { color: #f59e0b; }
.lobby-check.loading { color: var(--muted); }
.lobby-check.fail { color: #f87171; }
/* ── end lobby ── */'''

if old_css in src:
    src = src.replace(old_css, new_css)
    print('Lobby CSS injected')
else:
    print('CSS pattern not found')

# ─── 2. Replace prejoin HTML ──────────────────────────────────────────────────
old_html = '''<!-- PRE-JOIN -->
<div class="prejoin" id="prejoin" style="display:none">
  <div class="prejoin-card">
    <div class="prejoin-logo"><i class="hgi-stroke hgi-scales" style="font-size:2rem;color:var(--gold);"></i></div>
    <div class="prejoin-title">Quanby Legal</div>
    <div class="prejoin-sub" id="prejoin-sub">You are about to join a notarization session.</div>
    <video class="preview-video" id="preview-video" autoplay muted playsinline style="display:none"></video>
    <div class="preview-placeholder" id="preview-placeholder"><i class="hgi-stroke hgi-camera-01" style="font-size:2.5rem;color:var(--muted);"></i></div>
    <div class="prejoin-devices">
      <button class="device-toggle" id="toggle-mic-pre"><i class="hgi-stroke hgi-mic-01" style="font-size:.85rem;vertical-align:middle;margin-right:.25rem;"></i>Mic On</button>
      <button class="device-toggle" id="toggle-cam-pre"><i class="hgi-stroke hgi-camera-01" style="font-size:.85rem;vertical-align:middle;margin-right:.25rem;"></i>Camera On</button>
    </div>
    <button class="btn-join-session" id="btn-join-session">Join Session</button>
  </div>
</div>'''

new_html = '''<!-- PRE-JOIN / LOBBY -->
<div class="prejoin" id="prejoin" style="display:none">
  <div class="prejoin-inner">

    <!-- LEFT: Camera Preview -->
    <div class="lobby-left">
      <div class="lobby-header">
        <p class="lobby-title"><i class="hgi-stroke hgi-scales" style="font-size:1.1rem;color:var(--gold);"></i> Quanby Legal</p>
        <p class="lobby-subtitle" id="prejoin-sub">You are about to join a notarization session.</p>
      </div>

      <div class="preview-wrap">
        <video class="preview-video" id="preview-video" autoplay muted playsinline></video>
        <div class="preview-placeholder" id="preview-placeholder">
          <i class="hgi-stroke hgi-camera-01"></i>
          <span>Camera preview</span>
        </div>
        <div class="preview-label" id="preview-label">You</div>
      </div>

      <div class="device-row">
        <button class="device-toggle" id="toggle-mic-pre">
          <i class="hgi-stroke hgi-mic-01" style="font-size:.85rem;"></i> Mic On
        </button>
        <button class="device-toggle" id="toggle-cam-pre">
          <i class="hgi-stroke hgi-camera-01" style="font-size:.85rem;"></i> Camera On
        </button>
      </div>

      <button class="btn-join-session" id="btn-join-session">
        <i class="hgi-stroke hgi-video-01" style="font-size:1rem;"></i> Join Session
      </button>
    </div>

    <!-- RIGHT: Session Info + Participants + Checks -->
    <div class="lobby-right">

      <!-- Session Details -->
      <div class="lobby-section">
        <div class="lobby-section-title">
          <i class="hgi-stroke hgi-document-01" style="font-size:.75rem;"></i> Session Details
        </div>
        <div class="lobby-session-info" id="lobby-session-info">
          <div class="lobby-info-row">
            <span class="lobby-info-label">Type</span>
            <span class="lobby-info-val" id="lobby-notarization-type">—</span>
          </div>
          <div class="lobby-info-row">
            <span class="lobby-info-label">ENP</span>
            <span class="lobby-info-val" id="lobby-enp-name">—</span>
          </div>
          <div class="lobby-info-row">
            <span class="lobby-info-label">Client</span>
            <span class="lobby-info-val" id="lobby-client-name">—</span>
          </div>
        </div>
      </div>

      <!-- Meeting Participants -->
      <div class="lobby-section" style="flex:1">
        <div class="lobby-section-title">
          <i class="hgi-stroke hgi-users-01" style="font-size:.75rem;"></i> Meeting Participants
        </div>
        <div class="lobby-participants" id="lobby-participants">
          <!-- Populated by JS -->
        </div>
      </div>

      <!-- Pre-Join Checks -->
      <div class="lobby-section">
        <div class="lobby-section-title">
          <i class="hgi-stroke hgi-shield-01" style="font-size:.75rem;"></i> Pre-Join Checks
        </div>
        <div class="lobby-checks">
          <div class="lobby-check loading" id="check-location">
            <i class="hgi-stroke hgi-location-01"></i>
            <span id="check-location-text">Checking location…</span>
          </div>
          <div class="lobby-check loading" id="check-ip">
            <i class="hgi-stroke hgi-wifi-01"></i>
            <span id="check-ip-text">Checking IP address…</span>
          </div>
          <div class="lobby-check loading" id="check-camera">
            <i class="hgi-stroke hgi-camera-01"></i>
            <span id="check-camera-text">Checking camera…</span>
          </div>
          <div class="lobby-check loading" id="check-mic">
            <i class="hgi-stroke hgi-mic-01"></i>
            <span id="check-mic-text">Checking microphone…</span>
          </div>
        </div>
      </div>

    </div><!-- /lobby-right -->
  </div><!-- /prejoin-inner -->
</div>'''

if old_html in src:
    src = src.replace(old_html, new_html)
    print('Lobby HTML injected')
else:
    print('HTML pattern not found')

# ─── 3. Replace startPrejoin function to populate lobby ───────────────────────
old_prejoin_fn = '''async function startPrejoin(me, userName, userRole) {
  setLoading('Preparing camera preview…');
  try {
    _previewStream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
    document.getElementById('preview-video').srcObject = _previewStream;
    document.getElementById('preview-video').style.display = '';
    document.getElementById('preview-placeholder').style.display = 'none';
  } catch(e) {
    // No camera — that's ok
  }
  hideLoading();
  document.getElementById('prejoin').style.display = 'flex';

  // Fill prejoin info
  const sub = document.getElementById('prejoin-sub');
  if (_sessionInfo) {
    const partner = (me && me.id === _sessionInfo.enp_id) ? _sessionInfo.client_name : _sessionInfo.enp_name;
    sub.textContent = `You're about to join the notarization session for ${_sessionInfo.notarization_type || 'document'} with ${partner || 'your partner'}.`;
  }

  // Device toggles
  document.getElementById('toggle-mic-pre').onclick = () => {
    _micEnabled = !_micEnabled;
    const btn = document.getElementById('toggle-mic-pre');
    btn.innerHTML = _micEnabled ? '<i class="hgi-stroke hgi-mic-01" style="font-size:.9rem;vertical-align:middle;margin-right:.3rem;"></i>Mic On' : '<i class="hgi-stroke hgi-mic-off-01" style="font-size:.85rem;vertical-align:middle;margin-right:.3rem;"></i>Mic Off';
    btn.className = 'device-toggle' + (_micEnabled ? '' : ' off');
    if (_previewStream) _previewStream.getAudioTracks().forEach(t => t.enabled = _micEnabled);
  };
  document.getElementById('toggle-cam-pre').onclick = () => {
    _camEnabled = !_camEnabled;
    const btn = document.getElementById('toggle-cam-pre');
    btn.innerHTML = _camEnabled ? '<i class="hgi-stroke hgi-camera-01" style="font-size:.9rem;vertical-align:middle;margin-right:.3rem;"></i>Camera On' : '<i class="hgi-stroke hgi-camera-off-01" style="font-size:.85rem;vertical-align:middle;margin-right:.3rem;"></i>Camera Off';
    btn.className = 'device-toggle' + (_camEnabled ? '' : ' off');
    if (_previewStream) _previewStream.getVideoTracks().forEach(t => t.enabled = _camEnabled);
  };

  document.getElementById('btn-join-session').onclick = () => joinSession(me, userRole);
}'''

new_prejoin_fn = r"""async function startPrejoin(me, userName, userRole) {
  setLoading('Preparing lobby…');

  // ── Populate session details ──────────────────────────────────────────────
  if (_sessionInfo) {
    const partner = (me && me.id === _sessionInfo.enp_id) ? _sessionInfo.client_name : _sessionInfo.enp_name;
    const sub = document.getElementById('prejoin-sub');
    if (sub) sub.textContent = 'Ready to join your notarization session.';
    const typeEl = document.getElementById('lobby-notarization-type');
    const enpEl  = document.getElementById('lobby-enp-name');
    const cliEl  = document.getElementById('lobby-client-name');
    if (typeEl) typeEl.textContent = (_sessionInfo.notarization_type || 'Notarization').replace(/_/g,' ');
    if (enpEl)  enpEl.textContent  = _sessionInfo.enp_name || '—';
    if (cliEl)  cliEl.textContent  = _sessionInfo.client_name || '—';
  }

  // ── Participants ──────────────────────────────────────────────────────────
  const pList = document.getElementById('lobby-participants');
  if (pList && _sessionInfo) {
    const all = [];
    if (_sessionInfo.enp_name)    all.push({ name: _sessionInfo.enp_name,    role: 'ENP',    email: _sessionInfo.enp_email    || '' });
    if (_sessionInfo.client_name) all.push({ name: _sessionInfo.client_name, role: 'Client', email: _sessionInfo.client_email || '' });
    (_sessionInfo.session_participants || []).forEach(function(p) {
      all.push({ name: p.name || 'Guest', role: p.role || 'Witness', email: p.email || '' });
    });
    pList.innerHTML = all.map(function(p) {
      const initials = (p.name || '?').split(' ').map(function(w){ return w[0]; }).join('').toUpperCase().slice(0,2);
      const isMe = me && (p.email.toLowerCase() === (me.email || '').toLowerCase());
      const bgColor = p.role === 'ENP' ? 'linear-gradient(135deg,#c9a84c,#e0c06a)' : 'linear-gradient(135deg,#7c3aed,#9d5ff3)';
      const textColor = p.role === 'ENP' ? '#0a0e1a' : '#fff';
      return '<div class="lobby-participant">' +
        '<div class="lobby-p-avatar" style="background:' + bgColor + ';color:' + textColor + '">' + initials + '</div>' +
        '<div class="lobby-p-info">' +
          '<div class="lobby-p-name">' + (p.name || 'Unknown') + (isMe ? ' <span style="font-size:.68rem;color:#a78bfa;">(You)</span>' : '') + '</div>' +
          '<div class="lobby-p-role">' + p.role + (p.email ? ' · ' + p.email : '') + '</div>' +
        '</div>' +
        '<div class="lobby-p-status ' + (isMe ? 'joined' : 'waiting') + '">' + (isMe ? '● Ready' : '○ Waiting') + '</div>' +
      '</div>';
    }).join('');
  }

  // ── Camera + Mic preview ──────────────────────────────────────────────────
  let camOk = false, micOk = false;
  try {
    _previewStream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
    const vid = document.getElementById('preview-video');
    const ph  = document.getElementById('preview-placeholder');
    if (vid && ph) { vid.srcObject = _previewStream; vid.style.display = ''; ph.style.display = 'none'; }
    const lbl = document.getElementById('preview-label');
    if (lbl) lbl.textContent = userName || 'You';
    camOk = true; micOk = true;
  } catch(e) {
    try {
      _previewStream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false });
      micOk = true;
    } catch(e2) {}
  }
  _setCheck('check-camera', camOk ? 'ok' : 'warn', camOk ? 'Camera ready' : 'No camera detected');
  _setCheck('check-mic',    micOk ? 'ok' : 'warn', micOk ? 'Microphone ready' : 'No microphone detected');

  // ── Geolocation ───────────────────────────────────────────────────────────
  if (navigator.geolocation) {
    navigator.geolocation.getCurrentPosition(
      function(pos) {
        const lat = pos.coords.latitude.toFixed(4);
        const lon = pos.coords.longitude.toFixed(4);
        _setCheck('check-location', 'ok', 'Location: ' + lat + ', ' + lon);
      },
      function() {
        _setCheck('check-location', 'warn', 'Location not available');
      },
      { timeout: 6000 }
    );
  } else {
    _setCheck('check-location', 'warn', 'Geolocation not supported');
  }

  // ── IP check ─────────────────────────────────────────────────────────────
  fetch('/api/sessions/my-ip', { credentials: 'include' })
    .then(function(r){ return r.json(); })
    .then(function(d){
      const ip = d.ip || 'unknown';
      _setCheck('check-ip', 'ok', 'IP: ' + ip);
    })
    .catch(function(){
      _setCheck('check-ip', 'warn', 'Could not detect IP');
    });

  hideLoading();
  document.getElementById('prejoin').style.display = 'flex';

  // ── Device toggles ────────────────────────────────────────────────────────
  document.getElementById('toggle-mic-pre').onclick = function() {
    _micEnabled = !_micEnabled;
    const btn = document.getElementById('toggle-mic-pre');
    btn.innerHTML = _micEnabled
      ? '<i class="hgi-stroke hgi-mic-01" style="font-size:.85rem;"></i> Mic On'
      : '<i class="hgi-stroke hgi-mic-off-01" style="font-size:.85rem;"></i> Mic Off';
    btn.className = 'device-toggle' + (_micEnabled ? '' : ' off');
    if (_previewStream) _previewStream.getAudioTracks().forEach(function(t){ t.enabled = _micEnabled; });
  };
  document.getElementById('toggle-cam-pre').onclick = function() {
    _camEnabled = !_camEnabled;
    const btn = document.getElementById('toggle-cam-pre');
    btn.innerHTML = _camEnabled
      ? '<i class="hgi-stroke hgi-camera-01" style="font-size:.85rem;"></i> Camera On'
      : '<i class="hgi-stroke hgi-camera-off-01" style="font-size:.85rem;"></i> Camera Off';
    btn.className = 'device-toggle' + (_camEnabled ? '' : ' off');
    if (_previewStream) _previewStream.getVideoTracks().forEach(function(t){ t.enabled = _camEnabled; });
  };

  document.getElementById('btn-join-session').onclick = function() { joinSession(me, userRole); };
}

function _setCheck(id, status, text) {
  var el = document.getElementById(id);
  if (!el) return;
  el.className = 'lobby-check ' + status;
  var icon = el.querySelector('i');
  var span = el.querySelector('span');
  if (span) span.textContent = text;
  if (icon) {
    var iconMap = {
      'check-location': status === 'ok' ? 'hgi-location-01' : (status === 'warn' ? 'hgi-location-off-01' : 'hgi-location-01'),
      'check-ip':       'hgi-wifi-01',
      'check-camera':   status === 'ok' ? 'hgi-camera-01' : 'hgi-camera-off-01',
      'check-mic':      status === 'ok' ? 'hgi-mic-01' : 'hgi-mic-off-01',
    };
    icon.className = 'hgi-stroke ' + (iconMap[id] || 'hgi-check-circle-01');
  }
}"""

if old_prejoin_fn in src:
    src = src.replace(old_prejoin_fn, new_prejoin_fn)
    print('startPrejoin replaced with lobby version')
else:
    print('startPrejoin pattern not found')

with open('/var/www/quanby-legal/session.html', 'w', encoding='utf-8') as f:
    f.write(src)
print('session.html saved')
