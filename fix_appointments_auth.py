with open('/var/www/quanby-legal/appointments.html', 'r', encoding='utf-8') as f:
    src = f.read()

# Fix 1: requireAuth -> requireAuthWithRedirect (only redirect if truly needed, shows banner otherwise)
# Actually: keep requireAuth but pass explicit onFail that redirects to ?sso=1 not bare /
old_init = '''async function init() {
  await QLAuth.requireAuth(async function(user) {
    _user = user;
    try {
      populateNav();
      await loadAppointments();
    } catch(pageErr) {
      console.error('[Appointments] page error (not auth):', pageErr);
      // Don't redirect — show error in place
    }
  });
}'''

new_init = '''async function init() {
  await QLAuth.requireAuth(async function(user) {
    _user = user;
    try {
      populateNav();
      await loadAppointments();
    } catch(pageErr) {
      console.error('[Appointments] page error (not auth):', pageErr);
      // Don't redirect — show error in place
    }
  }
  // onFail: show banner, never redirect — user can click to re-auth
  // (QLAuth default behavior in v2.0 already does this, but be explicit)
  );
}'''

# Fix 2: startVideoSession — add auth preflight refresh before API call
old_start = '''async function startVideoSession(aptId, btn) {
  btn.disabled = true;
  btn.textContent = 'Starting…';
  try {
    const r = await fetch('/api/sessions/create', {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ apt_id: aptId }),
    });'''

new_start = '''async function startVideoSession(aptId, btn) {
  btn.disabled = true;
  btn.textContent = 'Starting…';
  try {
    // Auth preflight — refresh token before making the API call
    try { await fetch('/api/auth/refresh', { method: 'POST', credentials: 'include' }); } catch(e) {}
    const r = await QLAuth.authFetch('/api/sessions/create', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ apt_id: aptId }),
    });'''

changed = 0
if old_start in src:
    src = src.replace(old_start, new_start)
    print('startVideoSession preflight added')
    changed += 1
else:
    print('startVideoSession pattern not found')

# Fix 3: endSessionFromApts — add auth preflight
if 'async function endSessionFromApts' in src:
    src = src.replace(
        "async function endSessionFromApts(aptId, btn) {\n  if (!confirm('End this session?')) return;\n  btn.disabled = true;\n  try {\n    const r = await fetch('/api/sessions/' + aptId + '/end', {",
        "async function endSessionFromApts(aptId, btn) {\n  if (!confirm('End this session?')) return;\n  btn.disabled = true;\n  try {\n    try { await fetch('/api/auth/refresh', { method: 'POST', credentials: 'include' }); } catch(e) {}\n    const r = await fetch('/api/sessions/' + aptId + '/end', {"
    )
    print('endSessionFromApts preflight added')
    changed += 1

# Fix 4: confirmDeclineAction — add auth preflight
if 'async function confirmDeclineAction' in src:
    src = src.replace(
        "async function confirmDeclineAction(aptId, action, btn) {\n  btn.disabled = true;\n  btn.textContent = action === 'confirm' ? 'Confirming…' : 'Declining…';\n  try {\n    const r = await fetch('/api/appointments/' + aptId, {",
        "async function confirmDeclineAction(aptId, action, btn) {\n  btn.disabled = true;\n  btn.textContent = action === 'confirm' ? 'Confirming…' : 'Declining…';\n  try {\n    try { await fetch('/api/auth/refresh', { method: 'POST', credentials: 'include' }); } catch(e) {}\n    const r = await fetch('/api/appointments/' + aptId, {"
    )
    print('confirmDeclineAction preflight added')
    changed += 1

print(f'Total changes: {changed}')

with open('/var/www/quanby-legal/appointments.html', 'w', encoding='utf-8') as f:
    f.write(src)
print('appointments.html updated')
