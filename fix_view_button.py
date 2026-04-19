with open('/var/www/quanby-legal/registry.html', 'r', encoding='utf-8') as f:
    src = f.read()

# Fix 1: Use dc_vault_url from API response
src = src.replace(
    "else if (data.doconchain_view_url) { dlUrl = data.doconchain_view_url; }",
    "else if (data.dc_vault_url) { dlUrl = data.dc_vault_url; }\n    else if (data.doconchain_view_url) { dlUrl = data.doconchain_view_url; }"
)
print('Fix 1: dc_vault_url added to fallback chain')

# Fix 2: Change View button to open in new tab instead of modal iframe
old1 = "openDocModalById(this)"
new1 = "window.open(this.dataset.url,'_blank')"
if old1 in src:
    src = src.replace(old1, new1)
    print('Fix 2: View button opens in new tab')

with open('/var/www/quanby-legal/registry.html', 'w', encoding='utf-8') as f:
    f.write(src)
print('Done')
