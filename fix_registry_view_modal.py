with open('/var/www/quanby-legal/registry.html', 'r', encoding='utf-8') as f:
    src = f.read()

# 1. Update doc viewer modal to show PDF iframe for base64 data URLs
old_modal_body = '''    <div style="flex:1;overflow:auto;padding:1.25rem;display:flex;align-items:center;justify-content:center;background:#0d0f1a;min-height:400px;" id="doc-viewer-body">
      <div style="text-align:center;color:#64748b;">
        <div style="font-size:3rem;margin-bottom:1rem;">📄</div>
        <div style="font-size:.9rem;margin-bottom:.5rem;">DoconChain Document</div>
        <div style="font-size:.8rem;margin-bottom:1.5rem;">This document is hosted on DoconChain.<br>Click the button below to view it.</div>
        <a id="doc-viewer-btn" href="#" target="_blank" rel="noopener"
           style="display:inline-flex;align-items:center;gap:.4rem;padding:.6rem 1.25rem;background:linear-gradient(135deg,#e8c97a,#c9a84c);color:#0a0e1a;border-radius:8px;font-weight:700;text-decoration:none;font-size:.88rem;">
          <i class="hgi-stroke hgi-external-link" style="font-size:.85rem;"></i>View on DoconChain
        </a>
      </div>
    </div>'''

new_modal_body = '''    <div style="flex:1;overflow:hidden;background:#0d0f1a;min-height:500px;position:relative;" id="doc-viewer-body">
      <div id="doc-viewer-loading" style="position:absolute;inset:0;display:flex;align-items:center;justify-content:center;flex-direction:column;gap:.75rem;color:#64748b;">
        <div style="width:28px;height:28px;border:3px solid rgba(255,255,255,.1);border-top-color:#a78bfa;border-radius:50%;animation:spin .7s linear infinite;"></div>
        <div style="font-size:.85rem;">Loading document...</div>
      </div>
      <iframe id="doc-viewer-iframe" src="" style="width:100%;height:100%;border:none;display:none;min-height:500px;" allowfullscreen></iframe>
      <div id="doc-viewer-fallback" style="display:none;text-align:center;padding:2rem;color:#64748b;">
        <div style="font-size:2.5rem;margin-bottom:1rem;">📄</div>
        <div style="font-size:.88rem;margin-bottom:1.25rem;">Could not load preview. Open directly on DoconChain.</div>
        <a id="doc-viewer-btn" href="#" target="_blank" rel="noopener"
           style="display:inline-flex;align-items:center;gap:.4rem;padding:.6rem 1.25rem;background:linear-gradient(135deg,#e8c97a,#c9a84c);color:#0a0e1a;border-radius:8px;font-weight:700;text-decoration:none;font-size:.88rem;">
          Open on DoconChain →
        </a>
      </div>
    </div>'''

if old_modal_body in src:
    src = src.replace(old_modal_body, new_modal_body)
    print('Fixed: modal body has iframe for PDF preview')
else:
    print('Modal body pattern not found')

# 2. Update openDocViewer to load PDF in iframe
old_viewer_fn = '''function openDocViewer(url, name) {
  document.getElementById('doc-viewer-title').textContent = name || 'Document Preview';
  document.getElementById('doc-viewer-open').href = url || '#';
  document.getElementById('doc-viewer-btn').href = url || '#';
  var overlay = document.getElementById('doc-viewer-overlay');
  overlay.style.display = 'flex';
  document.body.style.overflow = 'hidden';
}'''

new_viewer_fn = '''function openDocViewer(url, name) {
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

if old_viewer_fn in src:
    src = src.replace(old_viewer_fn, new_viewer_fn)
    print('Fixed: openDocViewer shows PDF in iframe')
else:
    print('openDocViewer pattern not found')

# 3. Auto-fetch docs when page loads (after acts are rendered)
old_render_end = '''    renderPagination(data.total, currentPage, totalPages);
  } catch(e) {'''

new_render_end = '''    renderPagination(data.total, currentPage, totalPages);
    // Auto-fetch document links for all acts
    setTimeout(function() {
      document.querySelectorAll('[id^="doc-links-"]').forEach(function(el) {
        var actId = el.id.replace('doc-links-','');
        if (el.dataset.fetched !== '1') fetchActDocument(actId);
      });
    }, 500);
  } catch(e) {'''

if old_render_end in src:
    src = src.replace(old_render_end, new_render_end)
    print('Fixed: auto-fetch docs after render')
else:
    print('Render end pattern not found')

with open('/var/www/quanby-legal/registry.html', 'w', encoding='utf-8') as f:
    f.write(src)
print('Done')
