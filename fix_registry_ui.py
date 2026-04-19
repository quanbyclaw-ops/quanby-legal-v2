with open('/var/www/quanby-legal/registry.html', 'r', encoding='utf-8') as f:
    src = f.read()

# Fix 1: empty state with sync button
old_empty = "      wrap.innerHTML = `<div class=\"empty-state\"><div class=\"icon\"><i class=\"hgi-stroke hgi-book-open-01\" style=\"font-size:2.5rem;color:var(--teal);\"></i></div><h3>No notarial acts yet</h3><p>Completed notarizations will appear here after sessions end.</p></div>`;"

new_empty = '''      wrap.innerHTML = [
        '<div class="empty-state">',
        '<div class="icon"><i class="hgi-stroke hgi-book-open-01" style="font-size:2.5rem;color:#00d4c8;"></i></div>',
        '<h3>No notarial acts yet</h3>',
        '<p>Completed notarizations will appear here after sessions are ended and all signers have signed.</p>',
        '<div style="margin-top:1.25rem;">',
        '<button onclick="triggerSyncAll()" id="sync-all-btn" style="background:rgba(0,212,200,.12);border:1px solid rgba(0,212,200,.35);color:#00d4c8;padding:.55rem 1.25rem;border-radius:8px;font-size:.85rem;font-weight:600;cursor:pointer;">',
        '<i class="hgi-stroke hgi-refresh" style="font-size:.85rem;vertical-align:middle;margin-right:.3rem;"></i>Sync All Ended Sessions',
        '</button>',
        '</div>',
        '<p style="margin-top:.75rem;font-size:.78rem;color:#64748b;">Only <strong>completed</strong> (fully signed) DoconChain documents appear here.</p>',
        '</div>'
      ].join('');'''

if old_empty in src:
    src = src.replace(old_empty, new_empty)
    print('Empty state updated')
else:
    # Try to find and fix it regardless
    idx = src.find('No notarial acts yet')
    print('Acts pattern at:', idx)

# Fix 2: add triggerSyncAll function if not present
if 'function triggerSyncAll' not in src:
    trigger_fn = '''
async function triggerSyncAll() {
  const btn = document.getElementById('sync-all-btn');
  if (btn) { btn.disabled = true; btn.innerHTML = '<i class="hgi-stroke hgi-loading-03" style="font-size:.85rem;vertical-align:middle;margin-right:.3rem;animation:spin .8s linear infinite;"></i>Syncing...'; }
  try {
    const res = await fetch('/api/registry/sync-all', { method: 'POST', credentials: 'include' });
    const data = await res.json();
    if (data.success) {
      setTimeout(function() { loadActs(1); }, 3000);
    }
  } catch(e) { console.warn('Sync error:', e); }
}
'''
    # Insert before the closing script tag / init function
    src = src.replace('async function init()', trigger_fn + 'async function init()')
    print('triggerSyncAll function added')

with open('/var/www/quanby-legal/registry.html', 'w', encoding='utf-8') as f:
    f.write(src)
print('registry.html saved')
