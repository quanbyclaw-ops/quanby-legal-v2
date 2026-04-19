with open('/var/www/quanby-legal/backend/main.py', 'r', encoding='utf-8') as f:
    src = f.read()

quick_session_endpoint = '''
# ─── POST /api/quick-session ─────────────────────────────────────────────────

@app.post("/api/quick-session")
async def create_quick_session(
    request: Request,
    response: Response,
    authorization: Optional[str] = Header(None),
    ql_access: Optional[str] = Cookie(default=None),
    ql_refresh: Optional[str] = Cookie(default=None),
):
    """ENP-only: Create an instant session without a client appointment.
    Returns a LiveKit token and room name — ENP can share the session link with anyone.
    """
    user = get_current_user(authorization, ql_access)
    # Inline refresh fallback
    if not user and ql_refresh:
        from auth import verify_refresh_token, create_access_token
        rp = verify_refresh_token(ql_refresh)
        if rp:
            _ru = get_user(rp.get("user_id", ""))
            if _ru:
                user = _ru
                _nt = create_access_token({"user_id": _ru["id"], "email": _ru.get("email", "")})
                response.set_cookie(key=_ACCESS_COOKIE, value=_nt, httponly=True,
                    secure=_COOKIE_SECURE, samesite=_COOKIE_SAMESITE, max_age=7*24*3600, path="/")
    if not user:
        raise HTTPException(401, "Unauthorized")
    if user.get("role") != "attorney":
        raise HTTPException(403, "ENP only")

    enp_name = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip() or "ENP"
    ts = int(time.time())
    apt_id = str(uuid.uuid4())
    room_name = f"ql-quick-{apt_id[:8]}-{ts}"
    now_iso = _dt.now(_tz.utc).isoformat()

    # Create a minimal appointment record
    apt = {
        "apt_id": apt_id,
        "client_id": user["id"],       # ENP is also the host
        "client_name": enp_name,
        "client_email": user.get("email", ""),
        "enp_id": user["id"],
        "enp_name": enp_name,
        "enp_email": user.get("email", ""),
        "notarization_type": "ACKNOWLEDGMENT",
        "mode": "REN",
        "notes": "Quick session — no appointment required",
        "title": f"Quick Session by {enp_name}",
        "preferred_time": "",
        "status": "CONFIRMED",
        "session_status": "active",
        "session_room_name": room_name,
        "session_created_at": now_iso,
        "session_ended_at": None,
        "session_participants": [],
        "session_documents": [],
        "created_at": now_iso,
        "updated_at": now_iso,
        "confirmed_at": now_iso,
        "doconchain_project_uuid": None,
        "doconchain_sign_link": None,
        "is_quick_session": True,
    }

    with _apts_lock:
        _appointments[apt_id] = apt
        _save_appointments()

    # Generate LiveKit token for ENP
    token = _create_livekit_token(room_name, user["id"], enp_name, can_publish=True)

    # Build shareable join link for guests
    guest_token = _create_livekit_token(room_name, f"guest-{uuid.uuid4().hex[:8]}", "Guest", can_publish=True)
    join_link = f"https://legal.quanbyai.com/session?apt={apt_id}&room={room_name}&from_lobby=1"

    return {
        "success": True,
        "apt_id": apt_id,
        "room_name": room_name,
        "token": token,
        "url": _LIVEKIT_URL,
        "join_link": join_link,
        "guest_token": guest_token,
        "enp_name": enp_name,
    }


'''

# Insert before /api/sessions/create
target = '@app.post("/api/sessions/create")'
if target in src and '/api/quick-session' not in src:
    src = src.replace(target, quick_session_endpoint + target)
    print('Quick session endpoint added')
elif '/api/quick-session' in src:
    print('Already exists')
else:
    print('Target not found')

with open('/var/www/quanby-legal/backend/main.py', 'w', encoding='utf-8') as f:
    f.write(src)
print('main.py saved')
