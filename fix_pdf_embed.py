with open('/var/www/quanby-legal/registry.html', 'r', encoding='utf-8') as f:
    src = f.read()

# Replace openDocViewer to fetch PDF as blob then embed it
old_fn = '''function openDocViewer(url, name) {
  document.getElementById('doc-viewer-title').textContent = name || 'Document Preview';
  document.getElementById('doc-viewer-open').href = url || '#';
  var btnEl = document.getElementById('doc-viewer-btn');
  if (btnEl) btnEl.href = url || '#';
  // Show/hide iframe vs fallback based on URL type
  var iframe = document.getElementById('doc-viewer-iframe');
  var loading = document.getElementById('doc-viewer-loading');
  var fallback = document.getElementById('doc-viewer-fallback');
  if (url && (url.startsWith('data:application/pdf') || url.endsWith('.pdf'))) {
    // Inline PDF — show in iframe
    if (loading) loading.style.display = 'flex';
    if (iframe) { iframe.style.display = 'none'; iframe.src = ''; }
    if (fallback) fallback.style.display = 'none';
    setTimeout(function() {
      if (iframe) {
        iframe.onload = function() {
          if (loading) loading.style.display = 'none';
          iframe.style.display = 'block';
        };
        iframe.onerror = function() {
          if (loading) loading.style.display = 'none';
          if (fallback) fallback.style.display = 'block';
        };
        iframe.src = url;
      }
    }, 100);
  } else {
    // External URL — show fallback with link
    if (loading) loading.style.display = 'none';
    if (iframe) iframe.style.display = 'none';
    if (fallback) { fallback.style.display = 'flex'; fallback.style.flexDirection='column'; fallback.style.alignItems='center'; }
  }
  var overlay = document.getElementById('doc-viewer-overlay');
  overlay.style.display = 'flex';
  document.body.style.overflow = 'hidden';
}'''

new_fn = '''function openDocViewer(url, name) {
  document.getElementById('doc-viewer-title').textContent = name || 'Document Preview';
  document.getElementById('doc-viewer-open').href = url || '#';
  var btnEl = document.getElementById('doc-viewer-btn');
  if (btnEl) btnEl.href = url || '#';
  var iframe = document.getElementById('doc-viewer-iframe');
  var loading = document.getElementById('doc-viewer-loading');
  var fallback = document.getElementById('doc-viewer-fallback');
  var overlay = document.getElementById('doc-viewer-overlay');
  overlay.style.display = 'flex';
  document.body.style.overflow = 'hidden';
  if (!url) {
    if (loading) loading.style.display = 'none';
    if (fallback) { fallback.style.display = 'block'; }
    return;
  }
  // Show loading
  if (loading) loading.style.display = 'flex';
  if (iframe) { iframe.style.display = 'none'; iframe.src = ''; }
  if (fallback) fallback.style.display = 'none';
  // Fetch PDF with credentials then create object URL (avoids iframe cookie issue)
  fetch(url, { credentials: 'include' })
    .then(function(r) {
      if (!r.ok) throw new Error('HTTP ' + r.status);
      return r.blob();
    })
    .then(function(blob) {
      var objectUrl = URL.createObjectURL(blob);
      if (iframe) {
        iframe.onload = function() {
          if (loading) loading.style.display = 'none';
          iframe.style.display = 'block';
        };
        iframe.src = objectUrl;
      }
    })
    .catch(function(e) {
      console.warn('[Registry] PDF fetch failed:', e);
      if (loading) loading.style.display = 'none';
      if (fallback) fallback.style.display = 'block';
    });
}'''

if old_fn in src:
    src = src.replace(old_fn, new_fn)
    print('Fixed: openDocViewer fetches PDF blob then embeds as objectURL')
else:
    print('Pattern not found')

with open('/var/www/quanby-legal/registry.html', 'w', encoding='utf-8') as f:
    f.write(src)
print('Done')
