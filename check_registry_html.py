with open('/var/www/quanby-legal/registry.html') as f:
    content = f.read()

print('File size:', len(content))
print('Has DOCTYPE:', '<!DOCTYPE' in content)
print('Has stray return null:', '    return null;' in content and 'async function boot' in content[content.find('    return null;')-200:content.find('    return null;')])
print('boot() call:', 'boot();' in content)
print('QL Auth script:', 'ql-auth.js' in content)
print('Brace balance:', content.count('{') - content.count('}'))

# Check for JS errors
import re
scripts = re.findall(r'<script[^>]*>(.*?)</script>', content, re.DOTALL)
total_js = '\n'.join(s for s in scripts if 'src=' not in s[:20])
print('Total JS chars:', len(total_js))

# Look for the issue area
idx = content.find('return null')
if idx > 0:
    ctx = content[max(0,idx-200):idx+100]
    print('Context around return null:')
    print(ctx)
