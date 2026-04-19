import json
with open('/var/www/quanby-legal/backend/data/appointments.json') as f:
    a = json.load(f)
active = [(k, v) for k, v in a.items() if v.get('session_status') == 'active']
print('Active sessions:', len(active))
for aid, apt in active:
    print(aid[:12], '| room:', apt.get('session_room_name'), '| enp:', apt.get('enp_email'))
