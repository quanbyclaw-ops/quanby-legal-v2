with open('/var/www/quanbyai-website/calendar.html', 'r', encoding='utf-8') as f:
    src = f.read()

# Move the auto-login check to AFTER all variable declarations
# Simply change it to defer via DOMContentLoaded or move it after declarations

old_auto = "if (localStorage.getItem('qcal_auth') === '1') showApp();"
new_auto = "// Auto-login deferred — runs after all variables declared below"

# Find where MONTHS and DAYS are and add the check after them
old_days = "var DAYS = ['Sunday','Monday','Tuesday','Wednesday','Thursday','Friday','Saturday'];"
new_days = "var DAYS = ['Sunday','Monday','Tuesday','Wednesday','Thursday','Friday','Saturday'];\n\n// Auto-login: runs after all variables initialized\nif (localStorage.getItem('qcal_auth') === '1') showApp();"

changed = 0
if old_auto in src:
    src = src.replace(old_auto, new_auto)
    changed += 1
    print('Removed early showApp call')

if old_days in src and 'Auto-login: runs after' not in src:
    src = src.replace(old_days, new_days)
    changed += 1
    print('Added deferred showApp after DAYS declaration')

with open('/var/www/quanbyai-website/calendar.html', 'w', encoding='utf-8') as f:
    f.write(src)
print(f'Done — {changed} changes')
