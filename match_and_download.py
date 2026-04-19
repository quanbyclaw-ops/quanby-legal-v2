import urllib.request
import re
import os
import html as html_lib

DEST = '/var/www/quanby-legal/assets/partners'
os.makedirs(DEST, exist_ok=True)

# Fetch folder page
url = 'https://drive.google.com/drive/folders/142hrwV7iQMNivhn26VxevyeZKMAr0k2o'
req = urllib.request.Request(url, headers={
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0.0.0',
    'Accept': 'text/html',
})
with urllib.request.urlopen(req, timeout=20) as r:
    raw = r.read().decode('utf-8', errors='replace')

# Decode HTML entities
page = html_lib.unescape(raw)

# Find all file IDs from /file/d/ or data-id
file_ids = re.findall(r'/file/d/([a-zA-Z0-9_-]{25,})', page)
file_ids += re.findall(r'data-id="([a-zA-Z0-9_-]{25,})"', page)
file_ids = list(dict.fromkeys(file_ids))  # dedupe preserving order
print('Total unique file IDs:', len(file_ids))

# Try to match IDs with filenames by looking at surrounding context
# Find all filename occurrences and nearby IDs
filename_map = {}
filenames_of_interest = [
    'DICT Commercial Logo for dark backgrounds.png',
    'DOC - Horizontal w Slogan - White Gradient (Gradient).png',
    'DOC - Horizontal w Slogan - RGB Colors (Gradient).png',
    'Hyperledger Fabric Logo.png',
    'Linux Foundation-horizontal-white.png',
    'Linux Foundation-horizontal-color.png',
    'PNPKI logo.jpg.jpeg',
    'SC-Logo-with-halo-thin-scaled-1024x1024.png',
    'Proptech Logo.png',
]

for fname in filenames_of_interest:
    idx = page.find(fname)
    if idx < 0:
        # Try shorter match
        short = fname.split('.')[0][:20]
        idx = page.find(short)
    if idx < 0:
        print('NOT FOUND in page:', fname)
        continue
    # Look for a file ID within 3000 chars before this filename
    surrounding = page[max(0, idx-3000):idx+500]
    nearby_ids = re.findall(r'["\']([a-zA-Z0-9_-]{33})["\']', surrounding)
    # The last one closest to filename is most likely
    if nearby_ids:
        # Pick the one that's actually in our file_ids list
        matched = [i for i in reversed(nearby_ids) if i in file_ids]
        fid = matched[0] if matched else nearby_ids[-1]
        filename_map[fname] = fid
        print(f'MATCHED: {fname[:50]} -> {fid}')
    else:
        print(f'NO ID found near: {fname}')

print()
print('Matched', len(filename_map), 'files')

# Map to our output filenames
output_map = {
    'DICT Commercial Logo for dark backgrounds.png':              ('dict-logo.png',              'DICT'),
    'DOC - Horizontal w Slogan - White Gradient (Gradient).png':  ('doc-logo-white.png',          'DOCONCHAIN white'),
    'DOC - Horizontal w Slogan - RGB Colors (Gradient).png':      ('doc-logo-color.png',          'DOCONCHAIN color'),
    'Hyperledger Fabric Logo.png':                                 ('hyperledger-logo.png',        'Hyperledger'),
    'Linux Foundation-horizontal-white.png':                       ('linux-foundation-logo.png',   'LF white'),
    'Linux Foundation-horizontal-color.png':                       ('linux-foundation-color.png',  'LF color'),
    'PNPKI logo.jpg.jpeg':                                         ('pnpki-logo.jpg',              'PNPKI'),
    'SC-Logo-with-halo-thin-scaled-1024x1024.png':                ('sc-logo.png',                 'SC'),
    'Proptech Logo.png':                                           ('proptech-logo.png',           'Proptech'),
}

def download_file(file_id, out_path, label):
    dl_url = f'https://drive.google.com/uc?export=download&id={file_id}&confirm=t'
    req2 = urllib.request.Request(dl_url, headers={
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64)',
    })
    try:
        with urllib.request.urlopen(req2, timeout=30) as r:
            data = r.read()
        # Check it's actually an image
        if data[:4] in (b'\x89PNG', b'\xff\xd8\xff') or data[:4] == b'<svg' or b'PNG' in data[:16] or b'JFIF' in data[:16]:
            with open(out_path, 'wb') as f:
                f.write(data)
            print(f'  OK: {label} ({len(data)} bytes) -> {out_path}')
            return True
        elif b'<!DOCTYPE' in data[:100] or b'<html' in data[:100]:
            print(f'  FAIL: {label} got HTML (virus warning page) - trying confirm URL')
            # Try with confirm param
            confirm_url = f'https://drive.usercontent.google.com/download?id={file_id}&export=download&confirm=t&uuid=x'
            req3 = urllib.request.Request(confirm_url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req3, timeout=30) as r3:
                data3 = r3.read()
            if len(data3) > 1000 and b'<!DOCTYPE' not in data3[:100]:
                with open(out_path, 'wb') as f:
                    f.write(data3)
                print(f'  OK via usercontent: {label} ({len(data3)} bytes)')
                return True
            else:
                print(f'  STILL FAILED: {label}')
                return False
        else:
            print(f'  UNKNOWN format: {label} first bytes: {data[:16]}')
            with open(out_path, 'wb') as f:
                f.write(data)
            return True
    except Exception as e:
        print(f'  ERROR: {label}: {e}')
        return False

print()
print('=== Downloading ===')
for fname, (outfile, label) in output_map.items():
    fid = filename_map.get(fname)
    if not fid:
        print(f'SKIP (no ID): {label}')
        continue
    out_path = os.path.join(DEST, outfile)
    download_file(fid, out_path, label)

print()
print('=== Results ===')
for f in os.listdir(DEST):
    p = os.path.join(DEST, f)
    print(f'  {f}: {os.path.getsize(p)} bytes')
