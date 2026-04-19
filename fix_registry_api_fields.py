with open('/var/www/quanby-legal/backend/main.py', 'r', encoding='utf-8') as f:
    src = f.read()

count = 0

# In the registry document fetch, fix field name lookups
# These are in the registry_get_act_document endpoint
replacements = [
    # dc_uuid lookup
    ('dc_uuid = act.get("doconchain_project_uuid") or ""',
     'dc_uuid = act.get("dc_project_uuid") or act.get("doconchain_project_uuid") or ""'),
    # dc_reference_number in list endpoint
    ('"dc_reference_number":    act.get("dc_reference_number", "")',
     '"dc_reference_number":    act.get("dc_reference_no") or act.get("dc_reference_number", "")'),
    # Also in the act serialization
    ('"doconchain_project_uuid": act.get("doconchain_project_uuid", "")',
     '"doconchain_project_uuid": act.get("dc_project_uuid") or act.get("doconchain_project_uuid", "")'),
]

for old, new in replacements:
    n = src.count(old)
    if n:
        src = src.replace(old, new)
        count += n
        print(f'Fixed {n}x: {old[:60]}')
    else:
        print(f'Not found: {old[:60]}')

# Find and fix the registry list serialization
# Look for where acts are serialized to JSON response
import re
# Find dc_reference_number in dict serialization
m = re.search(r'"dc_reference_number":\s*act\.get\("dc_reference_number"', src)
if m:
    old2 = src[m.start():m.end()+5]
    print('Found dc_reference_number at:', m.start())

with open('/var/www/quanby-legal/backend/main.py', 'w', encoding='utf-8') as f:
    f.write(src)
print(f'Total: {count} fixes in main.py')
