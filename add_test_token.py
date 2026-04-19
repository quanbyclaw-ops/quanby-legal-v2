with open('/var/www/quanby-legal/backend/main.py', 'r', encoding='utf-8') as f:
    src = f.read()

test_endpoint = '''
# ─── GET /api/test/token ─────────────────────────────────────────────────────
# No auth required — pure LiveKit test endpoint

@app.get("/api/test/token")
async def test_livekit_token(room: str = "test-room", user: str = "tester"):
    """Generate a LiveKit token for testing — no auth needed."""
    token = _create_livekit_token(room, user, user, can_publish=True)
    return {
        "token": token,
        "room": room,
        "user": user,
        "url": _LIVEKIT_URL,
        "api_key": os.getenv("LIVEKIT_API_KEY", ""),
    }


'''

target = '@app.get("/api/sessions/my-ip")'
if '/api/test/token' not in src and target in src:
    src = src.replace(target, test_endpoint + target)
    with open('/var/www/quanby-legal/backend/main.py', 'w', encoding='utf-8') as f:
        f.write(src)
    print('Test token endpoint added')
elif '/api/test/token' in src:
    print('Already exists')
else:
    print('Target not found')
