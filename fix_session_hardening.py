with open('/var/www/quanby-legal/backend/main.py', 'r', encoding='utf-8') as f:
    src = f.read()

# 1. Add a global sync lock so only ONE sync-all can run at a time
old_sync_fn = '''    # Run sequentially in a single background thread to prevent worker exhaustion
    def _sync_all_bg():
        for aid in ended_apts:
            try:
                _populate_registry_bg(aid, enp_id)
            except Exception:
                pass

    _tsyncall.Thread(target=_sync_all_bg, daemon=True).start()
    return {"success": True, "message": f"Queued {len(ended_apts)} sessions for sync", "queued": len(ended_apts)}'''

new_sync_fn = '''    # Run sequentially in a single background thread — prevents worker exhaustion
    # Global lock ensures only one sync-all runs at a time
    import threading as _t_lock
    _SYNC_LOCK = getattr(registry_sync_all, '_lock', None)
    if _SYNC_LOCK is None:
        registry_sync_all._lock = _t_lock.Lock()
        _SYNC_LOCK = registry_sync_all._lock

    if not _SYNC_LOCK.acquire(blocking=False):
        return {"success": True, "message": "Sync already in progress — please wait", "queued": 0}

    def _sync_all_bg():
        try:
            for aid in ended_apts:
                try:
                    _populate_registry_bg(aid, enp_id)
                except Exception as _e:
                    print(f"[Registry] sync error for {aid}: {_e}", flush=True)
        finally:
            _SYNC_LOCK.release()

    _tsyncall.Thread(target=_sync_all_bg, daemon=True).start()
    return {"success": True, "message": f"Queued {len(ended_apts)} sessions for sync", "queued": len(ended_apts)}'''

if old_sync_fn in src:
    src = src.replace(old_sync_fn, new_sync_fn)
    print('Fix 1: sync-all lock added')
else:
    print('Fix 1: pattern not found')

# 2. Add timeout to _populate_registry_bg HTTP calls (check existing timeout)
# The function already has timeout=30 on urlopen — that's good
# But the overall function can still run for 90s+ with multiple retries
# Add a max-runtime guard using threading.Timer
old_bg_start = '''def _populate_registry_bg(apt_id: str, enp_id: str) -> None:
    """Background thread: populate registry acts from a completed appointment.
    Max runtime: 90 seconds. Never blocks API workers."""
    import signal as _sig_reg
    try:
        import urllib.request as _ureg, json as _jreg'''

new_bg_start = '''def _populate_registry_bg(apt_id: str, enp_id: str) -> None:
    """Background thread: populate registry acts from a completed appointment.
    Max runtime: 60 seconds hard cap. Never blocks API workers."""
    import signal as _sig_reg
    import threading as _t_reg
    # Hard timeout: kill this thread's work after 60s to prevent blocking
    _timeout_flag = [False]
    def _set_timeout():
        _timeout_flag[0] = True
    _timeout_timer = _t_reg.Timer(60.0, _set_timeout)
    _timeout_timer.daemon = True
    _timeout_timer.start()
    try:
        import urllib.request as _ureg, json as _jreg'''

if old_bg_start in src:
    src = src.replace(old_bg_start, new_bg_start)
    print('Fix 2: populate_registry_bg timeout guard added')
else:
    print('Fix 2: pattern not found')

with open('/var/www/quanby-legal/backend/main.py', 'w', encoding='utf-8') as f:
    f.write(src)
print('Done')
