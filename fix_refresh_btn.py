with open('/var/www/quanby-legal/registry.html', 'r', encoding='utf-8') as f:
    src = f.read()

# Change Refresh button to auto-sync first
old_btn = '<button class="btn btn-primary" onclick="loadActs(1)"><i class="hgi-stroke hgi-refresh" style="font-size:.9rem;vertical-align:middle;margin-right:.3rem;"></i>Refresh</button>'
new_btn = '<button class="btn btn-primary" onclick="syncAndRefresh(this)" id="refresh-btn"><i class="hgi-stroke hgi-refresh" style="font-size:.9rem;vertical-align:middle;margin-right:.3rem;"></i>Refresh</button>'

if old_btn in src:
    src = src.replace(old_btn, new_btn)
    print('Refresh button updated')

# Add syncAndRefresh function
if 'function syncAndRefresh' not in src:
    fn = (
        '\nasync function syncAndRefresh(btn) {\n'
        '  if (btn) { btn.disabled=true; btn.innerHTML=\'<i class="hgi-stroke hgi-loading-03" style="font-size:.9rem;vertical-align:middle;margin-right:.3rem;animation:spin .7s linear infinite"></i>Syncing...\'; }\n'
        '  try { await fetch(\'/api/registry/sync-all\', { method:\'POST\', credentials:\'include\' }); } catch(e) {}\n'
        '  await new Promise(function(resolve){ setTimeout(resolve, 2500); });\n'
        '  await loadActs(1);\n'
        '  if (btn) { btn.disabled=false; btn.innerHTML=\'<i class="hgi-stroke hgi-refresh" style="font-size:.9rem;vertical-align:middle;margin-right:.3rem;"></i>Refresh\'; }\n'
        '}\n\n'
    )
    src = src.replace('async function syncAllSessions()', fn + 'async function syncAllSessions()')
    print('syncAndRefresh function added')

with open('/var/www/quanby-legal/registry.html', 'w', encoding='utf-8') as f:
    f.write(src)
print('Done')
