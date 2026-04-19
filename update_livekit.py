import re

# ─── Update main.py ───────────────────────────────────────────────────────────
with open('/var/www/quanby-legal/backend/main.py', 'r') as f:
    src = f.read()

NEW_URL    = 'wss://quanby-legal-9ccf7xyj.livekit.cloud'
NEW_KEY    = 'APIiozAeJr6tmXG'
NEW_SECRET = 'ZANJ3xNOL5rherRyxhII2vqN5RfP6TU6qmR0zsMcxsA'

# Replace hardcoded strings
replacements = [
    ('APIfmzJ2GVEV3TJ',                         NEW_KEY),
    ('sTxyVlCJaPF9QMJTevLvT1xRmSPiXSZXZnLgGoJsIOH', NEW_SECRET),
    ('wss://quanby-lms-k4aq44qe.livekit.cloud', NEW_URL),
]

count = 0
for old, new in replacements:
    n = src.count(old)
    src = src.replace(old, new)
    count += n
    print(f'  Replaced {n}x: {old[:30]} -> {new[:30]}')

# Also update the _LIVEKIT_URL constant if present
src = re.sub(r'_LIVEKIT_URL\s*=\s*["\'].*?["\']', f'_LIVEKIT_URL = os.getenv("LIVEKIT_URL", "{NEW_URL}")', src)

with open('/var/www/quanby-legal/backend/main.py', 'w') as f:
    f.write(src)
print(f'main.py: {count} replacements')

# ─── Update session.html ──────────────────────────────────────────────────────
with open('/var/www/quanby-legal/session.html', 'r') as f:
    ses = f.read()

OLD_WS = 'wss://quanby-lms-k4aq44qe.livekit.cloud'
n_ses = ses.count(OLD_WS)
ses = ses.replace(OLD_WS, NEW_URL)
with open('/var/www/quanby-legal/session.html', 'w') as f:
    f.write(ses)
print(f'session.html: {n_ses} URL replacements')

# ─── Update lobby.html ────────────────────────────────────────────────────────
with open('/var/www/quanby-legal/lobby.html', 'r') as f:
    lob = f.read()
n_lob = lob.count(OLD_WS)
lob = lob.replace(OLD_WS, NEW_URL)
with open('/var/www/quanby-legal/lobby.html', 'w') as f:
    f.write(lob)
print(f'lobby.html: {n_lob} URL replacements')

print('Done — restart service to pick up new .env values')
