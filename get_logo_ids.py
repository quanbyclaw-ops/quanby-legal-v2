import urllib.request
import re
import json

# Fetch the folder page with proper headers
url = 'https://drive.google.com/drive/folders/142hrwV7iQMNivhn26VxevyeZKMAr0k2o'
req = urllib.request.Request(url, headers={
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml',
    'Accept-Language': 'en-US,en;q=0.9',
})
with urllib.request.urlopen(req, timeout=20) as r:
    html = r.read().decode('utf-8', errors='replace')

print('Page length:', len(html))

# Try to find file IDs - Google Drive embeds them in JSON blobs
# Pattern 1: file id in data-id attributes
ids_data = re.findall(r'data-id="([a-zA-Z0-9_-]{25,})"', html)
# Pattern 2: "id" in JSON
ids_json = re.findall(r'"([a-zA-Z0-9_-]{33})"', html)
# Pattern 3: /file/d/ID
ids_file = re.findall(r'/file/d/([a-zA-Z0-9_-]{25,})', html)

all_ids = list(set(ids_data + ids_file))
print('IDs found (data-id + /file/d/):', len(all_ids))
for i in all_ids[:20]:
    print(' ', i)

# Save html snippet around DICT for debugging
idx = html.find('DICT')
if idx > 0:
    print('\nSnippet around DICT:')
    print(html[max(0,idx-200):idx+500])
