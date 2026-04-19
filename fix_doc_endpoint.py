with open('/var/www/quanby-legal/backend/main.py', 'r', encoding='utf-8') as f:
    src = f.read()

# Find the document endpoint return statement and add dc_vault_url
old_return = '''    return {
        "act_id":             act_id,
        "dc_files":           dc_files,
        "sc_files":           sc_files,
        "doconchain_view_url": dc_view_url,'''

new_return = '''    return {
        "act_id":             act_id,
        "dc_files":           dc_files,
        "sc_files":           sc_files,
        "dc_vault_url":       act.get("dc_vault_url") or dc_view_url or "",
        "doconchain_view_url": dc_view_url,'''

if old_return in src:
    src = src.replace(old_return, new_return)
    with open('/var/www/quanby-legal/backend/main.py', 'w', encoding='utf-8') as f:
        f.write(src)
    print('Fixed: dc_vault_url added to document endpoint response')
else:
    print('Pattern not found')
    idx = src.find('"doconchain_view_url"')
    print('doconchain_view_url at:', idx)
