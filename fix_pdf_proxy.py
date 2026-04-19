with open('/var/www/quanby-legal/backend/main.py', 'r', encoding='utf-8') as f:
    src = f.read()

# Add a PDF proxy endpoint that streams the PDF from DC vault
pdf_proxy_endpoint = '''
# ─── GET /api/registry/acts/{act_id}/pdf ─────────────────────────────────────
# Streams the notarized PDF directly from DC vault to the browser

@app.get("/api/registry/acts/{act_id}/pdf")
async def registry_get_act_pdf(
    act_id: str,
    authorization: Optional[str] = Header(None),
    ql_access: Optional[str] = Cookie(default=None),
):
    """Stream the notarized PDF for an act directly from DoconChain vault."""
    from fastapi.responses import Response as _FResponse
    user = get_current_user(authorization, ql_access)
    if not user:
        raise HTTPException(401, "Unauthorized")

    with _registry_lock:
        registry = _load_registry()
        act = next((a for a in registry["acts"] if a.get("id") == act_id
                    and a.get("enp_id") == user["id"]), None)

    if not act:
        raise HTTPException(404, "Act not found")

    dc_vault_uuid = act.get("dc_vault_uuid") or ""
    if not dc_vault_uuid:
        raise HTTPException(404, "No vault document for this act")

    import urllib.request as _ureq_pdf
    enp_email = user.get("email", "") or _DC_EMAIL

    try:
        tok = _get_dc_token(email=enp_email)
        dl_url = f"{_DC_BASE}/vault/items/{dc_vault_uuid}/download?user_type=ENTERPRISE_API"
        dl_req = _ureq_pdf.Request(dl_url,
            headers={"Authorization": f"Bearer {tok}", "Accept": "*/*"})
        with _ureq_pdf.urlopen(dl_req, timeout=30) as dl_r:
            pdf_bytes = dl_r.read()
            content_type = dl_r.headers.get("Content-Type", "application/pdf")

        doc_name = act.get("doc_name", "notarized-document") or "notarized-document"
        safe_name = doc_name.replace('"', '').replace(' ', '_') + ".pdf"

        return _FResponse(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'inline; filename="{safe_name}"',
                "Content-Length": str(len(pdf_bytes)),
                "Cache-Control": "no-store",
            }
        )
    except Exception as e:
        raise HTTPException(502, f"Could not fetch PDF from DoconChain: {str(e)[:200]}")


'''

# Insert before the registry/sync-all endpoint
target = '# ─── POST /api/registry/sync-all'
if '/api/registry/acts/{act_id}/pdf' not in src and target in src:
    src = src.replace(target, pdf_proxy_endpoint + target)
    print('PDF proxy endpoint added')
elif '/api/registry/acts/{act_id}/pdf' in src:
    print('Already exists')
else:
    print('Target not found')

with open('/var/www/quanby-legal/backend/main.py', 'w', encoding='utf-8') as f:
    f.write(src)
print('Done')
