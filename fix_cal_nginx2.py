with open('/etc/nginx/sites-enabled/quanbyai-website', 'r') as f:
    src = f.read()

import re
# Remove the broken block entirely
src = re.sub(
    r'    location /cal-api/ \{[^}]+\}\n\n',
    '',
    src
)

# Re-add clean version
old = '    location = /calendar.html {'
new = ('    location /cal-api/ {\n'
       '        proxy_pass http://127.0.0.1:8090;\n'
       '    }\n\n'
       '    location = /calendar.html {')

if old in src:
    src = src.replace(old, new, 1)
    print('Cal API proxy added clean')
else:
    print('Not found')

with open('/etc/nginx/sites-enabled/quanbyai-website', 'w') as f:
    f.write(src)
