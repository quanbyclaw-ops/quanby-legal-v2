import json
with open('/var/www/quanby-legal/backend/data/appointments.json') as f:
    apts = json.load(f)

apt_id = 'dbe70548-1de7-452b-9f04-15a3f84ce1ae'
apt = apts.get(apt_id, {})
if apt:
    print('apt_id:', apt.get('apt_id'))
    print('status:', apt.get('status'))
    print('session_status:', apt.get('session_status'))
    print('session_room_name:', apt.get('session_room_name'))
    print('enp_id:', apt.get('enp_id'))
    print('client_id:', apt.get('client_id'))
else:
    print('Appointment not found. Recent appointments:')
    items = sorted(apts.items(), key=lambda x: x[1].get('created_at',''), reverse=True)[:5]
    for aid, a in items:
        print(' ', aid[:20], '| status:', a.get('status'), '| session:', a.get('session_status'), '| room:', bool(a.get('session_room_name')))
