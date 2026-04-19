with open('/var/www/bcs-ims/resources/views/auth/login.blade.php', 'r', encoding='utf-8') as f:
    login = f.read()

# Title
login = login.replace(
    '<title>Login \xe2\x80\x93 DENR Inventory Management System</title>',
    '<title>Login &mdash; Quanby Procurement</title>'
)
# Also catch the mojibake version
login = login.replace(
    '<title>Login â€" DENR Inventory Management System</title>',
    '<title>Login &mdash; Quanby Procurement</title>'
)

# Brand colors -> Quanby navy/teal
login = login.replace('--denr-green: #006c35; --denr-accent: #8dc63f;', '--denr-green: #1e3a5f; --denr-accent: #00d4c8;')
login = login.replace('.btn-login:hover { background: #00893f;', '.btn-login:hover { background: #254a78;')

# Remove gov bar
login = login.replace(
    '  <div class="gov-bar">Republic of the Philippines | Office of the President | Department of Environment and Natural Resources</div>\n',
    ''
)

# Replace DENR logo icon + heading + subtitle
login = login.replace(
    'DENR IMS</h4>',
    'Quanby Procurement</h4>'
)
login = login.replace(
    'Department of Environment and Natural Resources<br>Inventory Management System</p>',
    'Quanby Solutions, Inc.<br>Inventory &amp; Procurement System with GAM Reports</p>'
)

# Fix placeholder
login = login.replace('placeholder="you@denr.gov.ph"', 'placeholder="your@email.com"')

# Footer note
login = login.replace(
    'Authorized users only &mdash; BCS / PCO Personnel',
    'Authorized users only &mdash; Quanby Solutions, Inc.'
)

with open('/var/www/bcs-ims/resources/views/auth/login.blade.php', 'w', encoding='utf-8') as f:
    f.write(login)

print('Login rebranded')
# Verify
for line in login.split('\n'):
    if 'DENR' in line or 'denr.gov' in line or 'Environment' in line:
        print('STILL HAS DENR:', line.strip())
