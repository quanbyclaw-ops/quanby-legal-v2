with open('/var/www/quanby-legal/session.html', 'r', encoding='utf-8') as f:
    src = f.read()

old1 = "    if (!r.ok) { location.href = '/'; return; }\n    me = await r.json();"
new1 = "    if (!r.ok) { QLAuth._handleReauth(); return; }\n    me = await r.json();"

old2 = "  } catch(e) { location.href = '/'; return; }"
new2 = "  } catch(e) { console.warn('[Session] auth failed', e); QLAuth._handleReauth(); return; }"

c = 0
if old1 in src:
    src = src.replace(old1, new1)
    c += 1
    print('Fixed auth check redirect')
if old2 in src:
    src = src.replace(old2, new2)
    c += 1
    print('Fixed catch redirect')

with open('/var/www/quanby-legal/session.html', 'w', encoding='utf-8') as f:
    f.write(src)
print('Done, changes:', c)
