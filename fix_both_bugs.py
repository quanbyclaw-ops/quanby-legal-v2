import re

# ─── Fix 1: Registry — remove stray "return null;" outside function ─────────
with open('/var/www/quanby-legal/registry.html', 'r', encoding='utf-8') as f:
    reg = f.read()

# Find and remove the orphaned "return null;" that's between the variable declarations
# and the boot() function
old_stray = '''let debounceTimer = null;

// ─── Auth & Boot ──────────────────────────────────────────────────────────────

    return null;
  }
async function boot() {'''

new_clean = '''let debounceTimer = null;

// ─── Auth & Boot ──────────────────────────────────────────────────────────────
async function boot() {'''

if old_stray in reg:
    reg = reg.replace(old_stray, new_clean)
    print('Registry: stray return null removed')
else:
    # Try to find it with regex
    fixed = re.sub(r'(let debounceTimer = null;\s+// ─── Auth & Boot[^\n]*\n)\s+return null;\s+\}\n(async function boot)', r'\1\2', reg)
    if fixed != reg:
        reg = fixed
        print('Registry: stray return null removed (regex)')
    else:
        print('Registry: pattern not found — checking...')
        idx = reg.find('return null;')
        while idx >= 0:
            context = reg[max(0,idx-200):idx+100]
            if 'function' not in context[:-50]:  # return not inside a function
                print(f'  Orphaned return null at idx {idx}:')
                print(f'  Context: {context}')
            idx = reg.find('return null;', idx+1)

with open('/var/www/quanby-legal/registry.html', 'w', encoding='utf-8') as f:
    f.write(reg)
print('Registry saved')

# ─── Fix 2: session.html — null check for btn + fix FROM_LOBBY join call ────
with open('/var/www/quanby-legal/session.html', 'r', encoding='utf-8') as f:
    ses = f.read()

# Fix the joinSession function — btn can be null when FROM_LOBBY=1
old_btn = '''async function joinSession(me, userRole) {
  const btn = document.getElementById('btn-join-session');
  btn.disabled = true;
  btn.innerHTML = '<div style="width:16px;height:16px;border:2px solid rgba(255,255,255,.3);border-top-color:#fff;border-radius:50%;animation:spin .7s linear infinite;display:inline-block;vertical-align:middle;margin-right:.5rem;"></div> Connecting…';'''

new_btn = '''async function joinSession(me, userRole) {
  var btn = document.getElementById('btn-join-session');
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = '<div style="width:16px;height:16px;border:2px solid rgba(255,255,255,.3);border-top-color:#fff;border-radius:50%;animation:spin .7s linear infinite;display:inline-block;vertical-align:middle;margin-right:.5rem;"></div> Connecting…';
  }'''

if old_btn in ses:
    ses = ses.replace(old_btn, new_btn)
    print('session.html: btn null check added')
else:
    print('session.html: btn pattern not found')

# Fix _restorePrejoin to handle null btn
old_restore = '''  function _restorePrejoin(errMsg) {
    // Don't redirect — show error on the prejoin and re-enable the button
    document.getElementById('prejoin').style.display = 'flex';
    hideLoading();
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = '🎥 Join Session';
    }'''

new_restore = '''  function _restorePrejoin(errMsg) {
    // Don't redirect — show error on the prejoin and re-enable the button
    var _prejoinEl = document.getElementById('prejoin');
    if (_prejoinEl) _prejoinEl.style.display = 'flex';
    hideLoading();
    var _btnEl = document.getElementById('btn-join-session');
    if (_btnEl) {
      _btnEl.disabled = false;
      _btnEl.innerHTML = '🎥 Join Session';
    }'''

if old_restore in ses:
    ses = ses.replace(old_restore, new_restore)
    print('session.html: _restorePrejoin null checks added')
else:
    print('session.html: _restorePrejoin pattern not found')

# Fix FROM_LOBBY path — call joinSession with correct signature
# When FROM_LOBBY=1, session.html calls: await joinSession(userName, userRole)
# but joinSession(me, userRole) expects me=user object, not userName string
# The function doesn't actually USE me, so this is fine — but ensure prejoin is hidden
old_from_lobby = '''  if (FROM_LOBBY) {
    // Came from lobby — skip session.html\'s own pre-join screen, join directly
    const userName = isEnp ? _sessionInfo.enp_name : _sessionInfo.client_name;
    const userRole = isEnp ? \'ENP\' : \'Client\';
    await joinSession(userName, userRole);'''

new_from_lobby = '''  if (FROM_LOBBY) {
    // Came from lobby — skip session.html\'s own pre-join screen, join directly
    const userName = isEnp ? _sessionInfo.enp_name : _sessionInfo.client_name;
    const userRole = isEnp ? \'ENP\' : \'Client\';
    // Ensure prejoin is hidden (it should be, but safety check)
    var _pj = document.getElementById(\'prejoin\');
    if (_pj) _pj.style.display = \'none\';
    await joinSession(me, userRole);'''

if old_from_lobby in ses:
    ses = ses.replace(old_from_lobby, new_from_lobby)
    print('session.html: FROM_LOBBY path fixed')
else:
    print('session.html: FROM_LOBBY pattern not found — trying alternate')
    # Try without escaped quotes
    if "await joinSession(userName, userRole);" in ses:
        ses = ses.replace(
            "await joinSession(userName, userRole);",
            "var _pj2 = document.getElementById('prejoin'); if (_pj2) _pj2.style.display = 'none';\n    await joinSession(me, userRole);"
        )
        print('session.html: FROM_LOBBY path fixed (alternate)')

with open('/var/www/quanby-legal/session.html', 'w', encoding='utf-8') as f:
    f.write(ses)
print('session.html saved')
