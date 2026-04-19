import json, urllib.request, os

env = {}
with open('/var/www/quanby-legal/backend/.env') as f:
    for line in f:
        line = line.strip()
        if '=' in line and not line.startswith('#'):
            k, v = line.split('=', 1)
            env[k] = v.strip('"\'')

SC_URL    = env.get('SUPREME_COURT_API_URL','')
SC_AUTH   = env.get('SUPREME_COURT_AUTH_URL','')
SC_CLIENT = env.get('SUPREME_COURT_CLIENT_ID','')
SC_USER   = env.get('SUPREME_COURT_USERNAME','')
SC_PASS   = env.get('SUPREME_COURT_PASSWORD','')
SC_NFN    = env.get('SUPREME_COURT_NFN','NFN-2025-00017')

# Get Cognito token
print('Getting SC token...')
auth_body = json.dumps({
    'AuthFlow': 'USER_PASSWORD_AUTH',
    'AuthParameters': {'USERNAME': SC_USER, 'PASSWORD': SC_PASS},
    'ClientId': SC_CLIENT
}).encode()
auth_req = urllib.request.Request(
    SC_AUTH, data=auth_body,
    headers={'Content-Type': 'application/x-amz-json-1.1', 'X-Amz-Target': 'AWSCognitoIdentityProviderService.InitiateAuth'},
    method='POST'
)
with urllib.request.urlopen(auth_req, timeout=15) as r:
    auth_resp = json.loads(r.read().decode())
sc_token = auth_resp.get('AuthenticationResult', {}).get('IdToken', '')
print('SC Token len:', len(sc_token))

# Test CS endpoint
print('\nTesting /public-use/cs...')
cs_body = json.dumps({'npn': 'NPN-2024 - 024', 'rn': 'RN-69750'}).encode()
cs_req = urllib.request.Request(
    SC_URL + '/public-use/cs', data=cs_body,
    headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + sc_token},
    method='POST'
)
try:
    with urllib.request.urlopen(cs_req, timeout=15) as r:
        print('CS OK:', r.read().decode()[:200])
except Exception as e:
    body = ''
    try: body = e.read().decode()
    except: pass
    print('CS error:', e.code if hasattr(e,'code') else e, body[:300])

# Test consolidated with various NPN formats
for npn_fmt in ['NPN-2024 - 024', '2024 - 024', 'NPN-2024-024', '2024024']:
    print(f'\nTesting consolidated NPN={npn_fmt}...')
    payload = {
        'notaryFacilityNumber': SC_NFN,
        'notaryPublicNumber': npn_fmt,
        'rollNumber': 'RN-69750',
        'metaData': {
            'dateNotarized': '2026-04-14',
            'notarialActType': 'Acknowledgment',
            'notarialPageNumber': 1,
            'notarialBookNumber': 1,
            'description': 'file_sample',
            'modeOfNotarization': 'Remote Online',
            'remarks': 'Test notarization',
            'dateUpdated': '2026-04-14'
        },
        'listOfPrincipals': [{
            'principalName': 'Mj Balcueva',
            'principalAddress': {
                'homeStreet': 'N/A',
                'barangay': 'N/A',
                'cityProvince': 'Legazpi City, Albay'
            }
        }],
        'listOfWitness': []
    }
    con_body = json.dumps(payload).encode()
    con_req = urllib.request.Request(
        SC_URL + '/public-use/consolidated', data=con_body,
        headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + sc_token},
        method='POST'
    )
    try:
        with urllib.request.urlopen(con_req, timeout=15) as r:
            print('OK:', r.read().decode()[:300])
            break
    except Exception as e:
        body = ''
        try: body = e.read().decode()
        except: pass
        print('Error', e.code if hasattr(e, 'code') else '', body[:200])
