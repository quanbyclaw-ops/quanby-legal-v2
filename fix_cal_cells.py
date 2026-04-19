with open('/var/www/quanbyai-website/calendar.html', 'r', encoding='utf-8') as f:
    src = f.read()

fixes = [
    # Fix event pill — truncate long text
    (
        '.event-pill{',
        '.event-pill{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:100%;'
    ),
    # Fix cal cell — fixed height, no stretch
    (
        '.cal-cell{',
        '.cal-cell{overflow:hidden;'
    ),
    # Cal cell min-height stays but also add max-height to prevent distortion
    (
        '.cal-cell{\nbackground:var(--surface);min-height:110px;',
        '.cal-cell{\nbackground:var(--surface);min-height:110px;max-height:140px;overflow:hidden;'
    ),
]

count = 0
for old, new in fixes:
    if old in src and new not in src:
        src = src.replace(old, new, 1)
        count += 1
        print(f'Fixed: {old[:40]}')

with open('/var/www/quanbyai-website/calendar.html', 'w', encoding='utf-8') as f:
    f.write(src)
print(f'{count} fixes applied')
