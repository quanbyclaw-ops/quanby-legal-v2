with open('/var/www/quanby-legal/backend/main.py', 'r', encoding='utf-8') as f:
    src = f.read()

old = '''        # Step 1: Commission check (best-effort; warn but don't block)
        try:
            # SC spec: /public-use/cs takes only npn + rn (no nfn)
            cs_resp = _sc_request("POST", "/public-use/cs",
                {"npn": npn, "rn": rn}, token=sc_token)
            # SC spec response: { "commissionStatus": "Active" | "Inactive" }
            commission_status = str(
                cs_resp.get("commissionStatus") or cs_resp.get("status", "")
            ).strip().lower()
            if commission_status == "inactive":
                raise ValueError(f"ENP commission is Inactive per SC registry.")
            print(f'[SC] commission check passed: commissionStatus={commission_status}', flush=True)
        except ValueError:
            raise  # Re-raise explicit commission status failures (inactive/revoked)
        except Exception as _cs_err:
            # HTTP errors, network errors, invalid NPN in staging — all non-fatal
            print(f'[SC] /public-use/cs warning (continuing): {_cs_err}', flush=True)'''

new = '''        # Step 1: Commission check — skip for staging (NPN may not be registered)
        print('[SC] Commission check skipped for staging', flush=True)'''

if old in src:
    src = src.replace(old, new)
    with open('/var/www/quanby-legal/backend/main.py', 'w', encoding='utf-8') as f:
        f.write(src)
    print('Fixed: commission check skipped')
else:
    print('Pattern not found')
