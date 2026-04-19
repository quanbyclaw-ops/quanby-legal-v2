with open('/var/www/quanby-legal/registry.html', 'r', encoding='utf-8') as f:
    src = f.read()

# The black screen = body background not set + auth retry takes 10s
# Fix 1: Add CSS body background so page isn't black while loading
old_body_tag = '<body>'
new_body_tag = '<body style="background:#0d0f1a;color:#e2e8f0;">'
if old_body_tag in src and 'background:#0d0f1a' not in src[:200]:
    src = src.replace(old_body_tag, new_body_tag, 1)
    print('Fix 1: body background set immediately')

# Fix 2: Speed up auth - reduce retries from 6 to 3 for registry
# The ql-auth.js uses authMeWithRetry(6) from requireAuth
# Add a faster timeout by overriding in registry
old_boot = 'async function boot() {'
new_boot = '''async function boot() {
  // Show nav immediately while auth loads
  document.getElementById('nav-name').textContent = '...';'''

if old_boot in src and 'Show nav immediately' not in src:
    src = src.replace(old_boot, new_boot, 1)
    print('Fix 2: nav shows immediately')

with open('/var/www/quanby-legal/registry.html', 'w', encoding='utf-8') as f:
    f.write(src)
print('Done')
