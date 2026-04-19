with open('/var/www/quanby-legal/lobby.html', 'r', encoding='utf-8') as f:
    src = f.read()

# 1. Enable button immediately on lobby load - checks are informational only
src = src.replace(
    '<button id="btn-join" disabled onclick="doJoin()">',
    '<button id="btn-join" onclick="doJoin()">'
)

# 2. Remove the disabled styling that makes it look greyed out
src = src.replace(
    '#btn-join:disabled{opacity:.35;cursor:not-allowed;background:var(--muted);color:var(--bg)}',
    '#btn-join:disabled{opacity:.55;cursor:not-allowed;}'
)

# 3. Set join hint to "Ready to join" immediately instead of "Running pre-join checks..."
src = src.replace(
    '<div id="join-hint">Running pre-join checks…</div>',
    '<div id="join-hint" style="color:#34d399;">✅ Ready to join — checks running in background</div>'
)

# 4. Remove the _locOk guard in checkReady — just update the UI hint, never block
old_checkready = '''function checkReady() {
  if (_locOk) {
    document.getElementById('btn-join').disabled = false;
    document.getElementById('join-hint').textContent = '✅ All checks passed — ready to join';
    document.getElementById('join-hint').style.color = '#34d399';
  }
}'''

new_checkready = '''function checkReady() {
  // Checks are informational only — button is always enabled
  if (_locOk) {
    document.getElementById('join-hint').textContent = '✅ All checks passed — ready to join';
    document.getElementById('join-hint').style.color = '#34d399';
  }
}'''

if old_checkready in src:
    src = src.replace(old_checkready, new_checkready)
    print('checkReady updated — no longer gates the button')
else:
    print('checkReady pattern not found')

# 5. Also remove the VPN block (just warn, don't disable join)
old_vpn_block = '''          if (v.is_vpn) {
            setCheck('chk-ip', 'fail', 'VPN detected — please disable it');
            document.getElementById('join-hint').textContent = '⚠️ Disable your VPN to join';
          } else {'''

new_vpn_block = '''          if (v.is_vpn) {
            setCheck('chk-ip', 'warn', 'VPN detected — this may be flagged');
            // VPN warning only — not blocking
          } else {'''

if old_vpn_block in src:
    src = src.replace(old_vpn_block, new_vpn_block)
    print('VPN check changed to warning-only')
else:
    print('VPN block pattern not found')

with open('/var/www/quanby-legal/lobby.html', 'w', encoding='utf-8') as f:
    f.write(src)
print('lobby.html saved')
