import sqlite3
import json
import uuid
from datetime import datetime, timezone

DB = '/var/www/quanby-builder/database/database.sqlite'
conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
c = conn.cursor()

now = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')

# --- 1. Copy BCS (id=9) → "Quanby Procurement with GAM Reports" ---
c.execute('SELECT * FROM builds WHERE id = 9')
bcs = dict(c.fetchone())

parsed = json.loads(bcs['parsed_specs']) if bcs['parsed_specs'] else {}
parsed['title'] = 'Quanby Procurement with GAM Reports'
parsed['agency'] = 'Quanby Solutions, Inc.'
if 'summary' in parsed:
    parsed['summary'] = parsed['summary'].replace('Bureau of Customs Support', 'Quanby Solutions, Inc.').replace('BCS', 'Quanby Procurement').replace('bcs.quanbyai.com', 'projects.quanbyai.com')

def fix_bcs(s):
    if not s: return s
    return s.replace('Bureau of Customs Support (BCS)', 'Quanby Solutions, Inc.')\
            .replace('Bureau of Customs Support', 'Quanby Solutions, Inc.')\
            .replace('BCS ', 'Quanby Procurement ')\
            .replace('bcs.quanbyai.com', 'projects.quanbyai.com')

c.execute('''INSERT INTO builds
    (title, client_name, client_agency, category, priority, status, description,
     raw_specs_text, ai_summary, parsed_specs, tech_stack,
     portal_token, created_by, created_at, updated_at, product_url, build_type)
    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''', (
    'Quanby Procurement with GAM Reports',
    'Quanby Solutions, Inc.',
    'Quanby Solutions, Inc.',
    bcs['category'],
    bcs['priority'],
    'finished',
    fix_bcs(bcs['description']),
    fix_bcs(bcs['raw_specs_text']),
    fix_bcs(bcs['ai_summary']),
    json.dumps(parsed),
    bcs['tech_stack'],
    uuid.uuid4().hex[:32],
    1, now, now,
    'https://projects.quanbyai.com',
    'project'
))
new_bcs_id = c.lastrowid
print(f'Created id={new_bcs_id}: Quanby Procurement with GAM Reports')

# Copy requirements
c.execute('SELECT * FROM build_requirements WHERE build_id = 9')
for r in c.fetchall():
    conn.execute('''INSERT INTO build_requirements
        (build_id, category, requirement_text, compliance_status, compliance_notes, priority, created_at, updated_at)
        VALUES (?,?,?,?,?,?,?,?)''',
        (new_bcs_id, r['category'], r['requirement_text'], r['compliance_status'], r['compliance_notes'], r['priority'], now, now))
print(f'  Requirements copied')

# --- 2. Copy QSign (id=12) → "Quanby DMS" ---
c.execute('SELECT * FROM builds WHERE id = 12')
qsign = dict(c.fetchone())

parsed_q = json.loads(qsign['parsed_specs']) if qsign['parsed_specs'] else {}
parsed_q['title'] = 'Quanby DMS'
parsed_q['agency'] = 'Quanby Solutions, Inc.'
if 'summary' in parsed_q:
    parsed_q['summary'] = parsed_q['summary'].replace('Department of Environment and Natural Resources', 'Quanby Solutions, Inc.')\
        .replace('DENR', 'Quanby').replace('QSign', 'Quanby DMS').replace('qsign.quanbyai.com', 'edms.quanbyai.com')

def fix_qsign(s):
    if not s: return s
    return s.replace('Department of Environment and Natural Resources (DENR)', 'Quanby Solutions, Inc.')\
            .replace('Department of Environment and Natural Resources', 'Quanby Solutions, Inc.')\
            .replace('DENR', 'Quanby')\
            .replace('QSign', 'Quanby DMS')\
            .replace('qsign.quanbyai.com', 'edms.quanbyai.com')

c.execute('''INSERT INTO builds
    (title, client_name, client_agency, category, priority, status, description,
     raw_specs_text, ai_summary, parsed_specs, tech_stack,
     portal_token, created_by, created_at, updated_at, product_url, build_type)
    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''', (
    'Quanby DMS',
    'Quanby Solutions, Inc.',
    'Quanby Solutions, Inc.',
    'Document Management System',
    qsign['priority'],
    'finished',
    fix_qsign(qsign['description']),
    fix_qsign(qsign['raw_specs_text']),
    fix_qsign(qsign['ai_summary']),
    json.dumps(parsed_q),
    qsign['tech_stack'],
    uuid.uuid4().hex[:32],
    1, now, now,
    'https://edms.quanbyai.com',
    'project'
))
new_qsign_id = c.lastrowid
print(f'Created id={new_qsign_id}: Quanby DMS')

# Copy requirements
c.execute('SELECT * FROM build_requirements WHERE build_id = 12')
for r in c.fetchall():
    conn.execute('''INSERT INTO build_requirements
        (build_id, category, requirement_text, compliance_status, compliance_notes, priority, created_at, updated_at)
        VALUES (?,?,?,?,?,?,?,?)''',
        (new_qsign_id, r['category'], r['requirement_text'], r['compliance_status'], r['compliance_notes'], r['priority'], now, now))
print(f'  Requirements copied')

conn.commit()
conn.close()

# Verify
print()
conn2 = sqlite3.connect(DB)
for row in conn2.execute('SELECT id, title, status, product_url FROM builds ORDER BY id'):
    print(f'  [{row[0]}] {row[1]} | {row[2]} | {row[3]}')
conn2.close()
