with open('/var/www/quanby-legal/registry.html', 'r', encoding='utf-8') as f:
    src = f.read()

# ─── Fix CSV: headers must match data columns ────────────────────────────────
old_csv = '''    const headers = ['Registry #','Date','Document','Act Type','Workflow','Fee','DC Reference','DC Status','Principal','Principal Email','Witness','Witness Email','SC Synced','SC Registry ID','Location'];
    const rows = acts.map(a => [
      a.id || '',
      a.executed_at ? new Date(a.executed_at).toISOString().slice(0,10) : '',
      a.doc_name || '',
      a.act_type || '',
      a.principal_name || '',
      a.principal_email || '',
      a.witness_name || '',
      a.witness_email || '',
      a.dc_status || '',
      a.dc_reference_no || '',
      a.sc_synced ? 'Yes' : 'No',
      a.sc_registry_id || '',
      a.location || '',
    ].map(v => `"${String(v).replace(/"/g,'""')}"`));'''

new_csv = '''    const headers = [
      'Registry No.', 'Date Notarized', 'Document Name', 'Act Type', 'Fee (PHP)',
      'Principal Name', 'Principal Email', 'Witness', 'DC Reference No.',
      'DC Status', 'SC Synced', 'SC Registry ID (NRID)', 'Location',
      'ENP Name', 'Commission No.', 'Roll No.'
    ];
    const rows = acts.map(a => [
      String(a.id||'').slice(0,8).toUpperCase(),
      a.executed_at ? new Date(a.executed_at).toISOString().slice(0,10) : '',
      a.doc_name || '',
      a.act_type || a.notarization_type || '',
      a.fee || '₱100',
      a.principal_name || '',
      a.principal_email || '',
      a.witness_name || '',
      a.dc_reference_no || '',
      a.dc_status === 'completed' ? 'Completed' : (a.dc_status || ''),
      a.sc_synced ? 'Yes' : 'No',
      a.sc_registry_id || '',
      a.location || '',
      a.enp_name || '',
      a.commission_no || '',
      a.roll_no || '',
    ].map(v => '"' + String(v).replace(/"/g, '""') + '"'));'''

if old_csv in src:
    src = src.replace(old_csv, new_csv)
    print('CSV fixed: headers match data, all fields included')
else:
    print('CSV pattern not found')

# ─── Fix PDF: broken meta tags and improve layout ────────────────────────────
# Find and replace the PDF html generation
old_pdf_start = '''    const html = `<!DOCTYPE html>
<html><head><meta charset='UTF-8'>
<meta http-equiv=" cache-control content=
o-cache no-store must-revalidate>
 <meta http-equiv=pragma content=
o-cache>
 <title>Notarial Registry</title>'''

new_pdf_start = '''    const html = `<!DOCTYPE html>
<html><head><meta charset="UTF-8">
<title>Quanby Legal — Notarial Registry Export</title>'''

if old_pdf_start in src:
    src = src.replace(old_pdf_start, new_pdf_start)
    print('PDF meta tags fixed')
else:
    # Try regex approach
    import re
    broken = re.search(r'const html = `<!DOCTYPE html>.*?<title>Notarial Registry</title>', src, re.DOTALL)
    if broken:
        old_b = broken.group(0)
        new_b = 'const html = `<!DOCTYPE html>\n<html><head><meta charset="UTF-8">\n<title>Quanby Legal — Notarial Registry Export</title>'
        src = src.replace(old_b, new_b)
        print('PDF meta tags fixed via regex')
    else:
        print('PDF meta pattern not found')

# ─── Improve PDF table: add more columns and fix data ────────────────────────
old_pdf_row = '''      return `<tr style="${i%2===0?'background:#0f1220;':'background:#080b18;'}">
        <td>${String(a.id||'').slice(0,8).toUpperCase()}</td>
        <td>${actDate}</td>
        <td>${esc(a.doc_name||'—')}</td>
        <td><span style="background:rgba(14,165,233,.15);color:#38bdf8;padding:.1rem .4rem;border-radius:4px;font-size:.72rem;">${esc(a.act_type||'—')}</span></td>
        <td>${esc(a.principal_name||'—')}</td>
        <td>${a.dc_status === 'completed' ? 'Completed' : esc(a.dc_status||'—')}</td>
        <td>${nrid}</td>
      </tr>`;'''

new_pdf_row = '''      return `<tr style="${i%2===0?'background:#0f1220;':'background:#080b18;'}">
        <td style="font-weight:700;color:#c9a84c;font-size:.72rem;">${String(a.id||'').slice(0,8).toUpperCase()}</td>
        <td style="white-space:nowrap;">${actDate}</td>
        <td style="max-width:180px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="${esc(a.doc_name||'')}">${esc(a.doc_name||'—')}</td>
        <td>${esc(a.act_type||a.notarization_type||'—')}</td>
        <td>${esc(a.fee||'₱100')}</td>
        <td style="max-width:160px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${esc(a.principal_name||'—')}</td>
        <td>${a.dc_status === 'completed' ? '<span style="color:#6ee7b7;">Completed</span>' : esc(a.dc_status||'—')}</td>
        <td style="font-size:.7rem;">${nrid}</td>
      </tr>`;'''

if old_pdf_row in src:
    src = src.replace(old_pdf_row, new_pdf_row)
    print('PDF row data fixed: fee column added')
else:
    print('PDF row pattern not found')

# Fix PDF table headers to match
old_pdf_headers = '''<tr>
            <th>ACT #</th><th>DATE</th><th>DOCUMENT</th><th>TYPE</th><th>PRINCIPAL</th><th>DC STATUS</th><th>NRID</th>
          </tr>'''
new_pdf_headers = '''<tr>
            <th>ACT #</th><th>DATE</th><th>DOCUMENT</th><th>TYPE</th><th>FEE</th><th>PRINCIPAL</th><th>DC STATUS</th><th>NRID</th>
          </tr>'''
if old_pdf_headers in src:
    src = src.replace(old_pdf_headers, new_pdf_headers)
    print('PDF headers fixed: fee column added')

with open('/var/www/quanby-legal/registry.html', 'w', encoding='utf-8') as f:
    f.write(src)
print('Done')
