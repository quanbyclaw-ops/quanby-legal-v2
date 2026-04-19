import urllib.request, json, hmac, hashlib, base64, time

API_KEY    = 'APIiozAeJr6tmXG'
API_SECRET = 'ZANJ3xNOL5rherRyxhII2vqN5RfP6TU6qmR0zsMcxsA'
LK_URL     = 'https://quanby-legal-9ccf7xyj.livekit.cloud'

now = int(time.time())
header  = base64.urlsafe_b64encode(json.dumps({'alg':'HS256','typ':'JWT'}).encode()).rstrip(b'=').decode()
payload = base64.urlsafe_b64encode(json.dumps({
    'iss': API_KEY, 'sub': API_KEY, 'iat': now, 'exp': now+60,
    'video': {'roomAdmin': True, 'roomList': True}
}).encode()).rstrip(b'=').decode()
sig = base64.urlsafe_b64encode(
    hmac.new(API_SECRET.encode(), f'{header}.{payload}'.encode(), hashlib.sha256).digest()
).rstrip(b'=').decode()
token = f'{header}.{payload}.{sig}'

req = urllib.request.Request(
    f'{LK_URL}/twirp/livekit.RoomService/ListRooms',
    data=json.dumps({}).encode(),
    headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
)
try:
    with urllib.request.urlopen(req, timeout=10) as r:
        data = json.loads(r.read())
    rooms = data.get('rooms', [])
    print(f'Active rooms on quanby-legal-9ccf7xyj: {len(rooms)}')
    for room in rooms:
        print(f'  {room.get("name")} | participants: {room.get("numParticipants")}')
    if not rooms:
        print('NO rooms — LiveKit auto-creates rooms on first participant join')
        print('Testing: creating room ql-fefe5e10-1776134792...')
        req2 = urllib.request.Request(
            f'{LK_URL}/twirp/livekit.RoomService/CreateRoom',
            data=json.dumps({'name': 'ql-test-room', 'empty_timeout': 300}).encode(),
            headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
        )
        with urllib.request.urlopen(req2, timeout=10) as r2:
            d2 = json.loads(r2.read())
        print('Created room:', d2.get('name'), 'sid:', d2.get('sid'))
except Exception as e:
    print('Error:', e)
