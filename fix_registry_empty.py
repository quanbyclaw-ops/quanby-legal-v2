with open('/var/www/quanby-legal/registry.html', 'r', encoding='utf-8') as f:
    src = f.read()

old = 'wrap.innerHTML = `<div class="empty-state"><div class="icon"><i class="hgi-stroke hgi-folder-01" style="font-size:2.5rem;color:#8b949e;"></i></div><h3>No acts found</h3><p>Completed notarial acts will appear here automatically after sessions end.</p></div>`;'

new_parts = [
    'var _emptyHtml = \'<div class="empty-state">\';',
    '_emptyHtml += \'<div class="icon"><i class="hgi-stroke hgi-book-open-01" style="font-size:2.5rem;color:#00d4c8;"></i></div>\';',
    '_emptyHtml += \'<h3>No notarial acts yet</h3>\';',
    '_emptyHtml += \'<p>Completed notarizations appear here after sessions are ended and all signers have signed.</p>\';',
    '_emptyHtml += \'<div style="margin-top:1.25rem;">\';',
    '_emptyHtml += \'<button onclick="triggerSyncAll()" id="sync-all-btn" style="background:rgba(0,212,200,.12);border:1px solid rgba(0,212,200,.35);color:#00d4c8;padding:.55rem 1.25rem;border-radius:8px;font-size:.85rem;font-weight:600;cursor:pointer;">\';',
    '_emptyHtml += \'<i class="hgi-stroke hgi-refresh" style="font-size:.85rem;vertical-align:middle;margin-right:.3rem;"></i>Sync All Ended Sessions\';',
    '_emptyHtml += \'</button></div>\';',
    '_emptyHtml += \'<p style="margin-top:.75rem;font-size:.78rem;color:#64748b;">Only <strong>fully signed</strong> DoconChain documents appear here.</p>\';',
    '_emptyHtml += \'</div>\';',
    'wrap.innerHTML = _emptyHtml;',
]
new = '\n      '.join(new_parts)

if old in src:
    src = src.replace(old, new)
    with open('/var/www/quanby-legal/registry.html', 'w', encoding='utf-8') as f:
        f.write(src)
    print('Empty state fixed with sync button')
else:
    print('Pattern not found - checking...')
    idx = src.find('No acts found')
    if idx > 0:
        print('Found "No acts found" at:', idx)
        print('Context:', src[max(0,idx-200):idx+300])
