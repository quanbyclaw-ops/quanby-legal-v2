with open('/var/www/quanby-legal/lobby.html', 'r', encoding='utf-8') as f:
    src = f.read()

# Fix 1: Add from_lobby=1 to the session URL
old_join = '''  location.href = GUEST_TOKEN
    ? `/session?room=${encodeURIComponent(room)}&apt=${encodeURIComponent(APT_ID)}&guest_token=${encodeURIComponent(GUEST_TOKEN)}`
    : `/session?room=${encodeURIComponent(room)}&apt=${encodeURIComponent(APT_ID)}`;'''

new_join = '''  location.href = GUEST_TOKEN
    ? `/session?room=${encodeURIComponent(room)}&apt=${encodeURIComponent(APT_ID)}&guest_token=${encodeURIComponent(GUEST_TOKEN)}&from_lobby=1`
    : `/session?room=${encodeURIComponent(room)}&apt=${encodeURIComponent(APT_ID)}&from_lobby=1`;'''

if old_join in src:
    src = src.replace(old_join, new_join)
    print('Fix 1: from_lobby=1 added to joinNow() URL')
else:
    print('Fix 1 pattern not found')

# Fix 2: Replace direct proxycheck.io call with our backend proxy (avoids CORS)
# Also make VPN check non-blocking — CORS failure should not block joining
old_proxy = '''  if (userIp && userIp !== 'unknown') {
    try {
      const d = await (await fetch(`https://proxycheck.io/v2/${userIp}?key=${PROXY_KEY}&vpn=1&asn=1`)).json();
      const entry = d[userIp] || {};
      if (entry.proxy === 'yes' || entry.vpn === 'yes' || entry.type === 'VPN') {
        markStep('step-vpn', 'fail', '❌ VPN or proxy detected');
        setLocState('fail', '❌ VPN Detected', 'Disable your VPN to join this session.');
        return;
      }
    } catch(e) {}
  }
  markStep('step-vpn', 'done', '✅ No VPN detected');'''

new_proxy = '''  if (userIp && userIp !== 'unknown') {
    try {
      // Use backend proxy to avoid CORS issues with proxycheck.io
      const _pcUrl = '/api/sessions/vpn-check?ip=' + encodeURIComponent(userIp);
      const _pcRes = await fetch(_pcUrl, { credentials: 'include' });
      if (_pcRes.ok) {
        const d = await _pcRes.json();
        if (d.is_vpn) {
          markStep('step-vpn', 'fail', '❌ VPN or proxy detected');
          setLocState('fail', '❌ VPN Detected', 'Disable your VPN to join this session.');
          return;
        }
      }
      // CORS or network error — non-blocking, allow to proceed
    } catch(e) { console.warn('[Lobby] VPN check skipped:', e); }
  }
  markStep('step-vpn', 'done', '✅ No VPN detected');'''

if old_proxy in src:
    src = src.replace(old_proxy, new_proxy)
    print('Fix 2: proxycheck CORS fixed — using backend proxy')
else:
    print('Fix 2 pattern not found')

with open('/var/www/quanby-legal/lobby.html', 'w', encoding='utf-8') as f:
    f.write(src)
print('lobby.html saved')
