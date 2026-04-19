import re

with open(r'C:\Users\Claw\.openclaw\workspace\quanby-legal\admin.html', 'r', encoding='utf-8') as f:
    content = f.read()

print('File length:', len(content))

# 1. Replace sidebar HTML block
old_sidebar = '''  <!-- Sidebar -->
  <nav id="sidebar">
    <div id="sidebar-logo">
      <img src="/qlegal-logo-sm.png" alt="Quanby Legal" onerror="this.style.display='none'">
      <span>Admin Portal</span>
    </div>
    <div class="nav-group">
      <div class="nav-group-label">Main</div>
      <div class="nav-item active" data-page="overview" onclick="navigate('overview')">
        <span class="nav-icon"><i class="hgi-stroke hgi-chart-bar-line-02"></i></span> Overview
      </div>
      <div class="nav-item" data-page="users" onclick="navigate('users')">
        <span class="nav-icon"><i class="hgi-stroke hgi-user-group"></i></span> Users
      </div>
      <div class="nav-item" data-page="appointments" onclick="navigate('appointments')">
        <span class="nav-icon"><i class="hgi-stroke hgi-calendar-02"></i></span> Appointments
      </div>
      <div class="nav-item" data-page="registry" onclick="navigate('registry')">
        <span class="nav-icon"><i class="hgi-stroke hgi-book-open-01"></i></span> Notarial Registry
      </div>
    </div>
    <div class="nav-group">
      <div class="nav-group-label">Management</div>
      <div class="nav-item" data-page="suborgs" onclick="navigate('suborgs')">
        <span class="nav-icon"><i class="hgi-stroke hgi-building-03"></i></span> Sub-Organizations
      </div>
    </div>
    <div class="nav-group">
      <div class="nav-group-label">System</div>
      <div class="nav-item" data-page="settings" onclick="navigate('settings')">
        <span class="nav-icon"><i class="hgi-stroke hgi-settings-01"></i></span> Settings
      </div>
    </div>
    <div class="sidebar-bottom">
      <button class="logout-btn" onclick="doLogout()">
        <i class="hgi-stroke hgi-logout-02"></i> Logout
      </button>
    </div>
  </nav>'''

new_sidebar = '  <!-- Sidebar (loaded dynamically) -->\n  <nav id="sidebar" class="loading"></nav>'

if old_sidebar in content:
    content = content.replace(old_sidebar, new_sidebar, 1)
    print('OK Sidebar replaced')
else:
    print('FAIL Sidebar not found')

# 2. Replace topbar HTML block
old_topbar = '''    <!-- Topbar -->
    <div id="topbar">
      <button id="hamburger" onclick="openSidebar()">☰</button>
      <span id="page-title">Overview</span>
      <span id="last-updated"></span>
      <button id="refresh-btn" onclick="refreshPage()">
        <i class="hgi-stroke hgi-refresh-02"></i>
        <span class="refresh-label">Refresh</span>
      </button>
    </div>'''

new_topbar = '''    <!-- Topbar (loaded dynamically) -->
    <div id="topbar" class="loading"></div>
    <!-- Legacy compat spans (hidden, kept for JS refs) -->
    <span id="page-title" style="display:none">Overview</span>
    <span id="last-updated" style="display:none"></span>'''

if old_topbar in content:
    content = content.replace(old_topbar, new_topbar, 1)
    print('OK Topbar replaced')
else:
    print('FAIL Topbar not found')

# 3. Update navigate() to also update topbar title/breadcrumb
old_nav_line = "  document.getElementById('page-title').textContent = PAGES[page] || page;"
new_nav_line = """  const _pageLabel = PAGES[page] || page;
  const _ptEl = document.getElementById('page-title'); if(_ptEl) _ptEl.textContent = _pageLabel;
  const _tbTitle = document.getElementById('tb-page-title'); if(_tbTitle) _tbTitle.textContent = _pageLabel;
  const _tbBc = document.getElementById('tb-breadcrumb-page'); if(_tbBc) _tbBc.textContent = _pageLabel;"""

if old_nav_line in content:
    content = content.replace(old_nav_line, new_nav_line, 1)
    print('OK navigate() updated')
else:
    print('FAIL navigate() line not found')

# 4. Update updateLastUpdated()
old_lu = "function updateLastUpdated() {\n  document.getElementById('last-updated').textContent = 'Updated ' + new Date().toLocaleTimeString();"
new_lu = """function updateLastUpdated() {
  const _ts = 'Updated ' + new Date().toLocaleTimeString();
  const _luEl = document.getElementById('last-updated'); if(_luEl) _luEl.textContent = _ts;
  const _tbLu = document.getElementById('tb-last-updated'); if(_tbLu) _tbLu.textContent = _ts;"""

if old_lu in content:
    content = content.replace(old_lu, new_lu, 1)
    print('OK updateLastUpdated() updated')
else:
    print('FAIL updateLastUpdated() not found')

# 5. Replace boot section — add loadComponents before init
old_boot = """/* \u2500\u2500 Boot \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500 */
init();"""
new_boot = """/* \u2500\u2500 Component Loader \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500 */
async function loadComponents() {
  try {
    const [sidebarRes, topbarRes] = await Promise.all([
      fetch('/assets/admin-sidebar.html'),
      fetch('/assets/admin-topbar.html'),
    ]);
    const sidebarHtml = await sidebarRes.text();
    const topbarHtml = await topbarRes.text();
    document.getElementById('sidebar').innerHTML = sidebarHtml;
    document.getElementById('topbar').innerHTML = topbarHtml;
    document.getElementById('sidebar').classList.remove('loading');
    document.getElementById('topbar').classList.remove('loading');
    // Re-highlight active nav item after load
    const hash = location.hash.replace('#','') || 'overview';
    document.querySelectorAll('.nav-item[data-page]').forEach(el => {
      el.classList.toggle('active', el.dataset.page === hash);
    });
    // Sync topbar title
    const _label = PAGES[hash] || hash;
    const _tbTitle = document.getElementById('tb-page-title'); if(_tbTitle) _tbTitle.textContent = _label;
    const _tbBc = document.getElementById('tb-breadcrumb-page'); if(_tbBc) _tbBc.textContent = _label;
  } catch(e) { console.warn('Component load failed:', e); }
}

/* \u2500\u2500 Boot \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500 */
loadComponents().then(() => init());"""

if old_boot in content:
    content = content.replace(old_boot, new_boot, 1)
    print('OK Boot section updated with loadComponents()')
else:
    print('FAIL Boot section not found')

with open(r'C:\Users\Claw\.openclaw\workspace\quanby-legal\admin.html', 'w', encoding='utf-8') as f:
    f.write(content)

print('Done. File written. New length:', len(content))
