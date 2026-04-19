import re

QUANBY_VARS = """
      --ql-navy: #1e3a5f;
      --ql-navy-mid: #254a78;
      --ql-teal: #00d4c8;
      --ql-teal-dark: #00b8ad;
      --ql-purple: #7c3aed;
      --ql-bg: #0a0e1a;
      --ql-surface: #0f1521;
      --ql-text: #e6edf3;
      --ql-muted: #94a3b8;
"""

# ── BCS IMS layout ────────────────────────────────────────────────────────────
with open('/var/www/bcs-ims/resources/views/layouts/app.blade.php', 'r', encoding='utf-8') as f:
    bcs = f.read()

# Update CSS variables + link to favicon
bcs = bcs.replace(
    '  <link rel="icon" type="image/svg+xml" href="https://quanbyai.com/favicon.svg">',
    '  <link rel="icon" href="/favicon.ico">\n  <link rel="icon" type="image/png" href="/favicon.png">'
)

# Replace color vars with Quanby Legal palette
bcs = bcs.replace(
    '''      --denr-green: #1e3a5f;
      --denr-accent: #00d4c8;
      --denr-green-mid: #254a78;
      --bcs-bg: #f0f4f8;
      --bcs-text: #1a2535;''',
    '''      --denr-green: #1e3a5f;
      --denr-accent: #00d4c8;
      --denr-green-mid: #7c3aed;
      --bcs-bg: #f0f4f8;
      --bcs-text: #1a2535;'''
)

# Update sidebar brand text color to purple accent
bcs = bcs.replace(
    "style=\"font-size:0.95rem;font-weight:800;color:var(--denr-accent);line-height:1.2\">Quanby Procurement",
    "style=\"font-size:0.95rem;font-weight:800;color:var(--ql-teal, #00d4c8);line-height:1.2\">Quanby Procurement"
)

# Add Quanby Legal font (Inter) in head
if 'fonts.googleapis' not in bcs:
    bcs = bcs.replace(
        '  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">',
        '  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">\n  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">'
    )

# Update body font
bcs = bcs.replace(
    "body { background: var(--bcs-bg); font-family: 'Segoe UI', sans-serif;",
    "body { background: var(--bcs-bg); font-family: 'Inter', 'Segoe UI', sans-serif;"
)

# Add purple accent for active sidebar link
bcs = bcs.replace(
    ".sidebar .nav-link:hover, .sidebar .nav-link.active { color: var(--denr-accent); border-left-color: var(--denr-accent);",
    ".sidebar .nav-link.active { color: #a78bfa; border-left-color: #7c3aed; background: rgba(124,58,237,0.12); }\n    .sidebar .nav-link:hover { color: var(--denr-accent); border-left-color: var(--denr-accent);"
)

with open('/var/www/bcs-ims/resources/views/layouts/app.blade.php', 'w', encoding='utf-8') as f:
    f.write(bcs)
print('BCS IMS layout updated')

# ── BCS IMS login ─────────────────────────────────────────────────────────────
with open('/var/www/bcs-ims/resources/views/auth/login.blade.php', 'r', encoding='utf-8') as f:
    bcs_login = f.read()

bcs_login = bcs_login.replace(
    '<meta charset="UTF-8">',
    '<link rel="icon" href="/favicon.ico">\n  <link rel="icon" type="image/png" href="/favicon.png">\n  <meta charset="UTF-8">'
)
bcs_login = bcs_login.replace('--denr-green: #1e3a5f; --denr-accent: #00d4c8;', '--denr-green: #1e3a5f; --denr-accent: #00d4c8; --ql-purple: #7c3aed;')

if 'fonts.googleapis' not in bcs_login:
    bcs_login = bcs_login.replace(
        '  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">',
        '  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">\n  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">'
    )

with open('/var/www/bcs-ims/resources/views/auth/login.blade.php', 'w', encoding='utf-8') as f:
    f.write(bcs_login)
print('BCS IMS login updated')

# ── OPAPRU EDMS (DMS) layout ──────────────────────────────────────────────────
with open('/var/www/opapru-edms/resources/views/layouts/app.blade.php', 'r', encoding='utf-8') as f:
    dms = f.read()

# Replace favicon
dms = re.sub(r'<link rel="icon"[^>]*>', '', dms)
dms = dms.replace('<meta charset="utf-8">', '<link rel="icon" href="/favicon.ico">\n    <link rel="icon" type="image/png" href="/favicon.png">\n    <meta charset="utf-8">')

# Add Inter font
if 'fonts.googleapis' not in dms:
    dms = dms.replace(
        '<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2',
        '<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">\n    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2'
    )

# Replace primary color variable with Quanby Legal palette
dms = re.sub(r'--primary[^;]*;', '--primary: #1e3a5f;', dms)
dms = re.sub(r'--primary-dark[^;]*;', '--primary-dark: #254a78;', dms)
dms = re.sub(r'--accent[^;]*;', '--accent: #00d4c8;', dms)

# Update body font
dms = re.sub(r"font-family:\s*['\"]?Segoe UI['\"]?,?\s*sans-serif", "font-family: 'Inter', 'Segoe UI', sans-serif", dms)

with open('/var/www/opapru-edms/resources/views/layouts/app.blade.php', 'w', encoding='utf-8') as f:
    f.write(dms)
print('DMS layout updated')

# ── OPAPRU EDMS login ─────────────────────────────────────────────────────────
with open('/var/www/opapru-edms/resources/views/auth/login.blade.php', 'r', encoding='utf-8') as f:
    dms_login = f.read()

dms_login = re.sub(r'<link rel="icon"[^>]*>', '', dms_login)
dms_login = dms_login.replace('<meta charset="utf-8">', '<link rel="icon" href="/favicon.ico">\n    <link rel="icon" type="image/png" href="/favicon.png">\n    <meta charset="utf-8">')

if 'fonts.googleapis' not in dms_login:
    dms_login = dms_login.replace(
        '<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2',
        '<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">\n    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2'
    )

# Update primary colors
dms_login = re.sub(r'--primary[^;]*;', '--primary: #1e3a5f;', dms_login)
dms_login = re.sub(r'--accent[^;]*;', '--accent: #00d4c8;', dms_login)

with open('/var/www/opapru-edms/resources/views/auth/login.blade.php', 'w', encoding='utf-8') as f:
    f.write(dms_login)
print('DMS login updated')

print()
print('Done. Both apps rethemed with Quanby Legal colors + favicons.')
