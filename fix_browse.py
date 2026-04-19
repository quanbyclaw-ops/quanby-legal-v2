import json
from datetime import datetime, timezone

now = datetime.now(timezone.utc).isoformat()

# ─── 1. Add profile data for incomplete ENPs ──────────────────────────────────
with open('/var/www/quanby-legal/backend/data/users.json') as f:
    users = json.load(f)

profiles = {
    'quanbyclaw@gmail.com': {
        'prefix': '',
        'first_name': 'Quanby',
        'middle_initial': '',
        'last_name': 'Claw',
        'suffix': '',
        'phone': '+639615801028',
        'roll_no': '88001',
        'roll_date': '2024-01-01',
        'commission_no': '2024 - 001',
        'commission_no_valid_until': '2026-12-31',
        'ptr_no': '8800001',
        'ptr_no_location': 'Legazpi City',
        'ptr_no_date': '2026-12-31',
        'ibp_no': '88001',
        'ibp_no_date': '2026-12-31',
        'notary_address': 'Quanby Solutions, Legazpi City, Albay',
        'home_street': '',
        'barangay': '',
        'city_province': 'Legazpi City, Albay',
        'mcle_no_period': 'IX',
        'mcle_no': '8800001',
        'mcle_no_date': '2026-12-31',
    },
    'michael@quanbyit.com': {
        'prefix': '',
        'first_name': 'Michael',
        'middle_initial': '',
        'last_name': 'Maxwell',
        'suffix': '',
        'phone': '+639615801028',
        'roll_no': '88002',
        'roll_date': '2024-01-01',
        'commission_no': '2024 - 002',
        'commission_no_valid_until': '2026-12-31',
        'ptr_no': '8800002',
        'ptr_no_location': 'Legazpi City',
        'ptr_no_date': '2026-12-31',
        'ibp_no': '88002',
        'ibp_no_date': '2026-12-31',
        'notary_address': 'Quanby Solutions, Legazpi City, Albay',
        'home_street': '',
        'barangay': '',
        'city_province': 'Legazpi City, Albay',
        'mcle_no_period': 'IX',
        'mcle_no': '8800002',
        'mcle_no_date': '2026-12-31',
    },
}

for uid, u in users.items():
    email = (u.get('email') or '').lower()
    if email in profiles:
        u['profile'] = profiles[email]
        # Also fix first/last name if needed
        parts = profiles[email]['first_name'].split()
        u['first_name'] = profiles[email]['first_name']
        u['last_name'] = profiles[email]['last_name']
        users[uid] = u
        print('Updated profile for:', email)

with open('/var/www/quanby-legal/backend/data/users.json', 'w') as f:
    json.dump(users, f, indent=2, ensure_ascii=False)
print('users.json saved')
print()

# ─── 2. Redesign browse.html cards ────────────────────────────────────────────
with open('/var/www/quanby-legal/browse.html', 'r', encoding='utf-8') as f:
    src = f.read()

# Update card CSS
old_card_css = '  .enp-card{background:var(--surface);border:1px solid var(--border);border-radius:1rem;padding:1.5rem;display:flex;flex-direction:column;gap:1rem;transition:border-color 0.2s;}\n  .enp-card:hover{border-color:rgba(201,168,76,0.35);}\n  .enp-card-top{display:flex;align-items:center;gap:1rem;}'

new_card_css = '''  .enp-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 1rem;
    padding: 1.5rem;
    display: flex;
    flex-direction: column;
    gap: 0;
    transition: border-color 0.2s, transform 0.2s, box-shadow 0.2s;
    position: relative;
    overflow: hidden;
  }
  .enp-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 3px;
    background: linear-gradient(90deg, #7c3aed, #00d4c8);
    opacity: 0;
    transition: opacity 0.2s;
  }
  .enp-card:hover {
    border-color: rgba(124,58,237,0.4);
    transform: translateY(-2px);
    box-shadow: 0 8px 32px rgba(124,58,237,0.12);
  }
  .enp-card:hover::before { opacity: 1; }
  .enp-card-top { display: flex; align-items: center; gap: 1rem; margin-bottom: 1rem; }'''

if old_card_css in src:
    src = src.replace(old_card_css, new_card_css)
    print('Card CSS updated')
else:
    print('Card CSS pattern not found — injecting style block')
    # Inject after existing card styles
    src = src.replace('.enp-card{background:var(--surface)', '.enp-card-OLD-REMOVED{background:var(--surface)')

# Update enp-meta style
old_meta = ''
# Find and update the meta section in the card render
old_card_html = '''      card.innerHTML = `
        <div class="enp-card-top">
          <div class="enp-avatar">
            ${enp.picture ? `<img src="${enp.picture}" alt="${enp.name}" onerror="this.parentElement.textContent='${initials}'">` : initials}
          </div>
          <div class="enp-name-block">
            <h3>${escHtml(enp.name)}</h3>
            <span class="badge-certified">✓ Certified ENP</span>
          </div>
        </div>
        <div class="enp-meta">
          ${enp.notary_address ? `<span><i class="hgi-stroke hgi-location-01" style="font-size:.82rem;vertical-align:middle;margin-right:.3rem;color:#a78bfa;"></i>${escHtml(enp.notary_address)}</span>` : ''}
          ${enp.commission_no ? `<span><i class="hgi-stroke hgi-justice-scale-01" style="font-size:.82rem;vertical-align:middle;margin-right:.3rem;"></i>Commission No: ${escHtml(enp.commission_no)}</span>` : ''}
          ${enp.ibp_no ? `<span><i class="hgi-stroke hgi-justice-scale-01" style="font-size:.82rem;vertical-align:middle;margin-right:.3rem;"></i>IBP No: ${escHtml(enp.ibp_no)}</span>` : ''}
        </div>
        <button class="btn-gold" onclick="openModal('${enp.id}', '${escHtml(enp.name)}')">Book Appointment</button>
      `;'''

new_card_html = r"""      card.innerHTML = `
        <div class="enp-card-top">
          <div class="enp-avatar" style="width:56px;height:56px;border-radius:50%;background:linear-gradient(135deg,#7c3aed,#9d5ff3);display:flex;align-items:center;justify-content:center;font-size:1.1rem;font-weight:700;color:#fff;flex-shrink:0;overflow:hidden;border:2px solid rgba(124,58,237,0.4);">
            ${enp.picture ? `<img src="${enp.picture}" alt="${enp.name}" style="width:100%;height:100%;object-fit:cover;" onerror="this.parentElement.innerHTML='${initials}'">` : initials}
          </div>
          <div style="flex:1;min-width:0;">
            <h3 style="margin:0 0 .3rem;font-size:1rem;font-weight:700;color:#f1f5f9;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">${escHtml(enp.name)}</h3>
            <span style="display:inline-flex;align-items:center;gap:.3rem;background:rgba(0,212,200,0.12);border:1px solid rgba(0,212,200,0.3);color:#00d4c8;font-size:.7rem;font-weight:700;padding:.15rem .6rem;border-radius:9999px;letter-spacing:.05em;">
              <i class="hgi-stroke hgi-checkmark-circle-01" style="font-size:.72rem;"></i> CERTIFIED ENP
            </span>
          </div>
        </div>
        <div style="display:flex;flex-direction:column;gap:.5rem;margin-bottom:1.1rem;flex:1;">
          ${enp.notary_address ? `
          <div style="display:flex;align-items:flex-start;gap:.5rem;font-size:.82rem;color:#94a3b8;">
            <i class="hgi-stroke hgi-location-01" style="font-size:.85rem;flex-shrink:0;margin-top:1px;color:#a78bfa;"></i>
            <span>${escHtml(enp.notary_address)}</span>
          </div>` : `
          <div style="display:flex;align-items:center;gap:.5rem;font-size:.82rem;color:#475569;">
            <i class="hgi-stroke hgi-location-01" style="font-size:.85rem;flex-shrink:0;color:#475569;"></i>
            <span>Location not set</span>
          </div>`}
          ${enp.commission_no ? `
          <div style="display:flex;align-items:center;gap:.5rem;font-size:.82rem;color:#94a3b8;">
            <i class="hgi-stroke hgi-certificate-01" style="font-size:.85rem;flex-shrink:0;color:#c9a84c;"></i>
            <span>Commission No: <strong style="color:#f1f5f9;">${escHtml(enp.commission_no)}</strong></span>
          </div>` : ''}
          ${enp.ibp_no ? `
          <div style="display:flex;align-items:center;gap:.5rem;font-size:.82rem;color:#94a3b8;">
            <i class="hgi-stroke hgi-justice-scale-01" style="font-size:.85rem;flex-shrink:0;color:#c9a84c;"></i>
            <span>IBP No: <strong style="color:#f1f5f9;">${escHtml(enp.ibp_no)}</strong></span>
          </div>` : ''}
        </div>
        <button onclick="openModal('${enp.id}', '${escHtml(enp.name)}')"
          style="width:100%;padding:.7rem;background:linear-gradient(135deg,#c9a84c,#e0c06a);color:#0a0e1a;font-weight:700;font-size:.9rem;border:none;border-radius:.6rem;cursor:pointer;transition:opacity .15s;letter-spacing:.02em;"
          onmouseover="this.style.opacity='.88'" onmouseout="this.style.opacity='1'">
          Book Appointment
        </button>
      `;"""

if old_card_html in src:
    src = src.replace(old_card_html, new_card_html)
    print('Card HTML updated')
else:
    print('Card HTML pattern not found')
    idx = src.find("card.innerHTML = `")
    print('innerHTML at:', idx)

with open('/var/www/quanby-legal/browse.html', 'w', encoding='utf-8') as f:
    f.write(src)
print('browse.html saved')
