with open('/var/www/quanby-legal/backend/main.py', 'r', encoding='utf-8') as f:
    src = f.read()

# Replace the DC vault fetch to use /vault/items/{vault_uuid}/download directly
old_fetch = '''    # Also try vault UUID for direct file access
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

new_fetch = '''    # Get DC file via vault download endpoint (most reliable on staging)
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
                    # Approach 1: vault/items/{vault_uuid}/download — returns raw PDF
                    if dc_vault_uuid:
                        dl_url = f"{_DC_BASE}/vault/items/{dc_vault_uuid}/download?user_type=ENTERPRISE_API"
                        dl_req = _ureq_doc.Request(dl_url, headers={"Authorization": f"Bearer {tok}", "Accept": "*/*"})
                        try:
                            with _ureq_doc.urlopen(dl_req, timeout=30) as dl_r:
                                ct = dl_r.headers.get("Content-Type", "")
                                if "pdf" in ct.lower() or "application/octet" in ct.lower():
                                    pdf_bytes = dl_r.read()
                                    return {"_pdf_bytes": pdf_bytes, "_pdf_name": act.get("doc_name","document")+".pdf", "uuid": dc_vault_uuid}
                        except Exception as _de:
                            print(f"[DC] vault download failed: {_de}", flush=True)
                    # Approach 2: project details for signer info
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
                            print(f"[DC] project details failed: {_pe}", flush=True)
                except Exception as _e:
                    print(f"[DC] fetch failed for {_email}: {_e}", flush=True)
                    continue
            return None'''

if old_fetch in src:
    src = src.replace(old_fetch, new_fetch)
    print('Fixed: vault download endpoint added')
else:
    print('Pattern not found')

# Also fix the vault_item processing to handle _pdf_bytes
old_process = '''            if vault_item:
                # Build download/view links from vault item
                dc_view_url = f"{_DC_APP_URL}/sign/{dc_uuid}"'''

new_process = '''            if vault_item:
                # If we got raw PDF bytes, serve them directly
                if vault_item.get("_pdf_bytes"):
                    _pdf_b = vault_item["_pdf_bytes"]
                    _pdf_n = vault_item["_pdf_name"]
                    import base64 as _b64
                    dc_files.append({
                        "fileName": _pdf_n,
                        "downloadUrl": f"data:application/pdf;base64,{_b64.b64encode(_pdf_b).decode()}",
                        "source": "vault_download",
                        "size": len(_pdf_b),
                    })
                # Build download/view links from vault item
                dc_view_url = f"{_DC_APP_URL}/sign/{dc_uuid}"'''

if old_process in src:
    src = src.replace(old_process, new_process)
    print('Fixed: PDF bytes served as base64 data URL')
else:
    print('Process pattern not found')

with open('/var/www/quanby-legal/backend/main.py', 'w', encoding='utf-8') as f:
    f.write(src)
print('Done')
