import re

NEW_KEY    = 'APIRn8F2gpDAQHw'
NEW_SECRET = 'NseFKsnBr5rXxWlCTYUz33Hc6l7c64f0W3DHzN18r1eB'
NEW_URL    = 'wss://quanby-lms-k4aq44qe.livekit.cloud'

# Update .env
import subprocess
subprocess.run(['sed', '-i', f's|LIVEKIT_API_KEY=.*|LIVEKIT_API_KEY={NEW_KEY}|', '/var/www/quanby-legal/backend/.env'])
subprocess.run(['sed', '-i', f's|LIVEKIT_API_SECRET=.*|LIVEKIT_API_SECRET={NEW_SECRET}|', '/var/www/quanby-legal/backend/.env'])
subprocess.run(['sed', '-i', f's|LIVEKIT_URL=.*|LIVEKIT_URL={NEW_URL}|', '/var/www/quanby-legal/backend/.env'])

# Update main.py hardcoded values
OLD_KEY = 'APIfmzJ2GVEV3TJ'
OLD_SECRET = 'sTxyVlCJaPF9QMJTevLvT1xRmSPiXSZXZnLgGoJsIOH'
OLD_KEY2 = 'APIiozAeJr6tmXG'
OLD_SECRET2 = 'ZANJ3xNOL5rherRyxhII2vqN5RfP6TU6qmR0zsMcxsA'

with open('/var/www/quanby-legal/backend/main.py', 'r') as f:
    src = f.read()

for old_k in [OLD_KEY, OLD_KEY2]:
    src = src.replace(old_k, NEW_KEY)
for old_s in [OLD_SECRET, OLD_SECRET2]:
    src = src.replace(old_s, NEW_SECRET)

with open('/var/www/quanby-legal/backend/main.py', 'w') as f:
    f.write(src)

# Verify .env
with open('/var/www/quanby-legal/backend/.env') as f:
    for line in f:
        if 'LIVEKIT' in line:
            print(line.strip())

print('Done')
