import urllib.request, re

r = urllib.request.urlopen('https://quanbyai.com/calendar.html', timeout=10)
html = r.read().decode()

creds_match = re.search(r'var CREDS = \{.*?\};', html)
check_match = re.search(r'if \(CREDS.*?\) \{', html)
print('CREDS line:', creds_match.group() if creds_match else 'NOT FOUND')
print('Check line:', check_match.group() if check_match else 'NOT FOUND')

users = re.findall(r"'([\w]+)'", creds_match.group() if creds_match else '')
pw = re.search(r'pass: .([^.]+).', creds_match.group() if creds_match else '')
print('Users found:', users)
print('Password match:', pw.group(0) if pw else 'NOT FOUND')
