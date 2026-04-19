with open('/var/www/quanby-legal/backend/main.py', 'r', encoding='utf-8') as f:
    src = f.read()

# Find join_session endpoint and add room recreation logic
old_join = '''    is_enp    = uid == apt.get("enp_id")
    user_role = "ENP" if is_enp else "Client"
    user_name = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip() or user_role
    # ALWAYS use authoritative room_name from DB — never trust client-supplied value
    room_name = apt.get("session_room_name") or req.room_name
    token     = _create_livekit_token(room_name, uid, user_name, can_publish=True)

    return {
        "token":     token,
        "url":       _LIVEKIT_URL,
        "room_name": room_name,
        "user_name": user_name,
        "user_role": user_role,
    }'''

new_join = '''    is_enp    = uid == apt.get("enp_id")
    user_role = "ENP" if is_enp else "Client"
    user_name = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip() or user_role
    # ALWAYS use authoritative room_name from DB — never trust client-supplied value
    room_name = apt.get("session_room_name") or req.room_name

    # If ENP is rejoining, optionally recreate the room (LiveKit rooms expire when empty)
    # We just issue a fresh token — LiveKit auto-creates the room on first join
    token     = _create_livekit_token(room_name, uid, user_name, can_publish=True)

    return {
        "token":     token,
        "url":       _LIVEKIT_URL,
        "room_name": room_name,
        "user_name": user_name,
        "user_role": user_role,
    }'''

# LiveKit actually auto-creates rooms when the first participant joins with a valid token
# The real issue was the error message wasn't helpful. The above is informational only.
# Let's also add a session/restart endpoint for ENP

restart_endpoint = '''
# ─── POST /api/sessions/{apt_id}/restart ──────────────────────────────────────

@app.post("/api/sessions/{apt_id}/restart")
async def restart_session(
    apt_id: str,
    authorization: Optional[str] = Header(None),
    ql_access: Optional[str] = Cookie(default=None),
):
    """ENP restarts a session — creates a new LiveKit room name."""
    user = get_current_user(authorization, ql_access)
    if not user:
        raise HTTPException(401, "Unauthorized")
    if user.get("role") != "attorney":
        raise HTTPException(403, "ENP only")

    with _apts_lock:
        _reload_appointments()
        apt = _appointments.get(apt_id)
        if not apt:
            raise HTTPException(404, "Appointment not found")
        if apt.get("enp_id") != user["id"]:
            raise HTTPException(403, "Not your appointment")

        # Create fresh room name with new timestamp
        ts        = int(time.time())
        room_name = f"ql-{apt_id[:8]}-{ts}"
        enp_name  = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip() or "ENP"
        token     = _create_livekit_token(room_name, user["id"], enp_name, can_publish=True)
        now_iso   = _dt.now(_tz.utc).isoformat()

        apt["session_room_name"]  = room_name
        apt["session_status"]     = "active"
        apt["session_created_at"] = now_iso
        apt["session_ended_at"]   = None
        apt["updated_at"]         = now_iso
        _appointments[apt_id]     = apt
        _save_appointments()

    return {
        "room_name":    room_name,
        "token":        token,
        "url":          _LIVEKIT_URL,
        "session_link": f"https://legal.quanbyai.com/session?room={room_name}&apt={apt_id}",
    }


'''

# Insert before POST /api/sessions/create
if '/api/sessions/{apt_id}/restart' not in src:
    src = src.replace(
        '@app.post("/api/sessions/create")',
        restart_endpoint + '@app.post("/api/sessions/create")'
    )
    print('Restart endpoint added')
else:
    print('Restart endpoint already exists')

with open('/var/www/quanby-legal/backend/main.py', 'w', encoding='utf-8') as f:
    f.write(src)
print('main.py saved')
