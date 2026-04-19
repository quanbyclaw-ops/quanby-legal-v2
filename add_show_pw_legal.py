import re

SHOW_BTN = (
    '<button type="button" '
    'onclick="var f=this.previousElementSibling;'
    'f.type=f.type===\'password\'?\'text\':\'password\';'
    'this.innerHTML=f.type===\'password\'?\'&#x1F441;\':\'&#x1F648;\'" '
    'style="position:absolute;right:.7rem;top:50%;transform:translateY(-50%);'
    'background:none;border:none;cursor:pointer;font-size:1rem;padding:0;line-height:1;color:#94a3b8;">&#x1F441;</button>'
)

files_patterns = [
    # (file, search_pattern, wrap_in_div)
    ('/var/www/quanby-legal/admin.html', r'<input[^>]*type=["\']password["\'][^>]*id=["\']ql-admin-pass["\'][^>]*>', True),
]

for path, pattern, wrap in files_patterns:
    try:
        with open(path, 'r', encoding='utf-8') as f:
            src = f.read()
        
        m = re.search(pattern, src)
        if m:
            old = m.group(0)
            if wrap:
                # Check if already wrapped
                idx = src.find(old)
                before = src[max(0,idx-30):idx]
                if 'position:relative' in before:
                    print('Already wrapped:', path)
                    continue
                new = '<div style="position:relative;">' + old + SHOW_BTN + '</div>'
            else:
                new = old + SHOW_BTN
            
            src = src.replace(old, new, 1)
            with open(path, 'w', encoding='utf-8') as f:
                f.write(src)
            print('Fixed:', path)
        else:
            print('Pattern not found:', path)
    except FileNotFoundError:
        print('File not found:', path)

# Also add to the Quanby Legal admin login modal (already has show/hide)
# and onboard.html password field if any
print('Done')
