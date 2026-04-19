import re

with open('/var/www/quanby-legal/registry.html', 'r', encoding='utf-8') as f:
    src = f.read()

# Extract all inline scripts
scripts = re.findall(r'<script[^>]*>(.*?)</script>', src, re.DOTALL)
inline_js = '\n'.join(s for s in scripts if 'src=' not in s[:30])

print('File size:', len(src))
print('Inline JS chars:', len(inline_js))

# Check for common issues
issues = []

# 1. Stray return null
if '    return null;' in inline_js:
    idx = inline_js.find('    return null;')
    ctx = inline_js[max(0,idx-200):idx+50]
    if 'function' not in ctx[-200:]:
        issues.append('STRAY return null outside function')

# 2. Unmatched quotes in string concatenations
bad_patterns = [
    (",'_blank')", "'_blank' in string concat"),
    (',"_blank")', '"_blank" in string concat'),
]
for pat, desc in bad_patterns:
    if pat in inline_js:
        issues.append(f'Bad pattern: {desc}')

# 3. Basic brace balance
opens = inline_js.count('{')
closes = inline_js.count('}')
if abs(opens - closes) > 2:
    issues.append(f'Brace imbalance: {opens} open vs {closes} close')

# 4. Check specific function exists
required_fns = ['function boot', 'function loadActs', 'function renderTable',
                'function openInNewTab', 'function openDocViewer', 'function closeDocViewer',
                'function syncSC', 'function toggleDetail']
for fn in required_fns:
    if fn not in inline_js:
        issues.append(f'MISSING function: {fn}')

if issues:
    print()
    print('ISSUES FOUND:')
    for i in issues:
        print(' -', i)
else:
    print('No obvious issues found')
