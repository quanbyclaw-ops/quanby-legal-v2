import re

# ════════════════════════════════════════════════════════════════
# FIX 1: Remove Quanby nav bar from BCS IMS
# ════════════════════════════════════════════════════════════════
with open('/var/www/bcs-ims/resources/views/layouts/app.blade.php', 'r', encoding='utf-8') as f:
    bcs = f.read()

# Remove everything between the QUANBY UNIFIED NAV comments
bcs = re.sub(
    r'<!-- ===== QUANBY UNIFIED NAV ===== -->.*?<!-- ===== END QUANBY UNIFIED NAV ===== -->',
    '',
    bcs,
    flags=re.DOTALL
)
# Remove the padding-top that was added for the nav
bcs = bcs.replace('    body { padding-top: 64px !important; }', '')
bcs = bcs.replace('    @media (max-width: 900px) { #qnav .qnav-links { display: none; } }', '')
# Clean up blank lines
bcs = re.sub(r'\n{3,}', '\n\n', bcs)

with open('/var/www/bcs-ims/resources/views/layouts/app.blade.php', 'w', encoding='utf-8') as f:
    f.write(bcs)
print('Fix 1: BCS nav bar removed')

# ════════════════════════════════════════════════════════════════
# FIX 2: Pricing cards redesign on Quanby Legal landing page
# ════════════════════════════════════════════════════════════════
with open('/var/www/quanby-legal/index.html', 'r', encoding='utf-8') as f:
    idx = f.read()

# Replace pricing CSS
old_pricing_css = '''        /* PRICING */
        .pricing-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 2rem; margin-top: 1.5rem; }
        .pricing-card { position: relative; }
        .pricing-card.popular { padding-top: 2rem; }
        .popular-badge {
            position: absolute; top: -1rem; left: 50%; transform: translateX(-50%);
            background: var(--pink); padding: 0.25rem 0.75rem;
            border-radius: 9999px; font-size: 0.75rem; font-weight: bold;
        }
        .tier-name { font-size: 1.5rem; font-weight: 600; margin-bottom: 0.5rem; }
        .tier-price { font-size: 2rem; margin-bottom: 1rem; }
        .tier-features { list-style: none; color: var(--muted); }
        .tier-features li { margin-bottom: 0.5rem; }
        .tier-features li::before { content: "✓ "; color: var(--teal); }'''

new_pricing_css = '''        /* PRICING */
        #pricing { background: radial-gradient(ellipse at 50% 0%, rgba(124,58,237,0.07) 0%, transparent 65%); }
        .pricing-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 1.5rem;
            margin-top: 2rem;
            align-items: stretch;
        }
        @media (max-width: 900px) { .pricing-grid { grid-template-columns: 1fr; max-width: 420px; margin-left: auto; margin-right: auto; } }
        .pricing-card {
            position: relative;
            background: rgba(255,255,255,0.03);
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 1.25rem;
            padding: 2rem 1.75rem;
            display: flex;
            flex-direction: column;
            transition: border-color 0.2s, transform 0.2s;
        }
        .pricing-card:hover { border-color: rgba(124,58,237,0.4); transform: translateY(-2px); }
        .pricing-card.popular {
            background: rgba(124,58,237,0.08);
            border-color: #7c3aed;
            box-shadow: 0 0 0 1px #7c3aed, 0 20px 60px rgba(124,58,237,0.2);
        }
        .popular-badge {
            position: absolute; top: -0.75rem; left: 50%; transform: translateX(-50%);
            background: linear-gradient(135deg, #7c3aed, #9d5ff3);
            color: #fff; padding: 0.2rem 1rem;
            border-radius: 9999px; font-size: 0.7rem; font-weight: 700;
            letter-spacing: 0.08em; white-space: nowrap;
        }
        .tier-label {
            font-size: 0.72rem; font-weight: 700; text-transform: uppercase;
            letter-spacing: 0.1em; color: var(--muted); margin-bottom: 0.6rem;
        }
        .pricing-card.popular .tier-label { color: #c4b5fd; }
        .tier-name { font-size: 1.6rem; font-weight: 800; margin-bottom: 0.4rem; color: var(--text); }
        .tier-price {
            font-size: 2.75rem; font-weight: 800; margin-bottom: 0.3rem;
            background: linear-gradient(135deg, #fff 60%, rgba(255,255,255,0.6));
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        .pricing-card.popular .tier-price {
            background: linear-gradient(135deg, #c4b5fd, #a78bfa);
            -webkit-background-clip: text; background-clip: text;
        }
        .tier-price-sub { font-size: 0.85rem; color: var(--muted); margin-bottom: 1.5rem; }
        .tier-divider { height: 1px; background: rgba(255,255,255,0.07); margin: 1.25rem 0; }
        .pricing-card.popular .tier-divider { background: rgba(124,58,237,0.3); }
        .tier-features { list-style: none; padding: 0; margin: 0 0 1.75rem; flex: 1; }
        .tier-features li {
            display: flex; align-items: flex-start; gap: 0.6rem;
            padding: 0.4rem 0; font-size: 0.88rem; color: rgba(226,232,240,0.85);
            border-bottom: 1px solid rgba(255,255,255,0.04);
        }
        .tier-features li:last-child { border-bottom: none; }
        .tier-features li::before {
            content: "✓"; flex-shrink: 0; width: 18px; height: 18px;
            background: rgba(0,212,200,0.15); color: #00d4c8;
            border-radius: 50%; display: flex; align-items: center; justify-content: center;
            font-size: 0.65rem; font-weight: 800; margin-top: 2px;
        }
        .pricing-card.popular .tier-features li::before {
            background: rgba(124,58,237,0.2); color: #c4b5fd;
        }
        .pricing-cta { margin-top: auto; }'''

if old_pricing_css in idx:
    idx = idx.replace(old_pricing_css, new_pricing_css)
    print('Pricing CSS replaced')
else:
    print('WARNING: pricing CSS pattern not found')

# Replace pricing HTML cards
old_pricing_html = '''<section id="pricing">
        <div class="container">
            <h2>Simple, transparent pricing</h2>
            <p class="section-subtitle">Start free, scale as you grow</p>
            <div class="pricing-grid">
                <div class="pricing-card card">
                    <div class="tier-name">Starter</div>
                    <div class="tier-price">Free</div>
                    <ul class="tier-features">
                        <li>5 notarizations/month</li>
                        <li>Basic AI contract analysis</li>
                        <li>Basic eKYC</li>
                        <li>PDF export</li>
                    </ul>
                    <button class="btn btn-outline" style="width:100%;margin-top:1.5rem">Get started</button>
                </div>
                <div class="pricing-card popular card" style="border-color:var(--purple);position:relative">
                    <div class="popular-badge">MOST POPULAR</div>
                    <div class="tier-name">Professional</div>
                    <div class="tier-price">₱2,999<span style="font-size:1rem;color:var(--muted)">/mo</span></div>
                    <ul class="tier-features">
                        <li>100 notarizations/month</li>
                        <li>Full AI Contract Agent</li>
                        <li>Full PKI verification</li>
                        <li>Blockchain audit trail</li>
                        <li>Priority support</li>
                    </ul>
                    <button class="btn btn-filled" style="width:100%;margin-top:1.5rem">Start free trial</button>
                </div>
                <div class="pricing-card card">
                    <div class="tier-name">Enterprise</div>
                    <div class="tier-price">Custom</div>
                    <ul class="tier-features">
                        <li>Unlimited notarizations</li>
                        <li>Dedicated infrastructure</li>
                        <li>Custom AI training</li>
                        <li>99.9% SLA</li>
                        <li>Dedicated ENP team</li>
                    </ul>
                    <button class="btn btn-outline" style="width:100%;margin-top:1.5rem">Contact sales</button>
                </div>
            </div>
        </div>
    </section>'''

new_pricing_html = '''<section id="pricing">
        <div class="container">
            <h2>Simple, transparent pricing</h2>
            <p class="section-subtitle">Start free, scale as you grow</p>
            <div class="pricing-grid">

                <!-- Starter -->
                <div class="pricing-card">
                    <div class="tier-label">Starter</div>
                    <div class="tier-name">Free</div>
                    <div class="tier-price-sub">No credit card required</div>
                    <div class="tier-divider"></div>
                    <ul class="tier-features">
                        <li>5 notarizations/month</li>
                        <li>Basic AI contract analysis</li>
                        <li>Basic eKYC verification</li>
                        <li>PDF export</li>
                    </ul>
                    <div class="pricing-cta">
                        <button class="btn btn-outline" onclick="openSSO('client')" style="width:100%;">Get started free</button>
                    </div>
                </div>

                <!-- Professional -->
                <div class="pricing-card popular">
                    <div class="popular-badge">✦ MOST POPULAR</div>
                    <div class="tier-label">Professional</div>
                    <div class="tier-name">₱2,999</div>
                    <div class="tier-price-sub">per month · billed monthly</div>
                    <div class="tier-divider"></div>
                    <ul class="tier-features">
                        <li>100 notarizations/month</li>
                        <li>Full AI Contract Agent</li>
                        <li>Full PKI verification</li>
                        <li>Blockchain audit trail</li>
                        <li>Priority support</li>
                    </ul>
                    <div class="pricing-cta">
                        <button class="btn btn-filled" onclick="openSSO('client')" style="width:100%;background:linear-gradient(135deg,#7c3aed,#9d5ff3);border:none;font-weight:700;">Start free trial →</button>
                    </div>
                </div>

                <!-- Enterprise -->
                <div class="pricing-card">
                    <div class="tier-label">Enterprise</div>
                    <div class="tier-name">Custom</div>
                    <div class="tier-price-sub">Talk to our team</div>
                    <div class="tier-divider"></div>
                    <ul class="tier-features">
                        <li>Unlimited notarizations</li>
                        <li>Dedicated infrastructure</li>
                        <li>Custom AI training</li>
                        <li>99.9% uptime SLA</li>
                        <li>Dedicated ENP team</li>
                    </ul>
                    <div class="pricing-cta">
                        <button class="btn btn-outline" onclick="document.getElementById('faq').scrollIntoView({behavior:'smooth'})" style="width:100%;">Contact sales →</button>
                    </div>
                </div>

            </div>
        </div>
    </section>'''

if old_pricing_html in idx:
    idx = idx.replace(old_pricing_html, new_pricing_html)
    print('Pricing HTML replaced')
else:
    print('WARNING: pricing HTML not found — checking...')
    pos = idx.find('<section id="pricing">')
    print('Found pricing section at:', pos)

with open('/var/www/quanby-legal/index.html', 'w', encoding='utf-8') as f:
    f.write(idx)
print('Fix 2: Pricing cards redesigned')

# ════════════════════════════════════════════════════════════════
# FIX 3: Retheme DMS (opapru-edms) to Quanby Legal colors
# ════════════════════════════════════════════════════════════════
# Quanby Legal palette:
# --ql-navy: #1e3a5f  (sidebar/surface)
# --ql-navy-dark: #0a0e1a  (body bg)
# --ql-navy-mid: #0f1521  (sidebar brand, cards)
# --ql-teal: #00d4c8  (accent / active)
# --ql-purple: #7c3aed  (primary buttons)
# --ql-border: rgba(255,255,255,0.08)

with open('/var/www/opapru-edms/resources/views/layouts/app.blade.php', 'r', encoding='utf-8') as f:
    dms = f.read()

# Replace the entire :root + body + component CSS block
old_dms_css = '''        :root {
            --sidebar-bg: #0f172a;
            --sidebar-width: 260px;
            --topbar-height: 60px;
        }
        body { background-color: #0f172a; color: #e2e8f0; }
        #sidebar {
            width: var(--sidebar-width);
            min-height: 100vh;
            background: #1e293b;
            border-right: 1px solid #334155;
            position: fixed;
            top: 0; left: 0;
            z-index: 100;
            transition: all 0.3s;
        }
        #sidebar .sidebar-brand {
            height: var(--topbar-height);
            display: flex; align-items: center;
            padding: 0 1.25rem;
            background: #0f172a;
            border-bottom: 1px solid #334155;
        }
        #sidebar .nav-link {
            color: #94a3b8;
            padding: 0.6rem 1.25rem;
            border-radius: 0.375rem;
            margin: 0.1rem 0.5rem;
            transition: all 0.2s;
            font-size: 0.9rem;
        }
        #sidebar .nav-link:hover, #sidebar .nav-link.active {
            color: #f1f5f9;
            background: #334155;
        }
        #sidebar .nav-link i { width: 20px; text-align: center; margin-right: 8px; }
        #main-content {
            margin-left: var(--sidebar-width);
            min-height: 100vh;
        }
        #topbar {
            height: var(--topbar-height);
            background: #1e293b;
            border-bottom: 1px solid #334155;
            display: flex; align-items: center;
            padding: 0 1.5rem;
            position: sticky; top: 0;
            z-index: 99;
        }
        .content-area { padding: 1.5rem; }
        .card {
            background: #1e293b;
            border: 1px solid #334155;
            border-radius: 0.5rem;
        }
        .card-header { background: #162032; border-bottom: 1px solid #334155; }
        .table { color: #cbd5e1; }
        .table th { color: #94a3b8; border-color: #334155; font-weight: 500; font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.05em; }
        .table td { border-color: #334155; vertical-align: middle; }
        .table-hover tbody tr:hover { background-color: rgba(51,65,85,0.4); }
        .form-control, .form-select {
            background-color: #0f172a;
            border-color: #334155;
            color: #e2e8f0;
        }
        .form-control:focus, .form-select:focus {
            background-color: #0f172a;
            border-color: #60a5fa;
            color: #e2e8f0;
            box-shadow: 0 0 0 0.2rem rgba(96,165,250,0.15);
        }
        .btn-primary { background: #2563eb; border-color: #2563eb; }
        .btn-primary:hover { background: #1d4ed8; border-color: #1d4ed8; }
        .stat-card { border-left: 3px solid; }
        .stat-card.primary { border-color: #2563eb; }
        .stat-card.success { border-color: #16a34a; }
        .stat-card.warning { border-color: #d97706; }
        .stat-card.danger  { border-color: #dc2626; }
        .sidebar-section { padding: 0.5rem 1rem; font-size: 0.7rem; color: #475569; text-transform: uppercase; letter-spacing: 0.1em; margin-top: 0.5rem; }'''

new_dms_css = '''        :root {
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
            --sidebar-width: 260px;
            --topbar-height: 60px;
        }
        body { background-color: var(--ql-navy-dark); color: var(--ql-text); font-family: \'Inter\', \'Segoe UI\', sans-serif; }
        #sidebar {
            width: var(--sidebar-width);
            min-height: 100vh;
            background: var(--ql-navy);
            border-right: 1px solid var(--ql-border);
            position: fixed;
            top: 0; left: 0;
            z-index: 100;
            transition: all 0.3s;
        }
        #sidebar .sidebar-brand {
            height: var(--topbar-height);
            display: flex; align-items: center;
            padding: 0 1.25rem;
            background: rgba(0,0,0,0.2);
            border-bottom: 1px solid var(--ql-border);
        }
        #sidebar .nav-link {
            color: rgba(226,232,240,0.65);
            padding: 0.55rem 1.25rem;
            border-radius: 0.375rem;
            margin: 0.1rem 0.5rem;
            transition: all 0.2s;
            font-size: 0.875rem;
            border-left: 2px solid transparent;
        }
        #sidebar .nav-link:hover {
            color: var(--ql-teal);
            background: rgba(0,212,200,0.06);
        }
        #sidebar .nav-link.active {
            color: var(--ql-purple-light);
            background: rgba(124,58,237,0.12);
            border-left-color: var(--ql-purple);
        }
        #sidebar .nav-link i { width: 20px; text-align: center; margin-right: 8px; }
        #main-content {
            margin-left: var(--sidebar-width);
            min-height: 100vh;
        }
        #topbar {
            height: var(--topbar-height);
            background: var(--ql-navy);
            border-bottom: 1px solid var(--ql-border);
            display: flex; align-items: center;
            padding: 0 1.5rem;
            position: sticky; top: 0;
            z-index: 99;
        }
        .content-area { padding: 1.5rem; }
        .card {
            background: var(--ql-surface);
            border: 1px solid var(--ql-border);
            border-radius: 0.75rem;
        }
        .card-header {
            background: var(--ql-surface2);
            border-bottom: 1px solid var(--ql-border);
            font-weight: 600;
        }
        .table { color: var(--ql-text); }
        .table th { color: var(--ql-muted); border-color: var(--ql-border); font-weight: 500; font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.05em; }
        .table td { border-color: var(--ql-border); vertical-align: middle; }
        .table-hover tbody tr:hover { background-color: rgba(0,212,200,0.04); }
        .form-control, .form-select {
            background-color: rgba(0,0,0,0.2);
            border-color: var(--ql-border);
            color: var(--ql-text);
        }
        .form-control:focus, .form-select:focus {
            background-color: rgba(0,0,0,0.2);
            border-color: var(--ql-teal);
            color: var(--ql-text);
            box-shadow: 0 0 0 0.2rem rgba(0,212,200,0.15);
        }
        .btn-primary { background: var(--ql-purple); border-color: var(--ql-purple); }
        .btn-primary:hover { background: #6d28d9; border-color: #6d28d9; }
        .btn-success { background: var(--ql-teal); border-color: var(--ql-teal); color: #0a0e1a; font-weight: 600; }
        .btn-success:hover { background: #00b8ad; border-color: #00b8ad; color: #0a0e1a; }
        .stat-card { border-left: 3px solid; }
        .stat-card.primary { border-color: var(--ql-purple); }
        .stat-card.success { border-color: var(--ql-teal); }
        .stat-card.warning { border-color: #f59e0b; }
        .stat-card.danger  { border-color: #f87171; }
        .sidebar-section { padding: 0.5rem 1rem; font-size: 0.68rem; color: rgba(148,163,184,0.5); text-transform: uppercase; letter-spacing: 0.1em; margin-top: 0.5rem; }
        .badge.bg-primary { background-color: var(--ql-purple) !important; }
        .badge.bg-success { background-color: var(--ql-teal) !important; color: #0a0e1a !important; }
        .text-primary { color: var(--ql-teal) !important; }
        a { color: var(--ql-teal); }
        a:hover { color: var(--ql-purple-light); }
        .alert-success { background: rgba(0,212,200,0.1); border-color: rgba(0,212,200,0.3); color: var(--ql-teal); }
        .alert-danger { background: rgba(248,113,113,0.1); border-color: rgba(248,113,113,0.3); color: #f87171; }
        .alert-warning { background: rgba(245,158,11,0.1); border-color: rgba(245,158,11,0.3); color: #fbbf24; }
        .pagination .page-link { background: var(--ql-surface); border-color: var(--ql-border); color: var(--ql-muted); }
        .pagination .page-item.active .page-link { background: var(--ql-purple); border-color: var(--ql-purple); }'''

if old_dms_css in dms:
    dms = dms.replace(old_dms_css, new_dms_css)
    print('DMS CSS replaced')
else:
    print('WARNING: DMS CSS pattern not found')

# Update sidebar brand icon color
dms = dms.replace(
    '<i class="bi bi-folder2-open text-primary me-2 fs-5"></i>',
    '<i class="bi bi-folder2-open me-2 fs-5" style="color:var(--ql-teal)"></i>'
)

with open('/var/www/opapru-edms/resources/views/layouts/app.blade.php', 'w', encoding='utf-8') as f:
    f.write(dms)
print('Fix 3: DMS rethemed with Quanby Legal colors')

# Also fix DMS login page colors
with open('/var/www/opapru-edms/resources/views/auth/login.blade.php', 'r', encoding='utf-8') as f:
    dms_login = f.read()

# Replace primary color in login with Quanby Legal
dms_login = re.sub(r'#2563eb', '#7c3aed', dms_login)
dms_login = re.sub(r'#1d4ed8', '#6d28d9', dms_login)
dms_login = re.sub(r'#1e293b', '#1e3a5f', dms_login)
dms_login = re.sub(r'#0f172a', '#0a0e1a', dms_login)
dms_login = re.sub(r'#334155', 'rgba(255,255,255,0.08)', dms_login)

with open('/var/www/opapru-edms/resources/views/auth/login.blade.php', 'w', encoding='utf-8') as f:
    f.write(dms_login)
print('DMS login page recolored')

print()
print('All 3 fixes complete.')
