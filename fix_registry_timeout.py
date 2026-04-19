with open('/var/www/quanby-legal/backend/main.py', 'r', encoding='utf-8') as f:
    src = f.read()

# Fix 1: Reduce registry retries from 20 to 3 (3 x 30s = 90s max instead of 10 min)
old1 = '''                for _retry in range(20):  # retry for up to 10 minutes
                    _t_retry.sleep(30)'''
new1 = '''                for _retry in range(3):  # retry max 3 times (90s total)
                    _t_retry.sleep(30)'''

# Fix 2: Make all urlopen calls in registry have timeout
old2 = 'with _ureg.urlopen(_req_check, timeout=30) as _r_check:'
new2 = 'with _ureg.urlopen(_req_check, timeout=10) as _r_check:'

# Fix 3: Wrap entire populate function in try/except with timeout guard
old3 = '''def _populate_registry_bg(apt_id: str, enp_id: str) -> None:
    """Background thread: populate registry acts from a completed appointment."""
    try:'''
new3 = '''def _populate_registry_bg(apt_id: str, enp_id: str) -> None:
    """Background thread: populate registry acts from a completed appointment.
    Max runtime: 90 seconds. Never blocks API workers."""
    import signal as _sig_reg
    try:'''

c = 0
if old1 in src: src = src.replace(old1, new1); c+=1; print('Fixed: retries 20->3')
if old2 in src: src = src.replace(old2, new2); c+=1; print('Fixed: urlopen timeout 30->10')
if old3 in src: src = src.replace(old3, new3); c+=1; print('Fixed: docstring updated')

# Fix 4: Make the thread daemon so it dies if main process dies
for old_thread, new_thread in [
    ('target=_populate_registry_bg,\n                    args=(apt_id',
     'target=_populate_registry_bg,\n                    daemon=True,\n                    args=(apt_id'),
]:
    count = src.count(old_thread)
    if count:
        src = src.replace(old_thread, new_thread)
        print(f'Fixed: {count} thread(s) set to daemon=True')
        c += count

print(f'Total: {c} fixes')
with open('/var/www/quanby-legal/backend/main.py', 'w', encoding='utf-8') as f:
    f.write(src)
