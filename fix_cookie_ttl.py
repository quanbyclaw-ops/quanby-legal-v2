with open('/var/www/quanby-legal/backend/main.py', 'r', encoding='utf-8') as f:
    src = f.read()

original = src

# Fix 1: _set_auth_cookies — access token cookie 24h -> 7 days
src = src.replace(
    "        max_age=24 * 60 * 60,      # 24 hours\n        path=\"/\",\n    )\n    response.set_cookie(\n        key=_REFRESH_COOKIE",
    "        max_age=7 * 24 * 60 * 60,  # 7 days (matches JWT TTL)\n        path=\"/\",\n    )\n    response.set_cookie(\n        key=_REFRESH_COOKIE"
)

# Fix 2: refresh endpoint — access token cookie 24h -> 7 days
src = src.replace(
    "        max_age=24 * 60 * 60,  # 24 hours\n        path=\"/\",\n    )\n    response.set_cookie(\n        key=_REFRESH_COOKIE,",
    "        max_age=7 * 24 * 60 * 60,  # 7 days (matches JWT TTL)\n        path=\"/\",\n    )\n    response.set_cookie(\n        key=_REFRESH_COOKIE,"
)

# Count replacements
changed = src.count('7 * 24 * 60 * 60,  # 7 days')
print(f'Access token cookie TTL extended in {changed} locations')

if src == original:
    print('WARNING: No changes made — pattern not found')
    # Debug: find the 24h pattern
    idx = src.find('max_age=24 * 60 * 60')
    if idx >= 0:
        print('Found 24h pattern at:', idx)
        print('Context:', src[max(0,idx-100):idx+150])
else:
    with open('/var/www/quanby-legal/backend/main.py', 'w', encoding='utf-8') as f:
        f.write(src)
    print('main.py updated')
