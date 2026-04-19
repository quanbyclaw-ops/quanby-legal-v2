with open('/var/www/quanby-legal/backend/main.py', 'r', encoding='utf-8') as f:
    src = f.read()

# Replace base64 data URL with proxy endpoint URL
old = '''                elif vault_item.get("_pdf_bytes"):
                    _pdf_b = vault_item["_pdf_bytes"]
                    _pdf_n = vault_item.get("_pdf_name") or act.get("doc_name","document")+".pdf"
                    import base64 as _b64
                    dc_files.append({
                        "fileName": _pdf_n,
                        "downloadUrl": f"data:application/pdf;base64,{_b64.b64encode(_pdf_b).decode()}",
                        "source": "vault_download", "size": len(_pdf_b),
                    })'''

new = '''                elif vault_item.get("_pdf_bytes"):
                    # Use proxy endpoint instead of base64 data URL (browsers block data: in iframes)
                    _pdf_n = vault_item.get("_pdf_name") or act.get("doc_name","document")+".pdf"
                    _proxy_url = f"/api/registry/acts/{act_id}/pdf"
                    dc_files.append({
                        "fileName": _pdf_n,
                        "downloadUrl": _proxy_url,
                        "source": "vault_proxy",
                    })'''

if old in src:
    src = src.replace(old, new)
    print('Fixed: base64 replaced with proxy URL')
else:
    print('Pattern not found')

with open('/var/www/quanby-legal/backend/main.py', 'w', encoding='utf-8') as f:
    f.write(src)
