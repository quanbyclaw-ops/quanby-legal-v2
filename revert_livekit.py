import re

# Revert to the original LiveKit project that was confirmed working
OLD_URL    = 'wss://quanby-lms-k4aq44qe.livekit.cloud'
OLD_KEY    = 'APIfmzJ2GVEV3TJ'
OLD_SECRET = 'sTxyVlCJaPF9QMJTevLvT1xRmSPiXSZXZnLgGoJsIOH'

NEW_URL    = 'wss://quanby-legal-9ccf7xyj.livekit.cloud'
NEW_KEY    = 'APIiozAeJr6tmXG'
NEW_SECRET = 'ZANJ3xNOL5rherRyxhII2vqN5RfP6TU6qmR0zsMcxsA'

with open('/var/www/quanby-legal/backend/main.py', 'r') as f:
    src = f.read()

src = src.replace(NEW_KEY, OLD_KEY)
src = src.replace(NEW_SECRET, OLD_SECRET)
src = src.replace(NEW_URL, OLD_URL)

with open('/var/www/quanby-legal/backend/main.py', 'w') as f:
    f.write(src)

# Fix .env
import subprocess
subprocess.run(['sed', '-i', f's|LIVEKIT_URL=.*|LIVEKIT_URL={OLD_URL}|', '/var/www/quanby-legal/backend/.env'])
subprocess.run(['sed', '-i', f's|LIVEKIT_API_KEY=.*|LIVEKIT_API_KEY={OLD_KEY}|', '/var/www/quanby-legal/backend/.env'])
subprocess.run(['sed', '-i', f's|LIVEKIT_API_SECRET=.*|LIVEKIT_API_SECRET={OLD_SECRET}|', '/var/www/quanby-legal/backend/.env'])

# Fix session.html
with open('/var/www/quanby-legal/session.html', 'r') as f:
    ses = f.read()
ses = ses.replace(NEW_URL, OLD_URL)
with open('/var/www/quanby-legal/session.html', 'w') as f:
    f.write(ses)

print('Reverted to original LiveKit project (Quanby LMS)')
print('URL:', OLD_URL)
print('Key:', OLD_KEY)

# Verify
with open('/var/www/quanby-legal/backend/.env') as f:
    for line in f:
        if 'LIVEKIT' in line:
            print(line.strip())
