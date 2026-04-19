with open('/var/www/bcs-ims/resources/views/layouts/app.blade.php', 'r', encoding='utf-8') as f:
    src = f.read()

old_css = '''    :root {
      --denr-green: #1e3a5f;
      --denr-accent: #00d4c8;
      --denr-green-mid: #7c3aed;
      --bcs-bg: #f0f4f8;
      --bcs-text: #1a2535;
    }
    body { background: var(--bcs-bg); font-family: 'Inter', 'Segoe UI', sans-serif; color: var(--bcs-text); }
    .navbar-denr { background: var(--denr-green); }
    .navbar-denr .navbar-brand { color: var(--denr-accent) !important; font-weight: 700; font-size: 1rem; }
    .navbar-denr .nav-link { color: rgba(255,255,255,0.85) !important; }
    .navbar-denr .nav-link:hover { color: var(--denr-accent) !important; }
    .sidebar { background: var(--denr-green); min-height: calc(100vh - 56px); width: 260px; flex-shrink: 0; overflow-y: auto; }
    .sidebar .nav-link { color: rgba(255,255,255,0.75); padding: 10px 20px; font-size: 0.875rem; border-left: 3px solid transparent; text-decoration: none; display: block; }
    .sidebar .nav-link.active { color: #a78bfa; border-left-color: #7c3aed; background: rgba(124,58,237,0.12); }
    .sidebar .nav-link:hover { color: var(--denr-accent); border-left-color: var(--denr-accent); background: rgba(255,255,255,0.05); }
    .sidebar .nav-section { color: rgba(255,255,255,0.4); font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.1em; padding: 12px 20px 4px; }
    .main-content { flex: 1; padding: 24px; overflow-x: auto; }
    .page-header { background: white; border-bottom: 3px solid var(--denr-accent); padding: 16px 24px; margin: -24px -24px 24px; }
    .page-header h4 { color: var(--denr-green); font-weight: 700; margin: 0; }
    .card { border: none; box-shadow: 0 1px 4px rgba(0,0,0,0.08); border-radius: 8px; }
    .card-header-denr { background: var(--denr-green); color: white; border-radius: 8px 8px 0 0 !important; }
    .btn-denr { background: var(--denr-green); color: white; border: none; }
    .btn-denr:hover { background: var(--denr-green-mid); color: white; }
    .btn-denr-accent { background: var(--denr-accent); color: var(--denr-green); font-weight: 600; border: none; }
    .btn-denr-accent:hover { background: #00b8ad; color: var(--denr-green); }
    .badge-role { font-size: 0.7rem; }
    .stat-card { border-left: 4px solid var(--denr-accent); }
    @media print {
      .sidebar, .navbar-denr, .btn, form[method=POST] { display: none !important; }
      .main-content { padding: 0 !important; }
    }'''

new_css = '''    :root {
      --ql-navy: #1e3a5f;
      --ql-navy-dark: #0a0e1a;
      --ql-surface: #111827;
      --ql-surface2: #162032;
      --ql-border: rgba(255,255,255,0.08);
      --ql-teal: #00d4c8;
      --ql-purple: #7c3aed;
      --ql-purple-light: #a78bfa;
      --ql-text: #e6edf3;
      --ql-muted: #94a3b8;
      /* Keep legacy var names for compatibility */
      --denr-green: #1e3a5f;
      --denr-accent: #00d4c8;
      --denr-green-mid: #7c3aed;
    }
    body { background: var(--ql-navy-dark); font-family: 'Inter', 'Segoe UI', sans-serif; color: var(--ql-text); }
    .sidebar { background: var(--ql-navy); min-height: 100vh; width: 260px; flex-shrink: 0; overflow-y: auto; border-right: 1px solid var(--ql-border); }
    .sidebar .nav-link { color: rgba(226,232,240,0.65); padding: 10px 20px; font-size: 0.875rem; border-left: 3px solid transparent; text-decoration: none; display: block; transition: all 0.15s; }
    .sidebar .nav-link.active { color: var(--ql-purple-light); border-left-color: var(--ql-purple); background: rgba(124,58,237,0.12); }
    .sidebar .nav-link:hover { color: var(--ql-teal); border-left-color: var(--ql-teal); background: rgba(0,212,200,0.05); }
    .sidebar .nav-section { color: rgba(148,163,184,0.5); font-size: 0.68rem; text-transform: uppercase; letter-spacing: 0.1em; padding: 12px 20px 4px; }
    .main-content { flex: 1; padding: 24px; overflow-x: auto; background: var(--ql-navy-dark); }
    .page-header { background: var(--ql-surface); border-bottom: 2px solid var(--ql-teal); padding: 16px 24px; margin: -24px -24px 24px; }
    .page-header h4 { color: var(--ql-text); font-weight: 700; margin: 0; }
    .card { background: var(--ql-surface); border: 1px solid var(--ql-border); border-radius: 10px; box-shadow: none; color: var(--ql-text); }
    .card-header-denr { background: var(--ql-navy); color: white; border-radius: 10px 10px 0 0 !important; border-bottom: 1px solid var(--ql-border); }
    .card-header { background: var(--ql-surface2); border-bottom: 1px solid var(--ql-border); color: var(--ql-text); }
    .table { color: var(--ql-text); --bs-table-bg: transparent; }
    .table th { color: var(--ql-muted); border-color: var(--ql-border); font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.05em; }
    .table td { border-color: var(--ql-border); }
    .table-hover tbody tr:hover { background-color: rgba(0,212,200,0.04) !important; }
    .table-striped tbody tr:nth-of-type(odd) { background-color: rgba(255,255,255,0.02); }
    .form-control, .form-select { background: rgba(0,0,0,0.2); border-color: var(--ql-border); color: var(--ql-text); }
    .form-control:focus, .form-select:focus { background: rgba(0,0,0,0.2); border-color: var(--ql-teal); color: var(--ql-text); box-shadow: 0 0 0 0.2rem rgba(0,212,200,0.15); }
    .form-control::placeholder { color: var(--ql-muted); }
    .form-label { color: var(--ql-muted); font-size: 0.85rem; font-weight: 500; }
    .btn-denr { background: var(--ql-navy); color: white; border: none; }
    .btn-denr:hover { background: var(--ql-purple); color: white; }
    .btn-denr-accent { background: var(--ql-teal); color: #0a0e1a; font-weight: 600; border: none; }
    .btn-denr-accent:hover { background: #00b8ad; color: #0a0e1a; }
    .btn-outline-secondary { border-color: var(--ql-border); color: var(--ql-muted); }
    .btn-outline-secondary:hover { background: rgba(255,255,255,0.06); color: var(--ql-text); border-color: var(--ql-muted); }
    .btn-outline-primary { border-color: var(--ql-purple); color: var(--ql-purple-light); }
    .btn-outline-primary:hover { background: rgba(124,58,237,0.15); color: var(--ql-purple-light); }
    .btn-outline-danger { border-color: rgba(248,113,113,0.4); color: #f87171; }
    .btn-outline-danger:hover { background: rgba(248,113,113,0.1); color: #f87171; }
    .badge { font-size: 0.72rem; }
    .badge.bg-success { background: rgba(0,212,200,0.15) !important; color: var(--ql-teal) !important; border: 1px solid rgba(0,212,200,0.3); }
    .badge.bg-warning { background: rgba(245,158,11,0.15) !important; color: #fbbf24 !important; border: 1px solid rgba(245,158,11,0.3); }
    .badge.bg-danger { background: rgba(248,113,113,0.15) !important; color: #f87171 !important; border: 1px solid rgba(248,113,113,0.3); }
    .badge.bg-primary { background: rgba(124,58,237,0.2) !important; color: var(--ql-purple-light) !important; border: 1px solid rgba(124,58,237,0.3); }
    .badge.bg-secondary { background: rgba(148,163,184,0.15) !important; color: var(--ql-muted) !important; border: 1px solid rgba(148,163,184,0.2); }
    .stat-card { border-left: 3px solid var(--ql-teal); }
    .modal-content { background: var(--ql-surface); border: 1px solid var(--ql-border); color: var(--ql-text); }
    .modal-header { background: var(--ql-navy); border-bottom: 1px solid var(--ql-border); }
    .modal-footer { border-top: 1px solid var(--ql-border); }
    .alert-success { background: rgba(0,212,200,0.1); border-color: rgba(0,212,200,0.3); color: var(--ql-teal); }
    .alert-danger { background: rgba(248,113,113,0.1); border-color: rgba(248,113,113,0.3); color: #f87171; }
    .alert-warning { background: rgba(245,158,11,0.1); border-color: rgba(245,158,11,0.3); color: #fbbf24; }
    .alert-info { background: rgba(0,212,200,0.08); border-color: rgba(0,212,200,0.2); color: #7dd3fc; }
    .list-group-item { background: var(--ql-surface2); border-color: var(--ql-border); color: var(--ql-text); }
    .dropdown-menu { background: var(--ql-surface); border: 1px solid var(--ql-border); }
    .dropdown-item { color: var(--ql-muted); }
    .dropdown-item:hover { background: rgba(0,212,200,0.06); color: var(--ql-teal); }
    a { color: var(--ql-teal); }
    a:hover { color: var(--ql-purple-light); }
    .text-muted { color: var(--ql-muted) !important; }
    .badge-role { font-size: 0.7rem; }
    @media print {
      .sidebar, .btn, form[method=POST] { display: none !important; }
      .main-content { padding: 0 !important; }
    }'''

if old_css in src:
    src = src.replace(old_css, new_css)
    print('CSS replaced successfully')
else:
    print('Pattern not found — trying partial match...')
    idx = src.find('--bcs-bg: #f0f4f8')
    if idx >= 0:
        print('Found bcs-bg at:', idx)
    idx2 = src.find('--denr-green: #1e3a5f')
    if idx2 >= 0:
        print('Found denr-green at:', idx2)

with open('/var/www/bcs-ims/resources/views/layouts/app.blade.php', 'w', encoding='utf-8') as f:
    f.write(src)
print('Layout updated')
