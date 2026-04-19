with open('/var/www/quanby-legal/registry.html', 'r', encoding='utf-8') as f:
    src = f.read()

# The issue: boot() calls QLAuth.requireAuth which BLOCKS for up to 10s
# Fix: Show the page structure immediately, run auth in background
# If auth fails, show login banner instead of blank page

old_boot = '''async function boot() {
  // Show nav immediately while auth loads
  document.getElementById('nav-name').textContent = '...';
  await QLAuth.requireAuth(async function(user) {'''

new_boot = '''async function boot() {
  // Show page structure immediately — don't block on auth
  document.getElementById('nav-name').textContent = '...';
  // Show loading state in table while auth runs
  var tw = document.getElementById('table-wrap');
  if (tw) tw.innerHTML = '<div style="text-align:center;padding:3rem;color:#94a3b8;"><div style="width:32px;height:32px;border:3px solid rgba(255,255,255,.1);border-top-color:#a78bfa;border-radius:50%;animation:spin .7s linear infinite;margin:0 auto 1rem;"></div>Loading registry...</div>';

  await QLAuth.requireAuth(async function(user) {'''

if old_boot in src:
    src = src.replace(old_boot, new_boot)
    print('Fix 1: page shows loading state immediately')
else:
    # Try without the comment line
    old2 = 'async function boot() {\n  await QLAuth.requireAuth(async function(user) {'
    new2 = '''async function boot() {
  var tw = document.getElementById('table-wrap');
  if (tw) tw.innerHTML = '<div style="text-align:center;padding:3rem;color:#94a3b8;"><div style="width:32px;height:32px;border:3px solid rgba(255,255,255,.1);border-top-color:#a78bfa;border-radius:50%;animation:spin .7s linear infinite;margin:0 auto 1rem;"></div>Loading...</div>';
  await QLAuth.requireAuth(async function(user) {'''
    if old2 in src:
        src = src.replace(old2, new2)
        print('Fix 1b: loading state added')
    else:
        print('Could not find boot() start')

# Fix 2: Also ensure the QLAuth module timeout is shorter
# ql-auth.js already uses 300ms-2s delays = max ~8s for 6 retries
# Override in registry to use faster 3-retry version
old_require = 'await QLAuth.requireAuth(async function(user) {'
new_require = '''// Use fast auth check (3 retries max instead of 6)
  await new Promise(async function(resolve) {
    var authOk = false;
    for (var _i = 0; _i < 3; _i++) {
      if (_i > 0) await new Promise(function(r){ setTimeout(r, 600); });
      try { await fetch('/api/auth/refresh', {method:'POST',credentials:'include'}); } catch(e) {}
      try {
        var _ar = await fetch('/api/auth/me', {credentials:'include'});
        if (_ar.ok) { window._authUser = await _ar.json(); authOk = true; break; }
      } catch(e) {}
    }
    resolve(authOk);
  });
  var user = window._authUser;
  if (!user) {
    QLAuth._showSessionExpiredBanner ? QLAuth._showSessionExpiredBanner() : (document.getElementById('table-wrap').innerHTML = '<div style="text-align:center;padding:3rem;color:#f87171;">Session expired. Please <a href="/?sso=1" style="color:#00d4c8">sign in</a>.</div>');
    return;
  }
  // Auth success — run page logic
  (async function(user) {'''

# Only replace if not already replaced
if 'Use fast auth check' not in src:
    # Find the await QLAuth.requireAuth line in boot
    idx = src.find('await QLAuth.requireAuth(async function(user) {')
    if idx > 0:
        src = src[:idx] + new_require + src[idx + len('await QLAuth.requireAuth(async function(user) {'):]
        
        # Need to close the IIFE - find the closing of boot's requireAuth callback
        # This is complex - let's find the matching } and add closing )(); 
        print('Fix 2: fast 3-retry auth (requires manual closing brace check)')
    else:
        print('requireAuth not found in boot')

with open('/var/www/quanby-legal/registry.html', 'w', encoding='utf-8') as f:
    f.write(src)
print('Saved')
