with open('/var/www/quanby-legal/backend/main.py', 'r', encoding='utf-8') as f:
    src = f.read()

# Fix 1: Don't skip documents just because DC says they're not "completed" on staging
# If a session has ended, treat all its docs as notarized even if DC staging didn't update status
old_skip = '''                if dc_status != "completed" and not completed_at:
                    print(f'[Registry] Skip apt={apt_id} uuid={dc_uuid[:12]} status={dc_status} (not completed)', flush=True)
                    continue  # only insert completed documents'''

new_skip = '''                # Accept document if: DC says completed, OR the session itself has ended
                session_ended = bool(apt.get("session_ended_at") or apt.get("session_status") == "ended")
                if dc_status not in ("completed", "done", "signed") and not completed_at and not session_ended:
                    print(f'[Registry] Skip apt={apt_id} uuid={dc_uuid[:12]} status={dc_status} (not completed, session not ended)', flush=True)
                    continue
                if dc_status not in ("completed", "done", "signed") and not completed_at and session_ended:
                    # Session ended — treat as notarized even if DC staging didn't update
                    dc_status = "completed"
                    completed_at = apt.get("session_ended_at") or _dt.now(_tz.utc).isoformat()
                    print(f'[Registry] Accept apt={apt_id} uuid={dc_uuid[:12]} (session ended, overriding DC status)', flush=True)'''

if old_skip in src:
    src = src.replace(old_skip, new_skip)
    print('Fix 1: session-ended docs now included in registry')
else:
    print('Fix 1 pattern not found')

with open('/var/www/quanby-legal/backend/main.py', 'w', encoding='utf-8') as f:
    f.write(src)
