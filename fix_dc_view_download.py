with open('/var/www/quanby-legal/backend/main.py', 'r', encoding='utf-8') as f:
    src = f.read()

# Replace the DC vault fetch to use both vault download AND project details for file URL
old_fetch = '''    # Get DC file via vault download endpoint (most reliable on staging)
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

new_fetch = '''    # Get DC file: vault/items/{uuid} for metadata + vault download for PDF bytes
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

                    # Step 1: Try GET /vault/items/{vault_uuid}?user_type=ENTERPRISE_API
                    # Returns: data.url (direct file URL), data.files[].file_url, data.reference_number
                    if dc_vault_uuid:
                        vi_url = f"{_DC_BASE}/vault/items/{dc_vault_uuid}?user_type=ENTERPRISE_API"
                        vi_req = _ureq_doc.Request(vi_url, headers={"Authorization": f"Bearer {tok}", "Accept": "application/json"})
                        try:
                            with _ureq_doc.urlopen(vi_req, timeout=20) as vi_r:
                                vi_resp = _json_doc.loads(vi_r.read().decode())
                            vi_data = vi_resp.get("data") or vi_resp
                            if isinstance(vi_data, dict) and vi_data.get("uuid"):
                                # Found: extract direct file URL
                                direct_url = vi_data.get("url") or ""
                                files = vi_data.get("files") or []
                                if files and files[0].get("file_url"):
                                    direct_url = files[0]["file_url"]
                                if direct_url:
                                    vi_data["_direct_file_url"] = direct_url
                                    vi_data["_pdf_name"] = vi_data.get("file_name") or vi_data.get("name") or act.get("doc_name","document")+".pdf"
                                    print(f"[DC] vault item OK: {vi_data.get('uuid','?')[:12]} url={direct_url[:50]}", flush=True)
                                    return vi_data
                        except Exception as _ve:
                            print(f"[DC] vault/items detail failed (trying download): {_ve}", flush=True)

                        # Step 2: fallback to direct binary download
                        dl_url = f"{_DC_BASE}/vault/items/{dc_vault_uuid}/download?user_type=ENTERPRISE_API"
                        dl_req = _ureq_doc.Request(dl_url, headers={"Authorization": f"Bearer {tok}", "Accept": "*/*"})
                        try:
                            with _ureq_doc.urlopen(dl_req, timeout=30) as dl_r:
                                ct = dl_r.headers.get("Content-Type", "")
                                if "pdf" in ct.lower() or "octet" in ct.lower():
                                    pdf_bytes = dl_r.read()
                                    return {"_pdf_bytes": pdf_bytes,
                                            "_pdf_name": act.get("doc_name","document")+".pdf",
                                            "uuid": dc_vault_uuid}
                        except Exception as _de:
                            print(f"[DC] vault download failed: {_de}", flush=True)

                    # Step 3: project endpoint for signer/reference data
                    if dc_uuid:
                        p_url = f"{_DC_BASE}/api/v2/projects/{dc_uuid}?user_type=ENTERPRISE_API"
                        p_req = _ureq_doc.Request(p_url, headers={"Authorization": f"Bearer {tok}", "Accept": "application/json"})
                        try:
                            with _ureq_doc.urlopen(p_req, timeout=20) as pr:
                                p_resp = _json_doc.loads(pr.read().decode())
                            p_data = p_resp.get("data") or p_resp
                            if p_data and p_data.get("uuid"):
                                # Also attach vault download URL for direct access
                                if dc_vault_uuid:
                                    p_data["_vault_download_url"] = f"{_DC_BASE}/vault/items/{dc_vault_uuid}/download?user_type=ENTERPRISE_API"
                                    p_data["_vault_token"] = tok
                                return p_data
                        except Exception as _pe:
                            print(f"[DC] project details failed: {_pe}", flush=True)
                except Exception as _e:
                    print(f"[DC] fetch failed for {_email}: {_e}", flush=True)
                    continue
            return None'''

if old_fetch in src:
    src = src.replace(old_fetch, new_fetch)
    print('Fixed: DC fetch uses vault/items/{uuid} + direct URL + download fallback')
else:
    print('Pattern not found')

# Also fix vault_item processing to use _direct_file_url
old_process = '''            if vault_item:
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

new_process = '''            if vault_item:
                # Priority 1: direct file URL from vault/items/{uuid}
                if vault_item.get("_direct_file_url"):
                    _direct = vault_item["_direct_file_url"]
                    _pname  = vault_item.get("_pdf_name") or act.get("doc_name","Document")+".pdf"
                    dc_files.append({"fileName": _pname, "downloadUrl": _direct, "source": "vault_direct"})
                    print(f"[DC] using direct URL: {_direct[:60]}", flush=True)
                # Priority 2: raw PDF bytes via vault download
                elif vault_item.get("_pdf_bytes"):
                    _pdf_b = vault_item["_pdf_bytes"]
                    _pdf_n = vault_item.get("_pdf_name") or act.get("doc_name","document")+".pdf"
                    import base64 as _b64
                    dc_files.append({
                        "fileName": _pdf_n,
                        "downloadUrl": f"data:application/pdf;base64,{_b64.b64encode(_pdf_b).decode()}",
                        "source": "vault_download", "size": len(_pdf_b),
                    })
                # Build download/view links from vault item
                dc_view_url = f"{_DC_APP_URL}/sign/{dc_uuid}"'''

if old_process in src:
    src = src.replace(old_process, new_process)
    print('Fixed: vault item processing uses direct URL first')
else:
    print('Process pattern not found')

with open('/var/www/quanby-legal/backend/main.py', 'w', encoding='utf-8') as f:
    f.write(src)
print('Done')
