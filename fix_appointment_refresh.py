with open('/var/www/quanby-legal/backend/main.py', 'r', encoding='utf-8') as f:
    src = f.read()

old = '''@app.post("/api/appointments")
async def create_appointment(
    req: AppointmentCreateRequest,
    authorization: Optional[str] = Header(None),
    ql_access: Optional[str] = Cookie(default=None),
):
    """Client creates an appointment with an ENP."""
    user = get_current_user(authorization, ql_access)
    if not user:
        raise HTTPException(401, "Unauthorized")
    if user.get("role") != "client":
        raise HTTPException(403, "Only clients can book appointments")'''

new = '''@app.post("/api/appointments")
async def create_appointment(
    req: AppointmentCreateRequest,
    response: Response,
    authorization: Optional[str] = Header(None),
    ql_access: Optional[str] = Cookie(default=None),
    ql_refresh: Optional[str] = Cookie(default=None),
):
    """Client creates an appointment with an ENP."""
    user = get_current_user(authorization, ql_access)
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
    if user.get("role") != "client":
        raise HTTPException(403, "Only clients can book appointments")'''

if old in src:
    src = src.replace(old, new)
    with open('/var/www/quanby-legal/backend/main.py', 'w', encoding='utf-8') as f:
        f.write(src)
    print('Fixed: create_appointment has refresh fallback')
else:
    print('Pattern not found')
