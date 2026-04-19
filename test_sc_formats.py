import json, urllib.request

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

# Get SC token
auth_body = json.dumps({'AuthFlow':'USER_PASSWORD_AUTH','AuthParameters':{'USERNAME':SC_USER,'PASSWORD':SC_PASS},'ClientId':SC_CLIENT}).encode()
auth_req = urllib.request.Request(SC_AUTH, data=auth_body, headers={'Content-Type':'application/x-amz-json-1.1','X-Amz-Target':'AWSCognitoIdentityProviderService.InitiateAuth'}, method='POST')
with urllib.request.urlopen(auth_req, timeout=15) as r:
    sc_token = json.loads(r.read().decode()).get('AuthenticationResult',{}).get('IdToken','')
print('Token OK')

# Try consolidated with NO NPN validation — just the NFN and roll
# SC may accept without NPN on staging
test_cases = [
    # (npn, rn, notes)
    ('69750', '69750', 'raw numbers'),
    ('NPN-69750', 'RN-69750', 'prefixed'),
    (SC_NFN, '69750', 'NFN as NPN'),
    ('', '69750', 'empty NPN'),
    ('2024-024', '69750', 'commission as NPN'),
    ('NPN-2024-024', 'RN-69750', 'commission prefixed'),
]

def try_consolidated(npn, rn, note):
    payload = {
        'notaryFacilityNumber': SC_NFN,
        'notaryPublicNumber': npn,
        'rollNumber': rn,
        'metaData': {
            'dateNotarized': '2026-04-14',
            'notarialActType': 'Acknowledgment',
            'notarialPageNumber': 1,
            'notarialBookNumber': 1,
            'description': 'Test Document',
            'modeOfNotarization': 'Remote Online',
            'remarks': 'Test',
            'dateUpdated': '2026-04-14'
        },
        'listOfPrincipals': [{'principalName':'Test Principal','principalAddress':{'homeStreet':'N/A','barangay':'N/A','cityProvince':'Legazpi City, Albay'}}],
        'listOfWitness': []
    }
    req = urllib.request.Request(
        SC_URL+'/public-use/consolidated',
        data=json.dumps(payload).encode(),
        headers={'Content-Type':'application/json','Authorization':'Bearer '+sc_token},
        method='POST'
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            resp = r.read().decode()
            print(f'[{note}] NPN={npn} RN={rn} -> SUCCESS: {resp[:200]}')
            return True
    except Exception as e:
        body = ''
        try: body = e.read().decode()
        except: pass
        print(f'[{note}] NPN={npn} RN={rn} -> {e.code if hasattr(e,"code") else ""} {body[:150]}')
        return False

for npn, rn, note in test_cases:
    if try_consolidated(npn, rn, note):
        break
