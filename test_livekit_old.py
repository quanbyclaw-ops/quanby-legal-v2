import urllib.request, json, hmac, hashlib, base64, time

API_KEY    = 'APIfmzJ2GVEV3TJ'
API_SECRET = 'sTxyVlCJaPF9QMJTevLvT1xRmSPiXSZXZnLgGoJsIOH'
LK_URL     = 'https://quanby-lms-k4aq44qe.livekit.cloud'

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

# List rooms
req = urllib.request.Request(
    f'{LK_URL}/twirp/livekit.RoomService/ListRooms',
    data=json.dumps({}).encode(),
    headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
)
with urllib.request.urlopen(req, timeout=10) as r:
    data = json.loads(r.read())
rooms = data.get('rooms', [])
print(f'Original LK project OK — Active rooms: {len(rooms)}')
for room in rooms:
    print(f'  {room.get("name")} | participants: {room.get("numParticipants")}')

# Create a test room
req2 = urllib.request.Request(
    f'{LK_URL}/twirp/livekit.RoomService/CreateRoom',
    data=json.dumps({'name': 'ql-test-connection', 'empty_timeout': 60}).encode(),
    headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
)
with urllib.request.urlopen(req2, timeout=10) as r2:
    d2 = json.loads(r2.read())
print(f'Created test room: {d2.get("name")} sid={d2.get("sid")}')
print('LiveKit is WORKING on original project!')
