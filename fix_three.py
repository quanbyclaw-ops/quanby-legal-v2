with open('/var/www/quanby-legal/backend/main.py', 'r', encoding='utf-8') as f:
    src = f.read()

# ─── 1. Add mcle_no to /api/enps endpoint ────────────────────────────────────
old_enps = '''        result.append({
            "id": u["id"],
            "name": name,
            "email": u.get("email", ""),
            "notary_address": profile.get("notary_address", ""),
            "commission_no": profile.get("commission_no", ""),
            "ibp_no": profile.get("ibp_no", ""),
            "picture": u.get("picture", ""),
            "specializations": [],
        })'''

new_enps = '''        result.append({
            "id": u["id"],
            "name": name,
            "email": u.get("email", ""),
            "notary_address": profile.get("notary_address", ""),
            "commission_no": profile.get("commission_no", ""),
            "ibp_no": profile.get("ibp_no", ""),
            "mcle_no": profile.get("mcle_no", ""),
            "mcle_no_period": profile.get("mcle_no_period", ""),
            "picture": u.get("picture", ""),
            "specializations": [],
        })'''

if old_enps in src:
    src = src.replace(old_enps, new_enps)
    print('API: mcle_no added to /api/enps')
else:
    print('API pattern not found')

# ─── 2. Add DC token verify before using token in plot-link ──────────────────
old_verify = '''        # Retry up to 3 times with a fresh token each time
        for _retry in range(3):
            try:
                _tok = _get_dc_token(email=enp_email)
                print(f"[PlotLink] attempt {_retry+1}: email={enp_email} token={_tok[:12]}...", flush=True)
            except Exception as _te:
                _last_body = f"Token error for {enp_email}: {_te}"
                print(f"[PlotLink] token failed attempt {_retry+1}: {_te}", flush=True)
                _dc_token_cache.pop(enp_email, None)
                continue
            try:
                resp_data = _call_plot_link(_tok)
                print(f"[PlotLink] success on attempt {_retry+1} raw={str(resp_data)[:400]}", flush=True)
                break
            except _uerr2.HTTPError as he:
                _last_code = he.code
                _last_body = he.read().decode(errors="replace")
                _dc_token_cache.pop(enp_email, None)
                print(f"[PlotLink] HTTP {he.code} on attempt {_retry+1}: {_last_body[:120]}", flush=True)
                if he.code not in (401, 403):
                    raise HTTPException(he.code, f"DoconChain error {he.code}: {_last_body[:300]}")
                # 401/403 → clear cache and retry with fresh token
                continue'''

new_verify = '''        def _verify_dc_token(token):
            """Verify token is still valid using DC /auth/verify endpoint."""
            import json as _jv
            try:
                _vreq = _ureq2.Request(
                    f"{_DC_BASE}/api/v2/auth/verify?user_type=ENTERPRISE_API",
                    data=json.dumps({"org_invite_code": _DC_ORG_ID}).encode(),
                    headers={"Authorization": f"Bearer {token}",
                             "Content-Type": "application/json",
                             "Accept": "application/json"},
                    method="POST",
                )
                with _ureq2.urlopen(_vreq, timeout=10) as _vr:
                    _vd = json.loads(_vr.read().decode())
                    status = (_vd.get("data") or {}).get("status", "")
                    print(f"[PlotLink] token verify: status={status}", flush=True)
                    return status == "active"
            except Exception as _ve:
                print(f"[PlotLink] token verify failed (proceeding): {_ve}", flush=True)
                return True  # Assume valid if verify endpoint unreachable

        # Retry up to 3 times with a fresh token each time
        for _retry in range(3):
            try:
                _tok = _get_dc_token(email=enp_email)
                print(f"[PlotLink] attempt {_retry+1}: email={enp_email} token={_tok[:12]}...", flush=True)
            except Exception as _te:
                _last_body = f"Token error for {enp_email}: {_te}"
                print(f"[PlotLink] token failed attempt {_retry+1}: {_te}", flush=True)
                _dc_token_cache.pop(enp_email, None)
                continue
            # Verify token is active before using it
            if not _verify_dc_token(_tok):
                print(f"[PlotLink] token not active on attempt {_retry+1}, refreshing...", flush=True)
                _dc_token_cache.pop(enp_email, None)
                continue
            try:
                resp_data = _call_plot_link(_tok)
                print(f"[PlotLink] success on attempt {_retry+1} raw={str(resp_data)[:400]}", flush=True)
                break
            except _uerr2.HTTPError as he:
                _last_code = he.code
                _last_body = he.read().decode(errors="replace")
                _dc_token_cache.pop(enp_email, None)
                print(f"[PlotLink] HTTP {he.code} on attempt {_retry+1}: {_last_body[:120]}", flush=True)
                if he.code not in (401, 403):
                    raise HTTPException(he.code, f"DoconChain error {he.code}: {_last_body[:300]}")
                # 401/403 → clear cache and retry with fresh token
                continue'''

if old_verify in src:
    src = src.replace(old_verify, new_verify)
    print('Backend: DC token verify added to plot-link')
else:
    print('DC verify pattern not found')

with open('/var/www/quanby-legal/backend/main.py', 'w', encoding='utf-8') as f:
    f.write(src)
print('main.py saved')

# ─── 3. Browse page: IBP → MCLE ──────────────────────────────────────────────
with open('/var/www/quanby-legal/browse.html', 'r', encoding='utf-8') as f:
    browse = f.read()

old_ibp = '''          ${enp.ibp_no ? `
          <div style="display:flex;align-items:center;gap:.5rem;font-size:.82rem;color:#94a3b8;">
            <i class="hgi-stroke hgi-justice-scale-01" style="font-size:.85rem;flex-shrink:0;color:#c9a84c;"></i>
            <span>IBP No: <strong style="color:#f1f5f9;">${escHtml(enp.ibp_no)}</strong></span>
          </div>` : ''}'''

new_mcle = '''          ${enp.mcle_no ? `
          <div style="display:flex;align-items:center;gap:.5rem;font-size:.82rem;color:#94a3b8;">
            <i class="hgi-stroke hgi-certificate-01" style="font-size:.85rem;flex-shrink:0;color:#c9a84c;"></i>
            <span>MCLE No: <strong style="color:#f1f5f9;">${escHtml(enp.mcle_no)}</strong>${enp.mcle_no_period ? ' <span style="color:#94a3b8;font-size:.75rem;">(Compliance Period ' + escHtml(enp.mcle_no_period) + ')</span>' : ''}</span>
          </div>` : ''}'''

if old_ibp in browse:
    browse = browse.replace(old_ibp, new_mcle)
    print('Browse: IBP replaced with MCLE')
else:
    print('Browse IBP pattern not found — trying fallback')
    browse = browse.replace(
        "IBP No: <strong style=\"color:#f1f5f9;\">${escHtml(enp.ibp_no)}</strong>",
        "MCLE No: <strong style=\"color:#f1f5f9;\">${escHtml(enp.mcle_no || '—')}</strong>"
    )
    print('Browse: fallback IBP->MCLE done')

with open('/var/www/quanby-legal/browse.html', 'w', encoding='utf-8') as f:
    f.write(browse)
print('browse.html saved')
