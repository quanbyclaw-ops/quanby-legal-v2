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
SC_NFN    = env.get('SUPREME_COURT_NFN','')

print(f'SC_URL={SC_URL}')
print(f'SC_NFN={SC_NFN}')
print(f'SC_USER={SC_USER}')

# Get Cognito token
auth_body = json.dumps({'AuthFlow':'USER_PASSWORD_AUTH','AuthParameters':{'USERNAME':SC_USER,'PASSWORD':SC_PASS},'ClientId':SC_CLIENT}).encode()
auth_req = urllib.request.Request(SC_AUTH, data=auth_body,
    headers={'Content-Type':'application/x-amz-json-1.1','X-Amz-Target':'AWSCognitoIdentityProviderService.InitiateAuth'}, method='POST')
with urllib.request.urlopen(auth_req, timeout=15) as r:
    sc_token = json.loads(r.read().decode()).get('AuthenticationResult',{}).get('IdToken','')
print(f'SC token len={len(sc_token)}')

# Try many combinations to find what SC accepts
# Christian's profile: roll_no=69750, commission=2024-024, NPN=69750
test_cases = [
    # (npn, rn, nfn, notes)
    ('NPN-69750',     'RN-69750',  SC_NFN,            'default format'),
    ('69750',         '69750',     SC_NFN,             'raw numbers only'),
    ('NPN-69750',     '69750',     SC_NFN,             'NPN prefix, raw RN'),
    ('69750',         'RN-69750',  SC_NFN,             'raw NPN, RN prefix'),
    ('NPN-2024-024',  'RN-69750',  SC_NFN,             'commission as NPN'),
    ('2024-024',      '69750',     SC_NFN,             'raw commission, raw RN'),
    ('NPN-69750',     'RN-69750',  'NFN-2025-00017',   'hardcoded NFN'),
    ('NFN-2025-00017','RN-69750',  SC_NFN,             'NFN as NPN'),
]

def try_sc(npn, rn, nfn, note):
    for date_fmt in ['2026-04-14', '04/14/2026', '14-04-2026']:
        payload = {
            'notaryFacilityNumber': nfn,
            'notaryPublicNumber': npn,
            'rollNumber': rn,
            'metaData': {
                'dateNotarized': date_fmt,
                'notarialActType': 'Acknowledgment',
                'notarialPageNumber': 1,
                'notarialBookNumber': 1,
                'description': 'Test Document',
                'modeOfNotarization': 'Remote Online',
                'remarks': 'Test notarization by ENP',
                'dateUpdated': date_fmt,
            },
            'listOfPrincipals': [{
                'principalName': 'Test Principal',
                'principalAddress': {
                    'homeStreet': '123 Test Street',
                    'barangay': 'Daraga',
                    'cityProvince': 'Legazpi City, Albay',
                },
            }],
            'listOfWitness': [],
        }
        body = json.dumps(payload).encode()
        req = urllib.request.Request(SC_URL+'/public-use/consolidated', data=body,
            headers={'Content-Type':'application/json','Authorization':'Bearer '+sc_token}, method='POST')
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                resp = r.read().decode()
                print(f'SUCCESS [{note}] NPN={npn} RN={rn} NFN={nfn} date={date_fmt}')
                print('Response:', resp[:300])
                return True
        except Exception as e:
            err = ''
            try: err = e.read().decode()[:150]
            except: pass
            code = e.code if hasattr(e,'code') else '?'
            if code != 400 or 'Rejected' not in err:
                print(f'  [{note}] date={date_fmt} -> {code} {err}')
    return False

found = False
for npn, rn, nfn, note in test_cases:
    if try_sc(npn, rn, nfn, note):
        found = True
        break
    else:
        print(f'FAILED: {note} NPN={npn} RN={rn}')

if not found:
    print('\nAll rejected. Checking if /public-use/consolidated requires specific ENP registration...')
    # Try with completely different test values
    for npn in ['NPN-12345', 'NPN-00001', '12345']:
        payload = {
            'notaryFacilityNumber': SC_NFN,
            'notaryPublicNumber': npn,
            'rollNumber': 'RN-12345',
            'metaData': {'dateNotarized':'2026-04-14','notarialActType':'Acknowledgment',
                         'notarialPageNumber':1,'notarialBookNumber':1,
                         'description':'Test','modeOfNotarization':'Remote Online',
                         'remarks':'Test','dateUpdated':'2026-04-14'},
            'listOfPrincipals': [{'principalName':'Test','principalAddress':{'homeStreet':'N/A','barangay':'N/A','cityProvince':'Test City'}}],
            'listOfWitness': []
        }
        req = urllib.request.Request(SC_URL+'/public-use/consolidated',
            data=json.dumps(payload).encode(),
            headers={'Content-Type':'application/json','Authorization':'Bearer '+sc_token}, method='POST')
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                print(f'SUCCESS with NPN={npn}:', r.read().decode()[:200])
                break
        except Exception as e:
            err = ''
            try: err = e.read().decode()[:100]
            except: pass
            print(f'  NPN={npn}: {e.code if hasattr(e,"code") else ""} {err}')
