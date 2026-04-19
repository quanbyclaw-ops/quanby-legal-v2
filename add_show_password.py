files = [
    '/var/www/bcs-ims/resources/views/auth/login.blade.php',
    '/var/www/opapru-edms/resources/views/auth/login.blade.php',
]

SHOW_BTN_STYLE = (
    'position:absolute;right:.6rem;top:50%;transform:translateY(-50%);'
    'background:none;border:none;cursor:pointer;font-size:1rem;padding:0;line-height:1;color:#94a3b8;'
)

for path in files:
    with open(path, 'r', encoding='utf-8') as f:
        src = f.read()

    # Wrap password field in a relative div with toggle button
    old = '<input type="password" name="password" class="form-control" placeholder="\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022" required>'
    new = (
        '<div style="position:relative;">'
        '<input type="password" name="password" id="pw-field-' + path[-20:].replace('/','') + '" class="form-control" '
        'placeholder="\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022" required style="padding-right:3rem;">'
        '<button type="button" '
        'onclick="var f=this.previousElementSibling;f.type=f.type===\'password\'?\'text\':\'password\';this.innerHTML=f.type===\'password\'?\'&#x1F441;\':\'&#x1F648;\'" '
        'style="' + SHOW_BTN_STYLE + '">&#x1F441;</button>'
        '</div>'
    )

    if old in src:
        src = src.replace(old, new)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(src)
        print('Fixed:', path)
    else:
        # Find the password input line
        import re
        m = re.search(r'<input\s[^>]*name="password"[^>]*>', src)
        if m:
            old2 = m.group(0)
            # Add id and padding-right, then wrap with button
            new_input = old2.replace('type="password"', 'type="password" id="pw-field"')
            if 'style=' not in new_input:
                new_input = new_input.rstrip('>') + ' style="padding-right:3rem;">'
            new2 = (
                '<div style="position:relative;">' + new_input +
                '<button type="button" '
                'onclick="var f=this.previousElementSibling;f.type=f.type===\'password\'?\'text\':\'password\';this.innerHTML=f.type===\'password\'?\'&#x1F441;\':\'&#x1F648;\'" '
                'style="' + SHOW_BTN_STYLE + '">&#x1F441;</button>'
                '</div>'
            )
            src = src.replace(old2, new2)
            with open(path, 'w', encoding='utf-8') as f:
                f.write(src)
            print('Fixed (regex):', path)
        else:
            print('Not found:', path)
