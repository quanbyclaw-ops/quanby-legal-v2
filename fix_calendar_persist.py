with open('/var/www/quanbyai-website/calendar.html', 'r', encoding='utf-8') as f:
    src = f.read()

count = 0

# Fix 1: Auth — use localStorage instead of sessionStorage so login persists across tabs/refreshes
replacements = [
    # Login: set auth
    ("sessionStorage.setItem('qcal_auth', '1');", "localStorage.setItem('qcal_auth', '1');"),
    ("sessionStorage.setItem('qcal_user', u);", "localStorage.setItem('qcal_user', u);"),
    # Show app: read auth
    ("sessionStorage.getItem('qcal_auth') === '1') showApp();",
     "localStorage.getItem('qcal_auth') === '1') showApp();"),
    ("sessionStorage.getItem('qcal_user') || 'Staff'",
     "localStorage.getItem('qcal_user') || 'Staff'"),
    # Sign out: remove auth
    ("sessionStorage.removeItem('qcal_auth');",
     "localStorage.removeItem('qcal_auth');"),
    # Any other sessionStorage references for qcal
    ("sessionStorage.getItem('qcal_auth')", "localStorage.getItem('qcal_auth')"),
    ("sessionStorage.getItem('qcal_user')", "localStorage.getItem('qcal_user')"),
]

for old, new in replacements:
    n = src.count(old)
    if n:
        src = src.replace(old, new)
        count += n
        print(f'Fixed {n}x: {old[:50]}')

# Fix 2: Also clear user key on sign out
old_signout = "localStorage.removeItem('qcal_auth');"
new_signout = "localStorage.removeItem('qcal_auth'); localStorage.removeItem('qcal_user');"
if old_signout in src and 'qcal_user' not in src[src.find(old_signout):src.find(old_signout)+60]:
    src = src.replace(old_signout, new_signout, 1)
    count += 1
    print('Fixed: sign out also clears qcal_user')

with open('/var/www/quanbyai-website/calendar.html', 'w', encoding='utf-8') as f:
    f.write(src)
print(f'Total: {count} fixes — auth now persists in localStorage')
