with open('/var/www/quanby-legal/appointments.html', 'r', encoding='utf-8') as f:
    src = f.read()

# 1. Add Quick Session button to ENP page header
old_header = '''<div class="page-header">
      <h1 id="page-title">Appointments</h1>
      <p id="page-sub"></p>
    </div>
    <!-- ENP Tabs -->
    <div id="enp-tabs" style="display:none;">'''

new_header = '''<div class="page-header" style="display:flex;align-items:flex-start;justify-content:space-between;flex-wrap:wrap;gap:1rem;">
      <div>
        <h1 id="page-title">Appointments</h1>
        <p id="page-sub"></p>
      </div>
      <!-- ENP Quick Session button (hidden for clients) -->
      <div id="quick-session-wrap" style="display:none;">
        <button onclick="createQuickSession(this)" style="display:inline-flex;align-items:center;gap:.5rem;background:linear-gradient(135deg,#c9a84c,#e0c06a);color:#0a0e1a;font-weight:800;font-size:.9rem;padding:.6rem 1.25rem;border:none;border-radius:8px;cursor:pointer;transition:opacity .15s;" onmouseover="this.style.opacity='.85'" onmouseout="this.style.opacity='1'">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><path d="M23 7l-7 5 7 5V7z"/><rect x="1" y="5" width="15" height="14" rx="2"/></svg>
          Quick Session
        </button>
        <div style="font-size:.7rem;color:var(--muted);text-align:center;margin-top:.3rem;">No appointment needed</div>
      </div>
    </div>
    <!-- ENP Tabs -->
    <div id="enp-tabs" style="display:none;">'''

if old_header in src:
    src = src.replace(old_header, new_header)
    print('Header updated with Quick Session button')
else:
    print('Header pattern not found')

# 2. Show quick-session-wrap for ENPs
old_role_check = '''  if (_user.role === 'client') {'''
# Find the ENP init section
old_enp_init = '''  if (_user.role === 'client') {
    document.getElementById('page-title').textContent = 'My Appointments';
    document.getElementById('page-sub').textContent = 'Track your notarization appointments';'''

new_enp_init_prefix = '''  // Show Quick Session button for ENPs only
  if (_user.role === 'attorney') {
    var _qsw = document.getElementById('quick-session-wrap');
    if (_qsw) _qsw.style.display = '';
  }

  if (_user.role === 'client') {
    document.getElementById('page-title').textContent = 'My Appointments';
    document.getElementById('page-sub').textContent = 'Track your notarization appointments';'''

if old_enp_init in src:
    src = src.replace(old_enp_init, new_enp_init_prefix)
    print('ENP role check updated')
else:
    print('ENP init pattern not found')

# 3. Add createQuickSession function before signOut
old_signout = '''async function signOut() {
  await fetch('/api/auth/logout', { method: 'POST', credentials: 'include' });
  window.location.href = '/';
}'''

new_signout = '''async function createQuickSession(btn) {
  btn.disabled = true;
  btn.innerHTML = '<div style="width:14px;height:14px;border:2px solid rgba(0,0,0,.2);border-top-color:#0a0e1a;border-radius:50%;animation:spin .7s linear infinite"></div> Starting…';

  try {
    // Refresh auth
    try { await fetch('/api/auth/refresh', { method: 'POST', credentials: 'include' }); } catch(e) {}

    // Create a dummy appointment for this quick session
    // We need an appointment ID — create one with the ENP as both parties
    const aptRes = await fetch('/api/quick-session', {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ mode: 'REN', notes: 'Quick session created by ENP' })
    });

    if (!aptRes.ok) {
      const err = await aptRes.json().catch(() => ({}));
      alert('Error: ' + (err.detail || 'Could not create session'));
      btn.disabled = false;
      btn.innerHTML = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><path d="M23 7l-7 5 7 5V7z"/><rect x="1" y="5" width="15" height="14" rx="2"/></svg> Quick Session';
      return;
    }

    const data = await aptRes.json();
    const aptId = data.apt_id;
    const roomName = data.room_name;
    const token = data.token;

    // Navigate directly to lobby with pre-fetched token
    try {
      sessionStorage.setItem('ql_lk_token', token);
      sessionStorage.setItem('ql_lk_user', _user.first_name + ' ' + (_user.last_name || ''));
      sessionStorage.setItem('ql_lk_role', 'ENP');
      sessionStorage.setItem('ql_lk_apt', aptId);
    } catch(e) {}

    window.location.href = '/session?apt=' + encodeURIComponent(aptId) + '&room=' + encodeURIComponent(roomName) + '&from_lobby=1&lk_token=' + encodeURIComponent(token) + '&lk_user=' + encodeURIComponent((_user.first_name||'') + ' ' + (_user.last_name||'')) + '&lk_role=ENP';

  } catch(e) {
    alert('Network error: ' + e.message);
    btn.disabled = false;
    btn.innerHTML = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><path d="M23 7l-7 5 7 5V7z"/><rect x="1" y="5" width="15" height="14" rx="2"/></svg> Quick Session';
  }
}

async function signOut() {
  await fetch('/api/auth/logout', { method: 'POST', credentials: 'include' });
  window.location.href = '/';
}'''

if old_signout in src:
    src = src.replace(old_signout, new_signout)
    print('createQuickSession function added')
else:
    print('signOut pattern not found')

with open('/var/www/quanby-legal/appointments.html', 'w', encoding='utf-8') as f:
    f.write(src)
print('appointments.html saved')
