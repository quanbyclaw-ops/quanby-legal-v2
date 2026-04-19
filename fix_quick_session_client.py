with open('/var/www/quanby-legal/backend/main.py', 'r', encoding='utf-8') as f:
    src = f.read()

old = '''        "client_id": user["id"],       # ENP is also the host
        "client_name": enp_name,
        "client_email": user.get("email", ""),'''

new = '''        "client_id": None,              # Quick session — no client booked
        "client_name": "",
        "client_email": "",'''

if old in src:
    src = src.replace(old, new)
    with open('/var/www/quanby-legal/backend/main.py', 'w', encoding='utf-8') as f:
        f.write(src)
    print('Fixed')
else:
    print('Not found — checking context')
    idx = src.find('is_quick_session')
    print('is_quick_session at:', idx)
    print('Context:', src[max(0,idx-300):idx+50])
