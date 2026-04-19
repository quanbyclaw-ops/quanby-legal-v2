import sqlite3
import json
import uuid
from datetime import datetime

DB = '/var/www/quanby-builder/database/database.sqlite'
conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
c = conn.cursor()

now = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')

# --- Copy BCS (id=9) as "Quanby Procurement with GAM Reports" ---
c.execute('SELECT * FROM builds WHERE id = 9')
bcs = dict(c.fetchone())

# Update parsed_specs title
parsed = json.loads(bcs['parsed_specs']) if bcs['parsed_specs'] else {}
parsed['title'] = 'Quanby Procurement with GAM Reports'
parsed['agency'] = 'Quanby Solutions, Inc.'
parsed['summary'] = parsed.get('summary','').replace('Bureau of Customs Support', 'Quanby Solutions, Inc.').replace('BCS', 'Quanby Procurement')

c.execute('''INSERT INTO builds
    (title, client_name, client_agency, category, priority, status, description,
     raw_specs_text, specs_file_path, ai_summary, parsed_specs, tech_stack,
     project_budget, output_dir, portal_token, created_by, created_at, updated_at,
     product_url, build_type)
    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''', (
    'Quanby Procurement with GAM Reports',
    'Quanby Solutions, Inc.',
    'Quanby Solutions, Inc.',
    bcs['category'],
    bcs['priority'],
    'finished',
    bcs['description'].replace('Bureau of Customs Support', 'Quanby Solutions, Inc.').replace('BCS', 'Quanby Procurement').replace('bcs.quanbyai.com', 'projects.quanbyai.com'),
    bcs['raw_specs_text'].replace('BCS', 'Quanby Procurement').replace('Bureau of Customs Support', 'Quanby Solutions, Inc.').replace('bcs.quanbyai.com', 'projects.quanbyai.com') if bcs['raw_specs_text'] else None,
    None,  # no specs file
    bcs['ai_summary'].replace('Bureau of Customs Support', 'Quanby Solutions, Inc.').replace('BCS', 'Quanby Procurement').replace('bcs.quanbyai.com', 'projects.quanbyai.com') if bcs['ai_summary'] else None,
    json.dumps(parsed),
    bcs['tech_stack'],
    None,
    None,  # no output_dir
    uuid.uuid4().hex[:32],
    1,
    now,
    now,
    'https://projects.quanbyai.com',
    'project'
))
new_bcs_id = c.lastrowid
print(f'Created BCS copy → id={new_bcs_id}: Quanby Procurement with GAM Reports')

# Copy requirements from BCS (build_requirements)
c.execute('SELECT * FROM build_requirements WHERE build_id = 9')
reqs = c.fetchall()
for r in reqs:
    c.execute('''INSERT INTO build_requirements (build_id, category, requirement, priority, compliance_note, created_at, updated_at)
                 VALUES (?,?,?,?,?,?,?)''',
              (new_bcs_id, r['category'], r['requirement'], r['priority'], r['compliance_note'], now, now))
print(f'  Copied {len(reqs)} requirements')

# --- Copy QSign (id=12) as "Quanby DMS" ---
c.execute('SELECT * FROM builds WHERE id = 12')
qsign = dict(c.fetchone())

parsed_q = json.loads(qsign['parsed_specs']) if qsign['parsed_specs'] else {}
parsed_q['title'] = 'Quanby DMS'
parsed_q['agency'] = 'Quanby Solutions, Inc.'
parsed_q['summary'] = parsed_q.get('summary','').replace('Department of Environment and Natural Resources', 'Quanby Solutions, Inc.').replace('DENR', 'Quanby').replace('QSign', 'Quanby DMS')

c.execute('''INSERT INTO builds
    (title, client_name, client_agency, category, priority, status, description,
     raw_specs_text, specs_file_path, ai_summary, parsed_specs, tech_stack,
     project_budget, output_dir, portal_token, created_by, created_at, updated_at,
     product_url, build_type)
    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''', (
    'Quanby DMS',
    'Quanby Solutions, Inc.',
    'Quanby Solutions, Inc.',
    'Document Management System',
    qsign['priority'],
    'finished',
    qsign['description'].replace('Department of Environment and Natural Resources', 'Quanby Solutions, Inc.').replace('DENR', 'Quanby').replace('QSign', 'Quanby DMS').replace('qsign.quanbyai.com', 'edms.quanbyai.com'),
    qsign['raw_specs_text'].replace('QSign', 'Quanby DMS').replace('DENR', 'Quanby').replace('Department of Environment and Natural Resources', 'Quanby Solutions, Inc.').replace('qsign.quanbyai.com', 'edms.quanbyai.com') if qsign['raw_specs_text'] else None,
    None,
    qsign['ai_summary'].replace('Department of Environment and Natural Resources', 'Quanby Solutions, Inc.').replace('DENR', 'Quanby').replace('QSign', 'Quanby DMS') if qsign['ai_summary'] else None,
    json.dumps(parsed_q),
    qsign['tech_stack'],
    None,
    None,
    uuid.uuid4().hex[:32],
    1,
    now,
    now,
    'https://edms.quanbyai.com',
    'project'
))
new_qsign_id = c.lastrowid
print(f'Created QSign copy → id={new_qsign_id}: Quanby DMS')

# Copy requirements from QSign
c.execute('SELECT * FROM build_requirements WHERE build_id = 12')
reqs_q = c.fetchall()
for r in reqs_q:
    c.execute('''INSERT INTO build_requirements (build_id, category, requirement, priority, compliance_note, created_at, updated_at)
                 VALUES (?,?,?,?,?,?,?)''',
              (new_qsign_id, r['category'], r['requirement'], r['priority'], r['compliance_note'], now, now))
print(f'  Copied {len(reqs_q)} requirements')

conn.commit()
conn.close()

print()
print('Final builds:')
conn2 = sqlite3.connect(DB)
conn2.row_factory = sqlite3.Row
for row in conn2.execute('SELECT id, title, status, product_url FROM builds ORDER BY id'):
    print(f'  [{row["id"]}] {row["title"]} | {row["status"]} | {row["product_url"]}')
conn2.close()
