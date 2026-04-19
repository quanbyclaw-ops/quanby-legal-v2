with open('/var/www/quanby-legal/index.html', 'r', encoding='utf-8') as f:
    src = f.read()

old = 'style="display:none;">Sign In</button>'
new = 'style="display:inline-block;">Sign In</button>'

count = src.count(old)
print('Found:', count, 'instances')
if count:
    src = src.replace(old, new, 1)  # only first instance (the nav one)
    with open('/var/www/quanby-legal/index.html', 'w', encoding='utf-8') as f:
        f.write(src)
    print('Fixed: Sign In button visible by default')
else:
    # Find where it is
    idx = src.find('nav-signin-btn')
    print('nav-signin-btn at:', idx)
    print('Context:', src[idx:idx+120])
