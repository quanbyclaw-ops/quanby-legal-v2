with open('/var/www/quanby-legal/session.html', 'r', encoding='utf-8') as f:
    src = f.read()

# Find showError and replace with HTML-safe version
idx = src.find('function showError(msg) {')
if idx < 0:
    print('showError not found')
else:
    end = src.find('\n}', idx) + 2
    old_block = src[idx:end]
    print('Found showError block:', len(old_block), 'chars')
    new_block = '''function showError(msg) {
  var _ls = document.getElementById('loading-screen');
  if (!_ls) return;
  _ls.style.display = 'flex';
  var d = document.createElement('div');
  d.style.cssText = 'text-align:center;padding:2rem;max-width:500px;';
  d.innerHTML = '<div style="font-size:2.5rem;margin-bottom:1rem">&#x26A0;&#xFE0F;</div>' +
    '<div style="color:#f87171;font-size:.95rem;margin-bottom:1.25rem;line-height:1.6">' + msg + '</div>' +
    '<a href="/appointments" style="display:inline-block;padding:.5rem 1.25rem;background:rgba(20,184,166,.15);border:1px solid rgba(20,184,166,.4);border-radius:8px;color:#00d4c8;font-size:.9rem;text-decoration:none;">\u2190 Back to Appointments</a>';
  _ls.innerHTML = '';
  _ls.appendChild(d);
}'''
    src = src[:idx] + new_block + src[end:]
    with open('/var/www/quanby-legal/session.html', 'w', encoding='utf-8') as f:
        f.write(src)
    print('showError replaced - now renders HTML safely')
