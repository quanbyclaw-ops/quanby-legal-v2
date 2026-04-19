with open('/var/www/quanby-legal/registry.html', 'r', encoding='utf-8') as f:
    src = f.read()

# Replace Download <a> with a button that uses fetch+blob (avoids about:blank#blocked)
old_dl = (
    "      '<a href=\"' + esc(dlUrl) + '\" target=\"_blank\" rel=\"noopener\" onclick=\"event.stopPropagation()\" '\n"
    "      + 'style=\"display:inline-flex;align-items:center;gap:.3rem;padding:.25rem .6rem;background:rgba(63,185,80,.12);color:#3fb950;border:1px solid rgba(63,185,80,.3);border-radius:6px;font-size:.74rem;font-weight:600;text-decoration:none;margin-right:.3rem;\">'\n"
    "      + '<i class=\"hgi-stroke hgi-download-01\" style=\"font-size:.78rem;\"></i>Download</a>'"
)

new_dl = (
    "      '<button onclick=\"event.stopPropagation();downloadDoc(this.dataset.url, this.dataset.name)\" '\n"
    "      + 'data-url=\"' + esc(dlUrl) + '\" data-name=\"' + esc(dlName) + '\" '\n"
    "      + 'style=\"display:inline-flex;align-items:center;gap:.3rem;padding:.25rem .6rem;background:rgba(63,185,80,.12);color:#3fb950;border:1px solid rgba(63,185,80,.3);border-radius:6px;font-size:.74rem;font-weight:600;cursor:pointer;margin-right:.3rem;\">'\n"
    "      + '<i class=\"hgi-stroke hgi-download-01\" style=\"font-size:.78rem;\"></i>Download</button>'"
)

if old_dl in src:
    src = src.replace(old_dl, new_dl)
    print('Download button: uses fetch+blob')
else:
    print('Download button pattern not found')

# Add downloadDoc function
if 'function downloadDoc' not in src:
    download_fn = '''
function downloadDoc(url, name) {
  if (!url) return;
  // Use fetch so we can force-download without about:blank#blocked
  fetch(url, { credentials: 'include' })
    .then(function(r) {
      if (!r.ok) { alert('Could not download document (HTTP ' + r.status + ')'); return null; }
      return r.blob();
    })
    .then(function(blob) {
      if (!blob) return;
      var a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = name || 'notarized-document.pdf';
      a.click();
      setTimeout(function() { URL.revokeObjectURL(a.href); }, 5000);
    })
    .catch(function(e) { alert('Download failed: ' + e.message); });
}

'''
    src = src.replace('function openInNewTab(', download_fn + 'function openInNewTab(')
    print('downloadDoc function added')

with open('/var/www/quanby-legal/registry.html', 'w', encoding='utf-8') as f:
    f.write(src)
print('Done')
