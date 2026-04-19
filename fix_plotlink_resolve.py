with open('/var/www/quanby-legal/backend/main.py', 'r', encoding='utf-8') as f:
    src = f.read()

old_return = '''        # Record that plotting was started for this document
        with _apts_lock:
            _reload_appointments()
            for _aid, _apt in _appointments.items():
                for _doc in _apt.get("session_documents", []):
                    _duuid = _doc.get("doconchain_project_uuid") or _doc.get("project_uuid")
                    if _duuid == project_uuid:
                        _doc["plotting_started"] = True
                        _doc["plotting_started_at"] = _dt.now(_tz.utc).isoformat()
                        _save_appointments()
                        break

          # NOTE: Do NOT strip token/api_token — DC needs them for auto-login in popup.
        try:
            from urllib.parse import urlparse
            _base = urlparse(link).netloc + urlparse(link).path
        except Exception:
            _base = link[:60]
        print(f"[PlotLink] link ready: {_base}", flush=True)
        return {"link": link, "project_uuid": project_uuid}'''

new_return = '''        # Resolve short links (link.doconchain.com/...) to full URL with embedded auth token
        # Short links embed a session-bound token that expires — resolving gives us the live
        # token that was just generated, preventing login redirects on popup open.
        resolved_link = link
        if "link.doconchain.com" in link:
            import urllib.request as _ureq_resolve
            try:
                _resolve_req = _ureq_resolve.Request(
                    link,
                    headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"},
                    method="GET",
                )
                with _ureq_resolve.urlopen(_resolve_req, timeout=10) as _rr:
                    resolved_link = _rr.url
                print(f"[PlotLink] resolved short link to full URL (has token params: {('token=' in resolved_link)})", flush=True)
            except Exception as _re:
                print(f"[PlotLink] short link resolve failed (using original): {_re}", flush=True)
                resolved_link = link

        # Record that plotting was started for this document
        with _apts_lock:
            _reload_appointments()
            for _aid, _apt in _appointments.items():
                for _doc in _apt.get("session_documents", []):
                    _duuid = _doc.get("doconchain_project_uuid") or _doc.get("project_uuid")
                    if _duuid == project_uuid:
                        _doc["plotting_started"] = True
                        _doc["plotting_started_at"] = _dt.now(_tz.utc).isoformat()
                        _save_appointments()
                        break

          # NOTE: Do NOT strip token/api_token — DC needs them for auto-login in popup.
        try:
            from urllib.parse import urlparse
            _base = urlparse(resolved_link).netloc + urlparse(resolved_link).path
        except Exception:
            _base = resolved_link[:60]
        print(f"[PlotLink] link ready: {_base}", flush=True)
        return {"link": resolved_link, "project_uuid": project_uuid}'''

if old_return in src:
    src = src.replace(old_return, new_return)
    print('PlotLink: short-link resolution added')
else:
    print('Pattern not found')

with open('/var/www/quanby-legal/backend/main.py', 'w', encoding='utf-8') as f:
    f.write(src)
print('Done')
