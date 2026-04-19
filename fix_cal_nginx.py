with open('/etc/nginx/sites-enabled/quanbyai-website', 'r') as f:
    src = f.read()

old = '    location / {\n        try_files $uri $uri/ /index.html;\n    }'
new = ('    location = /calendar.html {\n'
       '        try_files $uri =404;\n'
       '        add_header Cache-Control "no-cache, no-store, must-revalidate" always;\n'
       '        add_header Pragma "no-cache" always;\n'
       '    }\n\n'
       '    location / {\n'
       '        try_files $uri $uri/ /index.html;\n'
       '    }')

if old in src:
    src = src.replace(old, new)
    with open('/etc/nginx/sites-enabled/quanbyai-website', 'w') as f:
        f.write(src)
    print('nginx updated')
else:
    print('Pattern not found')
