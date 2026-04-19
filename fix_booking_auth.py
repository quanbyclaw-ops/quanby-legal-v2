# Fix 1: Frontend — add refresh before booking call
with open('/var/www/quanby-legal/browse.html', 'r', encoding='utf-8') as f:
    browse = f.read()

old_submit = '''  try {
    const r = await fetch('/api/appointments', {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },'''

new_submit = '''  try {
    // Preflight refresh to ensure fresh token before booking
    try { await fetch('/api/auth/refresh', { method: 'POST', credentials: 'include' }); } catch(e) {}
    const r = await fetch('/api/appointments', {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },'''

if old_submit in browse:
    browse = browse.replace(old_submit, new_submit)
    with open('/var/www/quanby-legal/browse.html', 'w', encoding='utf-8') as f:
        f.write(browse)
    print('browse.html: preflight refresh added to submitBooking')
else:
    print('browse.html: pattern not found')

# Fix 2: Backend — add ql_refresh fallback to create_appointment
with open('/var/www/quanby-legal/backend/main.py', 'r', encoding='utf-8') as f:
    src = f.read()

old_apt = '''@app.post("/api/appointments")
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

new_apt = '''@app.post("/api/appointments")
async def create_appointment(
    req: AppointmentCreateRequest,
    response: Response,
    authorization: Optional[str] = Header(None),
    ql_access: Optional[str] = Cookie(default=None),
    ql_refresh: Optional[str] = Cookie(default=None),
):
    """Client creates an appointment with an ENP."""
    user = get_current_user(authorization, ql_access)
    # Inline refresh fallback — handles cases where ql_access cookie expired
    if not user and ql_refresh:
        from auth import verify_refresh_token, create_access_token
        rp = verify_refresh_token(ql_refresh)
        if rp:
            _ru = get_user(rp.get("user_id", ""))
            if _ru:
                user = _ru
                _new_tok = create_access_token({"user_id": _ru["id"], "email": _ru.get("email", "")})
                response.set_cookie(key=_ACCESS_COOKIE, value=_new_tok, httponly=True,
                    secure=_COOKIE_SECURE, samesite=_COOKIE_SAMESITE, max_age=7*24*3600, path="/")
    if not user:
        raise HTTPException(401, "Unauthorized")
    if user.get("role") != "client":
        raise HTTPException(403, "Only clients can book appointments")'''

if old_apt in src:
    src = src.replace(old_apt, new_apt)
    with open('/var/www/quanby-legal/backend/main.py', 'w', encoding='utf-8') as f:
        f.write(src)
    print('main.py: ql_refresh fallback added to create_appointment')
else:
    print('main.py: pattern not found')
