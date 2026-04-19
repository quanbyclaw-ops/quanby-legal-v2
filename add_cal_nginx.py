with open('/etc/nginx/sites-enabled/quanbyai-website', 'r') as f:
    src = f.read()

# Remove bad block if added
import re
src = re.sub(r'\s*location /cal-api/[^}]+\}\s*', '\n', src)

old = '    location = /calendar.html {'
new = ('    location /cal-api/ {\n'
       '        proxy_pass http://127.0.0.1:8090;\n'
       '    }\n\n'
       '    location = /calendar.html {')

if old in src and '/cal-api/' not in src:
    src = src.replace(old, new)
    with open('/etc/nginx/sites-enabled/quanbyai-website', 'w') as f:
        f.write(src)
    print('nginx updated')
else:
    print('already done or pattern not found')
