with open('/var/www/quanby-legal/registry.html', 'r', encoding='utf-8') as f:
    src = f.read()

# Simple fix: override authMeWithRetry to use 3 retries instead of 6
# Insert right after ql-auth.js is loaded
old_script = '<script src="/assets/ql-auth.js"></script>'
new_script = '''<script src="/assets/ql-auth.js"></script>
<script>
// Override to use 3 retries (faster) for registry page
document.addEventListener('DOMContentLoaded', function() {
  if (window.QLAuth && QLAuth.authMeWithRetry) {
    var _orig = QLAuth.authMeWithRetry;
    QLAuth.authMeWithRetry = function(max) { return _orig(3); };
  }
});
</script>'''

if old_script in src and 'Override to use 3 retries' not in src:
    src = src.replace(old_script, new_script)
    print('Fix: auth reduced to 3 retries max')
else:
    print('Already patched or not found')

# Also show content div background immediately
if 'background:#0d0f1a;color:#e2e8f0' not in src:
    src = src.replace('<body style="background:#0d0f1a;color:#e6edf3;">', '<body style="background:#0d0f1a;color:#e2e8f0;">')
    print('Body bg confirmed')

with open('/var/www/quanby-legal/registry.html', 'w', encoding='utf-8') as f:
    f.write(src)
print('Saved')
