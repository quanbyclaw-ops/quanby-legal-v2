with open('/var/www/quanby-legal/backend/main.py', 'r', encoding='utf-8') as f:
    src = f.read()

# Replace the DC vault fetch to use vault UUID instead of project UUID
old = '''    if dc_uuid:
        def _fetch_dc_vault():
            enp_user = get_user(enp_id)
            enp_email = (enp_user or {}).get("email", "") if enp_user else ""
            # Use GET /api/v2/projects/{uuid} — returns files[] with signed PDFs
            for _email in [enp_email, _DC_EMAIL]:
                if not _email:
                    continue
                try:
                    tok = _get_dc_token(email=_email)
                    url = f"{_DC_BASE}/api/v2/projects/{dc_uuid}?user_type=ENTERPRISE_API"
                    req = _ureq_doc.Request(url, headers={
                        "Authorization": f"Bearer {tok}",
                        "Accept": "application/json",
                    })
                    with _ureq_doc.urlopen(req, timeout=20) as r:
                        resp = _json_doc.loads(r.read().decode())
                    data = resp.get("data") or resp
                    if data and data.get("uuid"):
                        return data
                except Exception as _e:
                    print(f"[DC] /api/v2/projects/{dc_uuid} with {_email} failed: {_e}", flush=True)
                    continue
            return None'''

new = '''    # Also try vault UUID for direct file access
    dc_vault_uuid = act.get("dc_vault_uuid") or ""
    if dc_uuid or dc_vault_uuid:
        def _fetch_dc_vault():
            enp_user = get_user(enp_id)
            enp_email = (enp_user or {}).get("email", "") if enp_user else ""
            for _email in [enp_email, _DC_EMAIL]:
                if not _email:
                    continue
                try:
                    tok = _get_dc_token(email=_email)
                    # Try vault/items/{vault_uuid} first (more reliable on staging)
                    if dc_vault_uuid:
                        vault_url = f"{_DC_BASE}/vault/items/{dc_vault_uuid}?user_type=ENTERPRISE_API"
                        req = _ureq_doc.Request(vault_url, headers={"Authorization": f"Bearer {tok}", "Accept": "application/json"})
                        try:
                            with _ureq_doc.urlopen(req, timeout=20) as r:
                                resp = _json_doc.loads(r.read().decode())
                            data = resp.get("data") or resp
                            if data and (data.get("uuid") or data.get("project_uuid")):
                                return data
                        except Exception as _ve:
                            print(f"[DC] vault/items/{dc_vault_uuid} failed: {_ve}", flush=True)
                    # Fallback: project endpoint
                    if dc_uuid:
                        url = f"{_DC_BASE}/api/v2/projects/{dc_uuid}?user_type=ENTERPRISE_API"
                        req = _ureq_doc.Request(url, headers={"Authorization": f"Bearer {tok}", "Accept": "application/json"})
                        try:
                            with _ureq_doc.urlopen(req, timeout=20) as r:
                                resp = _json_doc.loads(r.read().decode())
                            data = resp.get("data") or resp
                            if data and data.get("uuid"):
                                return data
                        except Exception as _pe:
                            print(f"[DC] /api/v2/projects/{dc_uuid} failed: {_pe}", flush=True)
                except Exception as _e:
                    print(f"[DC] fetch failed for {_email}: {_e}", flush=True)
                    continue
            return None'''

if old in src:
    src = src.replace(old, new)
    print('Fixed: DC vault fetch now tries vault UUID first')
else:
    print('Pattern not found')

# Also fix the fallback URL - use vault contents URL not the sign page
old_fallback = '''                if not dc_files:
                    dc_files.append({
                        "fileName": act.get("doc_name", "Notarized Document"),'''

# Check what comes after to fix the stg-app URL
idx = src.find('"downloadUrl": f"{_DC_APP_URL}/sign/{dc_uuid}"')
if idx > 0:
    # Replace the stg-app sign URL fallback with a message
    old_sign_url = '"downloadUrl": f"{_DC_APP_URL}/sign/{dc_uuid}"'
    new_sign_url = '"downloadUrl": ""'  # empty = no direct download from sign page
    src = src.replace(old_sign_url, new_sign_url)
    print('Fixed: removed stg-app sign URL fallback (not a direct download)')

with open('/var/www/quanby-legal/backend/main.py', 'w', encoding='utf-8') as f:
    f.write(src)
print('Done')
