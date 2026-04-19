with open('/var/www/quanby-legal/backend/main.py', 'r', encoding='utf-8') as f:
    src = f.read()

# Add vpn-check endpoint right after /api/sessions/my-ip
old_after = '''@app.get("/api/sessions/my-ip")
async def get_my_ip(request: Request):
    """Return the client IP for VPN/proxy detection. No auth required."""
    # Respect X-Forwarded-For (set by nginx proxy)
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        ip = forwarded.split(",")[0].strip()
    else:
        ip = request.client.host if request.client else "unknown"
    return {"ip": ip}'''

new_after = '''@app.get("/api/sessions/my-ip")
async def get_my_ip(request: Request):
    """Return the client IP for VPN/proxy detection. No auth required."""
    # Respect X-Forwarded-For (set by nginx proxy)
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        ip = forwarded.split(",")[0].strip()
    else:
        ip = request.client.host if request.client else "unknown"
    return {"ip": ip}


@app.get("/api/sessions/vpn-check")
async def vpn_check(ip: str):
    """Backend proxy for proxycheck.io — avoids CORS when called from browser.
    No auth required (public endpoint for lobby use).
    """
    import urllib.request as _ureq_vpn, json as _json_vpn
    PROXY_KEY = "71e443-5vn7j9-232954-9a3565"
    if not ip or ip == "unknown":
        return {"is_vpn": False, "ip": ip, "note": "no_ip"}
    try:
        _url = f"https://proxycheck.io/v2/{ip}?key={PROXY_KEY}&vpn=1&asn=1"
        _req = _ureq_vpn.Request(_url, headers={"User-Agent": "QuanbyLegal/1.0"})
        with _ureq_vpn.urlopen(_req, timeout=8) as _r:
            _d = _json_vpn.loads(_r.read().decode())
        entry = _d.get(ip) or {}
        is_vpn = entry.get("proxy") == "yes" or entry.get("vpn") == "yes" or entry.get("type") == "VPN"
        return {
            "is_vpn": is_vpn,
            "ip": ip,
            "proxy": entry.get("proxy", "no"),
            "vpn": entry.get("vpn", "no"),
            "asn": entry.get("asn", ""),
            "country": entry.get("country", ""),
        }
    except Exception as e:
        # proxycheck unavailable — fail open (don't block)
        return {"is_vpn": False, "ip": ip, "note": f"check_failed: {str(e)[:80]}"}'''

if old_after in src:
    src = src.replace(old_after, new_after)
    print('VPN check endpoint added')
else:
    print('Pattern not found')

with open('/var/www/quanby-legal/backend/main.py', 'w', encoding='utf-8') as f:
    f.write(src)
