with open('/var/www/quanby-legal/session.html', 'r', encoding='utf-8') as f:
    src = f.read()

livekit_tag = '<script src="https://cdn.jsdelivr.net/npm/livekit-client@2/dist/livekit-client.umd.min.js"></script>'
qlauth_tag = '<script src="/assets/ql-auth.js"></script>\n' + livekit_tag

if '/assets/ql-auth.js' not in src:
    if livekit_tag in src:
        src = src.replace(livekit_tag, qlauth_tag)
        print('ql-auth.js added before livekit')
    else:
        print('Could not find livekit tag')
else:
    print('ql-auth.js already present')

# Fix authFetch to use a safe fallback
old_authfetch = "const r = await QLAuth.authFetch('/api/sessions/join',"
new_authfetch = """var _safeAuthFetch = (typeof QLAuth !== 'undefined' && QLAuth.authFetch) ? QLAuth.authFetch.bind(QLAuth) : function(u, o) { if (o) o.credentials = 'include'; return fetch(u, o); };
      const r = await _safeAuthFetch('/api/sessions/join',"""

if old_authfetch in src:
    src = src.replace(old_authfetch, new_authfetch)
    print('authFetch fallback added')
elif '_safeAuthFetch' in src:
    print('authFetch fallback already present')
else:
    print('authFetch pattern not found')

with open('/var/www/quanby-legal/session.html', 'w', encoding='utf-8') as f:
    f.write(src)
print('session.html saved')
