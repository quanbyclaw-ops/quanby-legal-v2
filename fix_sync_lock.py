with open('/var/www/quanby-legal/backend/main.py', 'r', encoding='utf-8') as f:
    src = f.read()

# Make sync-all sequential (one at a time) to prevent worker deadlock
old = '''    for aid in ended_apts:
        _tsyncall.Thread(
            target=_populate_registry_bg,
            args=(aid, enp_id),
            daemon=True,
        ).start()

    return {"success": True, "message": f"Syncing {len(ended_apts)} sessions", "queued": len(ended_apts)}'''

new = '''    # Run sequentially in a single background thread to prevent worker exhaustion
    def _sync_all_bg():
        for aid in ended_apts:
            try:
                _populate_registry_bg(aid, enp_id)
            except Exception:
                pass

    _tsyncall.Thread(target=_sync_all_bg, daemon=True).start()
    return {"success": True, "message": f"Queued {len(ended_apts)} sessions for sync", "queued": len(ended_apts)}'''

if old in src:
    src = src.replace(old, new)
    with open('/var/www/quanby-legal/backend/main.py', 'w', encoding='utf-8') as f:
        f.write(src)
    print('Fixed: sync-all now runs sequentially in one thread')
else:
    print('Pattern not found')
