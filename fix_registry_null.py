with open('/var/www/quanby-legal/registry.html', 'r', encoding='utf-8') as f:
    src = f.read()

# Fix: wrap the addEventListener in a DOMContentLoaded so element exists
old = "document.getElementById('doc-viewer-overlay').addEventListener('click', function(e) {\n  if (e.target === this) closeDocViewer();\n});"

new = "document.addEventListener('DOMContentLoaded', function() {\n  var _dvo = document.getElementById('doc-viewer-overlay');\n  if (_dvo) _dvo.addEventListener('click', function(e) { if (e.target === this) closeDocViewer(); });\n});"

if old in src:
    src = src.replace(old, new)
    print('Fixed: wrapped in DOMContentLoaded')
else:
    print('Pattern not found - trying line 309 area')
    lines = src.split('\n')
    print('Line 307-312:')
    for i, l in enumerate(lines[305:313], 306):
        print(i, repr(l))

with open('/var/www/quanby-legal/registry.html', 'w', encoding='utf-8') as f:
    f.write(src)
