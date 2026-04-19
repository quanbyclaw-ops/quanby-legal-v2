import json
with open('/tmp/dc_vault.json') as f:
    d = json.load(f)
items = d.get('data', [])
if items:
    print('First vault item fields:')
    print(json.dumps(items[0], indent=2))
