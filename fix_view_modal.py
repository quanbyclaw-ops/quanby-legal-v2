with open('/var/www/quanby-legal/registry.html', 'r', encoding='utf-8') as f:
    src = f.read()

# 1. Change View button from new-tab to modal
old_view = (
    "      + '<button onclick=\"event.stopPropagation();openInNewTab(this.dataset.url)\" data-url=\"' + esc(dlUrl) + '\" data-name=\"' + esc(dlName) + '\" '\n"
    "      + 'style=\"display:inline-flex;align-items:center;gap:.3rem;padding:.25rem .6rem;background:rgba(88,166,255,.12);color:#58a6ff;border:1px solid rgba(88,166,255,.3);border-radius:6px;font-size:.74rem;font-weight:600;cursor:pointer;\">'\n"
    "      + '<i class=\"hgi-stroke hgi-eye\" style=\"font-size:.78rem;\"></i>View</button>';"
)
new_view = (
    "      + '<button onclick=\"event.stopPropagation();openDocViewer(this.dataset.url, this.dataset.name)\" data-url=\"' + esc(dlUrl) + '\" data-name=\"' + esc(dlName) + '\" '\n"
    "      + 'style=\"display:inline-flex;align-items:center;gap:.3rem;padding:.25rem .6rem;background:rgba(88,166,255,.12);color:#58a6ff;border:1px solid rgba(88,166,255,.3);border-radius:6px;font-size:.74rem;font-weight:600;cursor:pointer;\">'\n"
    "      + '<i class=\"hgi-stroke hgi-eye\" style=\"font-size:.78rem;\"></i>View</button>';"
)

if old_view in src:
    src = src.replace(old_view, new_view)
    print('Fixed View button -> modal')
else:
    print('View pattern not found - trying simpler replacement')
    src = src.replace(
        'openInNewTab(this.dataset.url)',
        'openDocViewer(this.dataset.url, this.dataset.name)'
    )
    print('Replaced openInNewTab with openDocViewer')

# 2. Add doc viewer modal HTML before </body>
viewer_modal = '''
<!-- Document Viewer Modal -->
<div id="doc-viewer-overlay" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,.75);backdrop-filter:blur(8px);z-index:1000;align-items:center;justify-content:center;padding:1rem;">
  <div style="background:#1a1a2e;border:1px solid rgba(255,255,255,.12);border-radius:16px;width:100%;max-width:900px;max-height:92vh;display:flex;flex-direction:column;overflow:hidden;box-shadow:0 24px 80px rgba(0,0,0,.6);">
    <div style="display:flex;align-items:center;justify-content:space-between;padding:1rem 1.25rem;border-bottom:1px solid rgba(255,255,255,.08);">
      <div style="font-weight:700;font-size:.95rem;color:#f1f5f9;" id="doc-viewer-title">Document Preview</div>
      <div style="display:flex;gap:.5rem;">
        <a id="doc-viewer-open" href="#" target="_blank" rel="noopener"
           style="display:inline-flex;align-items:center;gap:.3rem;padding:.35rem .8rem;background:rgba(232,201,122,.15);border:1px solid rgba(232,201,122,.3);border-radius:7px;color:#e8c97a;font-size:.78rem;font-weight:600;text-decoration:none;">
          <i class="hgi-stroke hgi-share-01" style="font-size:.8rem;"></i>Open in DC
        </a>
        <button onclick="closeDocViewer()" style="background:rgba(248,113,113,.12);border:1px solid rgba(248,113,113,.25);color:#f87171;border-radius:7px;padding:.35rem .75rem;cursor:pointer;font-size:.85rem;font-weight:600;">✕ Close</button>
      </div>
    </div>
    <div style="flex:1;overflow:auto;padding:1.25rem;display:flex;align-items:center;justify-content:center;background:#0d0f1a;min-height:400px;" id="doc-viewer-body">
      <div style="text-align:center;color:#64748b;">
        <div style="font-size:3rem;margin-bottom:1rem;">📄</div>
        <div style="font-size:.9rem;margin-bottom:.5rem;">DoconChain Document</div>
        <div style="font-size:.8rem;margin-bottom:1.5rem;">This document is hosted on DoconChain.<br>Click the button below to view it.</div>
        <a id="doc-viewer-btn" href="#" target="_blank" rel="noopener"
           style="display:inline-flex;align-items:center;gap:.4rem;padding:.6rem 1.25rem;background:linear-gradient(135deg,#e8c97a,#c9a84c);color:#0a0e1a;border-radius:8px;font-weight:700;text-decoration:none;font-size:.88rem;">
          <i class="hgi-stroke hgi-external-link" style="font-size:.85rem;"></i>View on DoconChain
        </a>
      </div>
    </div>
  </div>
</div>
'''

if 'doc-viewer-overlay' not in src:
    src = src.replace('</body>', viewer_modal + '</body>')
    print('Viewer modal added')

# 3. Add openDocViewer / closeDocViewer functions
viewer_js = '''
function openDocViewer(url, name) {
  document.getElementById('doc-viewer-title').textContent = name || 'Document Preview';
  document.getElementById('doc-viewer-open').href = url || '#';
  document.getElementById('doc-viewer-btn').href = url || '#';
  var overlay = document.getElementById('doc-viewer-overlay');
  overlay.style.display = 'flex';
  document.body.style.overflow = 'hidden';
}
function closeDocViewer() {
  document.getElementById('doc-viewer-overlay').style.display = 'none';
  document.body.style.overflow = '';
}
document.getElementById('doc-viewer-overlay').addEventListener('click', function(e) {
  if (e.target === this) closeDocViewer();
});

'''

if 'function openDocViewer' not in src:
    src = src.replace('function openInNewTab(', viewer_js + 'function openInNewTab(')
    print('openDocViewer function added')

with open('/var/www/quanby-legal/registry.html', 'w', encoding='utf-8') as f:
    f.write(src)
print('Done')
