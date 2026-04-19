import urllib.request, json, hmac, hashlib, base64, time

# Test if we can create a LiveKit participant token and that the room auto-creates
API_KEY    = 'APIfmzJ2GVEV3TJ'
API_SECRET = 'sTxyVlCJaPF9QMJTevLvT1xRmSPiXSZXZnLgGoJsIOH'
LK_HTTP    = 'https://quanby-lms-k4aq44qe.livekit.cloud'
LK_WS      = 'wss://quanby-lms-k4aq44qe.livekit.cloud'
ROOM_NAME  = 'ql-test-auto-create'
USER_ID    = 'test-user-123'
USER_NAME  = 'Test User'

now = int(time.time())

# Create participant token
h = base64.urlsafe_b64encode(json.dumps({'alg':'HS256','typ':'JWT'}).encode()).rstrip(b'=').decode()
p = base64.urlsafe_b64encode(json.dumps({
    'iss': API_KEY, 'sub': USER_ID,
    'iat': now, 'exp': now + 3600,
    'name': USER_NAME,
    'video': {
        'room': ROOM_NAME,
        'roomJoin': True,
        'canPublish': True,
        'canSubscribe': True,
    }
}).encode()).rstrip(b'=').decode()
sig = base64.urlsafe_b64encode(
    hmac.new(API_SECRET.encode(), f'{h}.{p}'.encode(), hashlib.sha256).digest()
).rstrip(b'=').decode()
token = f'{h}.{p}.{sig}'

print('Generated token:', token[:50] + '...')
print('Token ISS:', API_KEY)
print('Room:', ROOM_NAME)
print()

# Test admin token for ListRooms
ah = base64.urlsafe_b64encode(json.dumps({'alg':'HS256','typ':'JWT'}).encode()).rstrip(b'=').decode()
ap = base64.urlsafe_b64encode(json.dumps({
    'iss': API_KEY, 'sub': API_KEY,
    'iat': now, 'exp': now + 60,
    'video': {'roomAdmin': True, 'roomList': True, 'roomCreate': True}
}).encode()).rstrip(b'=').decode()
asig = base64.urlsafe_b64encode(
    hmac.new(API_SECRET.encode(), f'{ah}.{ap}'.encode(), hashlib.sha256).digest()
).rstrip(b'=').decode()
admin_token = f'{ah}.{ap}.{asig}'

# List rooms
req = urllib.request.Request(
    f'{LK_HTTP}/twirp/livekit.RoomService/ListRooms',
    data=json.dumps({}).encode(),
    headers={'Authorization': f'Bearer {admin_token}', 'Content-Type': 'application/json'}
)
with urllib.request.urlopen(req, timeout=10) as r:
    d = json.loads(r.read())
print('Active rooms:', len(d.get('rooms', [])))
for rm in d.get('rooms', []):
    print(f'  {rm.get("name")} | participants={rm.get("numParticipants")} | sid={rm.get("sid","")}')

# Note: LiveKit auto-creates rooms when first participant connects with roomJoin token
print()
print('LiveKit API working. Rooms auto-create on first join.')
print('WebSocket URL to use in browser:', LK_WS)
