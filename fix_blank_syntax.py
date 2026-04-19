with open('/var/www/quanby-legal/registry.html', 'r', encoding='utf-8') as f:
    src = f.read()

# The broken line: onclick="event.stopPropagation();window.open(this.dataset.url,'_blank')"
# The '_blank' uses single quotes inside an onclick attr that's already in single-quoted JS string concat
# Fix: use a named function instead

# Find and replace the broken button
bad = "window.open(this.dataset.url,'_blank')"
good = "openInNewTab(this.dataset.url)"

if bad in src:
    src = src.replace(bad, good)
    print('Fixed inline onclick')

# Add the openInNewTab function if not present
if 'function openInNewTab' not in src:
    # Insert before boot()
    src = src.replace(
        'async function boot() {',
        'function openInNewTab(url) { if(url) window.open(url, "_blank", "noopener"); }\n\nasync function boot() {'
    )
    print('Added openInNewTab function')

with open('/var/www/quanby-legal/registry.html', 'w', encoding='utf-8') as f:
    f.write(src)
print('Done')
