with open('/var/www/bcs-ims/resources/views/layouts/app.blade.php', 'r', encoding='utf-8') as f:
    src = f.read()

new_src = '''<!DOCTYPE html>
<html lang="en">
<head>
  <link rel="icon" type="image/svg+xml" href="https://quanbyai.com/favicon.svg">
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>@yield('title', 'Quanby Procurement') &mdash; Quanby Solutions, Inc.</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
  <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.css" rel="stylesheet">
  <style>
    :root {
      --denr-green: #1e3a5f;
      --denr-accent: #00d4c8;
      --denr-green-mid: #254a78;
      --bcs-bg: #f0f4f8;
      --bcs-text: #1a2535;
    }
    body { background: var(--bcs-bg); font-family: \'Segoe UI\', sans-serif; color: var(--bcs-text); }
    .navbar-denr { background: var(--denr-green); }
    .navbar-denr .navbar-brand { color: var(--denr-accent) !important; font-weight: 700; font-size: 1rem; }
    .navbar-denr .nav-link { color: rgba(255,255,255,0.85) !important; }
    .navbar-denr .nav-link:hover { color: var(--denr-accent) !important; }
    .sidebar { background: var(--denr-green); min-height: calc(100vh - 56px); width: 260px; flex-shrink: 0; overflow-y: auto; }
    .sidebar .nav-link { color: rgba(255,255,255,0.75); padding: 10px 20px; font-size: 0.875rem; border-left: 3px solid transparent; text-decoration: none; display: block; }
    .sidebar .nav-link:hover, .sidebar .nav-link.active { color: var(--denr-accent); border-left-color: var(--denr-accent); background: rgba(255,255,255,0.05); }
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
    }
  </style>
  @stack(\'styles\')
</head>
<body>
<!-- ===== QUANBY UNIFIED NAV ===== -->
  <style>
    #qnav {
      position: fixed; top: 0; left: 0; right: 0; z-index: 9999;
      padding: 0 24px;
      background: rgba(10,14,26,0.97);
      backdrop-filter: blur(16px);
      -webkit-backdrop-filter: blur(16px);
      border-bottom: 1px solid rgba(255,255,255,0.08);
      height: 64px; display: flex; align-items: center;
    }
    #qnav .qnav-inner {
      width: 100%; display: flex; align-items: center;
      justify-content: space-between; gap: 16px;
    }
    #qnav .qnav-logo {
      display: flex; align-items: center; gap: 0;
      text-decoration: none; flex-shrink: 0;
    }
    #qnav .qnav-logo img { height: 44px; width: auto; display: block; }
    #qnav .qnav-links {
      display: flex; align-items: center; gap: 28px;
      list-style: none; margin: 0; padding: 0;
    }
    #qnav .qnav-links a {
      font-size: 0.9rem; font-weight: 500;
      color: rgba(255,255,255,0.6); text-decoration: none;
      transition: color 0.2s; white-space: nowrap;
    }
    #qnav .qnav-links a:hover { color: #fff; }
    #qnav .qnav-right { display: flex; align-items: center; gap: 14px; flex-shrink: 0; }
    #qnav .qnav-cta {
      padding: 8px 20px; font-size: 0.9rem; font-weight: 600;
      background: var(--teal, #00d4c8); color: #0a0e1a;
      border-radius: 6px; text-decoration: none; white-space: nowrap;
      transition: opacity 0.2s;
    }
    #qnav .qnav-cta:hover { opacity: 0.85; }
    #qnav .qnav-user {
      font-size: 0.86rem; color: rgba(255,255,255,0.5);
      display: flex; align-items: center; gap: 6px;
    }
    #qnav .qnav-user strong { color: rgba(255,255,255,0.85); font-size: 0.9rem; }
    body { padding-top: 64px !important; }
    @media (max-width: 900px) { #qnav .qnav-links { display: none; } }
  </style>
  <div id="qnav">
    <div class="qnav-inner">
      <a class="qnav-logo" href="https://quanbyai.com" target="_blank">
        <img src="https://quanbyai.com/brand/neural-icon.svg" alt="Quanby AI" onerror="this.style.display=\'none\'">
      </a>
      <ul class="qnav-links">
        <li><a href="https://quanbyai.com/#features">What We Build</a></li>
        <li><a href="https://quanbyai.com/#about">About</a></li>
        <li><a href="https://quanbyai.com/#products">Products</a></li>
        <li><a href="https://bcs.quanbyai.com" style="color:#00d4c8;font-weight:700;">Procurement</a></li>
        <li><a href="https://qsign.quanbyai.com" style="color:#a78bfa;font-weight:700;">QSign</a></li>
        <li><a href="https://edms.quanbyai.com" style="color:#34d399;font-weight:700;">DMS</a></li>
      </ul>
      <div class="qnav-right">
        @auth
        <div class="qnav-user">&#128100; <strong>{{ auth()->user()->name }}</strong></div>
        @endauth
        <a href="https://quanbyai.com/calendar.html" class="qnav-cta" target="_blank">Book a Call</a>
      </div>
    </div>
  </div>
<!-- ===== END QUANBY UNIFIED NAV ===== -->

  <div class="d-flex" style="min-height:calc(100vh - 64px)">
    <!-- Sidebar -->
    @auth
    <div class="sidebar">
      <div class="px-4 py-3" style="border-bottom:1px solid rgba(255,255,255,0.1)">
        <div style="font-size:0.95rem;font-weight:800;color:var(--denr-accent);line-height:1.2">Quanby Procurement</div>
        <div style="font-size:0.7rem;color:rgba(255,255,255,0.5);margin-top:2px">with GAM Reports</div>
      </div>
      <nav class="py-2">
        <div class="nav-section"><i class="bi bi-grid me-1"></i>Main</div>
        <a class="nav-link {{ request()->routeIs(\'dashboard\') ? \'active\' : \'\' }}" href="{{ route(\'dashboard\') }}">
          <i class="bi bi-speedometer2 me-2"></i>Dashboard
        </a>

        <div class="nav-section"><i class="bi bi-receipt me-1"></i>Transactions</div>
        <a class="nav-link {{ request()->routeIs(\'purchase-requests.*\') ? \'active\' : \'\' }}" href="{{ route(\'purchase-requests.index\') }}">
          <i class="bi bi-file-earmark-text me-2"></i>Purchase Requests
        </a>
        <a class="nav-link {{ request()->routeIs(\'iars.*\') ? \'active\' : \'\' }}" href="{{ route(\'iars.index\') }}">
          <i class="bi bi-clipboard-check me-2"></i>Inspection & Acceptance
        </a>
        <a class="nav-link {{ request()->routeIs(\'ris.*\') ? \'active\' : \'\' }}" href="{{ route(\'ris.index\') }}">
          <i class="bi bi-arrow-right-square me-2"></i>Issue Slips (RIS)
        </a>

        <div class="nav-section"><i class="bi bi-building me-1"></i>Property</div>
        <a class="nav-link {{ request()->routeIs(\'property.*\') ? \'active\' : \'\' }}" href="{{ route(\'property.index\') }}">
          <i class="bi bi-tag me-2"></i>Property Items
        </a>
        <a class="nav-link {{ request()->routeIs(\'ics.*\') ? \'active\' : \'\' }}" href="{{ route(\'ics.index\') }}">
          <i class="bi bi-person-badge me-2"></i>ICS (Semi-Expendable)
        </a>
        <a class="nav-link {{ request()->routeIs(\'par.*\') ? \'active\' : \'\' }}" href="{{ route(\'par.index\') }}">
          <i class="bi bi-receipt me-2"></i>PAR (PPE)
        </a>

        <div class="nav-section"><i class="bi bi-arrow-left-right me-1"></i>Transfers</div>
        <a class="nav-link {{ request()->routeIs(\'ptr.*\') ? \'active\' : \'\' }}" href="{{ route(\'ptr.index\') }}">
          <i class="bi bi-arrow-left-right me-2"></i>Property Transfer (PTR)
        </a>
        <a class="nav-link {{ request()->routeIs(\'itr.*\') ? \'active\' : \'\' }}" href="{{ route(\'itr.index\') }}">
          <i class="bi bi-box-arrow-right me-2"></i>Inventory Transfer (ITR)
        </a>

        <div class="nav-section"><i class="bi bi-calculator me-1"></i>Physical Count</div>
        <a class="nav-link {{ request()->routeIs(\'physical-count.*\') ? \'active\' : \'\' }}" href="{{ route(\'physical-count.index\') }}">
          <i class="bi bi-calculator me-2"></i>Physical Count Reports
        </a>

        <div class="nav-section"><i class="bi bi-printer me-1"></i>Reports</div>
        <a class="nav-link {{ request()->routeIs(\'reports.*\') ? \'active\' : \'\' }}" href="{{ route(\'reports.index\') }}">
          <i class="bi bi-file-earmark-bar-graph me-2"></i>GAM Reports (26)
        </a>
        <a class="nav-link {{ request()->routeIs(\'barcode.*\') ? \'active\' : \'\' }}" href="{{ route(\'barcode.scan\') }}">
          <i class="bi bi-upc-scan me-2"></i>Barcode Scanner
        </a>

        <div class="nav-section"><i class="bi bi-gear me-1"></i>Administration</div>
        <a class="nav-link {{ request()->routeIs(\'items.*\') ? \'active\' : \'\' }}" href="{{ route(\'items.index\') }}">
          <i class="bi bi-box me-2"></i>Items Master
        </a>
        <a class="nav-link {{ request()->routeIs(\'suppliers.*\') ? \'active\' : \'\' }}" href="{{ route(\'suppliers.index\') }}">
          <i class="bi bi-shop me-2"></i>Suppliers
        </a>
        <a class="nav-link {{ request()->routeIs(\'users.*\') ? \'active\' : \'\' }}" href="{{ route(\'users.index\') }}">
          <i class="bi bi-people me-2"></i>Users & Roles
        </a>
        <a class="nav-link {{ request()->routeIs(\'audit-log.*\') ? \'active\' : \'\' }}" href="{{ route(\'audit-log.index\') }}">
          <i class="bi bi-journal-check me-2"></i>Audit Trail
        </a>

        <div style="border-top:1px solid rgba(255,255,255,0.1);margin-top:12px;padding:12px 20px;">
          @auth
          <div style="font-size:0.8rem;color:rgba(255,255,255,0.6);margin-bottom:6px">
            <i class="bi bi-person-circle me-1"></i>{{ auth()->user()->name }}<br>
            <span style="font-size:0.7rem;color:var(--denr-accent)">{{ ucfirst(str_replace(\'_\',\' \', auth()->user()->role)) }}</span>
          </div>
          <form method="POST" action="{{ route(\'logout\') }}">@csrf
            <button class="btn btn-sm btn-outline-light w-100">
              <i class="bi bi-box-arrow-right me-1"></i>Logout
            </button>
          </form>
          @endauth
        </div>
      </nav>
    </div>
    @endauth

    <!-- Main content -->
    <div class="main-content">
      @if(session(\'success\'))
        <div class="alert alert-success alert-dismissible fade show border-0 shadow-sm">
          <i class="bi bi-check-circle-fill me-2"></i>{{ session(\'success\') }}
          <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
      @endif
      @if(session(\'error\'))
        <div class="alert alert-danger alert-dismissible fade show border-0 shadow-sm">
          <i class="bi bi-exclamation-circle-fill me-2"></i>{{ session(\'error\') }}
          <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
      @endif
      @if($errors->any())
        <div class="alert alert-warning alert-dismissible fade show border-0 shadow-sm">
          <i class="bi bi-exclamation-triangle-fill me-2"></i>
          <strong>Please fix the following errors:</strong>
          <ul class="mb-0 mt-1">
            @foreach($errors->all() as $error)
              <li>{{ $error }}</li>
            @endforeach
          </ul>
          <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
      @endif
      @yield(\'content\')
    </div>
  </div>

  <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
  @stack(\'scripts\')
</body>
</html>
'''

with open('/var/www/bcs-ims/resources/views/layouts/app.blade.php', 'w', encoding='utf-8') as f:
    f.write(new_src)
print('Layout rewritten')
