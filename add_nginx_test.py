with open('/etc/nginx/sites-enabled/quanby-legal', 'r') as f:
    src = f.read()

old = '    location = /session      { try_files /session.html /index.html; }'
new = '    location = /session      { try_files /session.html /index.html; }\n    location = /test/room    { try_files /test-room.html /index.html; add_header Cache-Control "no-cache" always; }'

if old in src:
    src = src.replace(old, new)
    with open('/etc/nginx/sites-enabled/quanby-legal', 'w') as f:
        f.write(src)
    print('nginx route added')
else:
    print('not found')
