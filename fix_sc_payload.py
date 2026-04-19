with open('/var/www/quanby-legal/backend/main.py', 'r', encoding='utf-8') as f:
    src = f.read()

# Fix principal list - always include at least one principal from act data
old = '''        # Step 2: Build principals list per SC spec
        # SC spec: { principalName, principalAddress: { homeStreet, barangay, cityProvince } }
        list_of_principals = []
        if act.get("principal_name") or act.get("principal_email"):
            list_of_principals.append({
                "principalName": act.get("principal_name") or act.get("principal_email", ""),
                "principalAddress": {
                    "homeStreet": profile.get("home_street") or "N/A",
                    "barangay": profile.get("barangay") or "N/A",
                    "cityProvince": profile.get("city_province") or act.get("location", "Remote Electronic Notarization"),
                },
            })'''

new = '''        # Step 2: Build principals list per SC spec
        # Always include at least one principal — SC rejects empty list
        _principal_name = (act.get("principal_name") or act.get("principal") or
                          act.get("client_name") or act.get("principal_email") or "Principal")
        _city = (profile.get("city_province") or act.get("location") or
                 profile.get("notary_address") or "Legazpi City, Albay")
        list_of_principals = [{
            "principalName": _principal_name,
            "principalAddress": {
                "homeStreet": profile.get("home_street") or "N/A",
                "barangay": profile.get("barangay") or "N/A",
                "cityProvince": _city,
            },
        }]'''

if old in src:
    src = src.replace(old, new)
    print('Fixed: SC payload always has principal')
else:
    print('Pattern not found')

# Fix act_type mapping to use notarization_type fallback
old2 = '''        _notarial_act_type = _act_type_map.get(
            str(act.get("act_type", "ACKNOWLEDGMENT")).upper(),
            act.get("act_type", "Acknowledgment")
        )'''
new2 = '''        _act_type_src = act.get("act_type") or act.get("notarization_type") or "ACKNOWLEDGMENT"
        _notarial_act_type = _act_type_map.get(
            str(_act_type_src).upper(),
            _act_type_src or "Acknowledgment"
        )'''

if old2 in src:
    src = src.replace(old2, new2)
    print('Fixed: act_type fallback to notarization_type')
else:
    print('act_type pattern not found (may already be fixed)')

with open('/var/www/quanby-legal/backend/main.py', 'w', encoding='utf-8') as f:
    f.write(src)
print('Done')
