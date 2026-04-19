with open('/var/www/quanby-legal/registry.html', 'r', encoding='utf-8') as f:
    src = f.read()

count = 0

# DC Project UUID field name mismatch (doconchain_project_uuid -> dc_project_uuid)
for old in ['act.doconchain_project_uuid', 'a.doconchain_project_uuid']:
    new = old.replace('doconchain_project_uuid', 'dc_project_uuid')
    n = src.count(old)
    if n:
        src = src.replace(old, new)
        count += n
        print(f'Fixed {n}x: {old}')

# DC Reference No field name mismatch (dc_reference_number -> dc_reference_no)
for old in ['act.dc_reference_number', 'a.dc_reference_number']:
    new = old.replace('dc_reference_number', 'dc_reference_no')
    n = src.count(old)
    if n:
        src = src.replace(old, new)
        count += n
        print(f'Fixed {n}x: {old}')

# STATUS column — show 'Completed' for completed status (DC badge)
# Also fix the status display in the table
old_status = "act.dc_status === 'completed'"
if old_status in src:
    print('dc_status badge check already correct')

# Fix: dc_status in table should show "Completed" not "completed"
old_table = "<td>${esc(a.dc_status||'—')}</td>"
new_table = "<td>${a.dc_status === 'completed' ? 'Completed' : esc(a.dc_status||'—')}</td>"
if old_table in src:
    src = src.replace(old_table, new_table)
    count += 1
    print('Fixed: dc_status table cell shows Completed')

# Fix notarized document column — should show download link if dc_file_url exists
# Also add dc_project_uuid display
old_notarized = "act.dc_reference_number ? '<div style=\"font-size:.7rem;color:var(--muted);margin-top:.15rem;\">Ref: ' + esc(act.dc_reference_number) + '</div>' : ''"
new_notarized = "act.dc_reference_no ? '<div style=\"font-size:.7rem;color:var(--muted);margin-top:.15rem;\">Ref: ' + esc(act.dc_reference_no) + '</div>' : ''"
if old_notarized in src:
    src = src.replace(old_notarized, new_notarized)
    count += 1
    print('Fixed: dc_reference_no in badge')

with open('/var/www/quanby-legal/registry.html', 'w', encoding='utf-8') as f:
    f.write(src)
print(f'Total fixes: {count}')
