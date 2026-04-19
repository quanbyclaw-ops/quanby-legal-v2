"""
Quanby Calendar API — simple SQLite-backed REST API
Runs on port 8090, served at /cal-api/ via nginx proxy
"""
import sqlite3, json, uuid, os
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

DB_PATH = '/var/www/quanbyai-website/calendar.db'
VALID_USERS = ['quanbyai', 'quahnbyai', 'quanby', 'quanbydevelopment', 'admin',
               'michael', 'christian', 'quanbyai']
VALID_PASS  = 'Alyssa7719!!'

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute('''CREATE TABLE IF NOT EXISTS events (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        date TEXT NOT NULL,
        type TEXT DEFAULT 'meeting',
        start TEXT DEFAULT '',
        end TEXT DEFAULT '',
        notes TEXT DEFAULT '',
        created_by TEXT DEFAULT '',
        created_at TEXT DEFAULT '',
        updated_at TEXT DEFAULT ''
    )''')
    conn.commit()
    conn.close()

def auth_check(headers):
    auth = headers.get('X-Cal-User', '').lower().strip()
    pw   = headers.get('X-Cal-Pass', '').strip()
    if auth in [u.lower() for u in VALID_USERS] and pw == VALID_PASS:
        return auth
    return None

def json_response(handler, data, status=200):
    body = json.dumps(data, ensure_ascii=False).encode()
    handler.send_response(status)
    handler.send_header('Content-Type', 'application/json')
    handler.send_header('Content-Length', str(len(body)))
    handler.send_header('Access-Control-Allow-Origin', '*')
    handler.send_header('Access-Control-Allow-Methods', 'GET,POST,PUT,DELETE,OPTIONS')
    handler.send_header('Access-Control-Allow-Headers', 'Content-Type,X-Cal-User,X-Cal-Pass')
    handler.end_headers()
    handler.wfile.write(body)

class CalHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args): pass  # silence logs

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET,POST,PUT,DELETE,OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type,X-Cal-User,X-Cal-Pass')
        self.end_headers()

    def do_GET(self):
        path = urlparse(self.path).path.rstrip('/')
        if path == '/cal-api/events':
            user = auth_check(self.headers)
            if not user:
                json_response(self, {'error': 'Unauthorized'}, 401); return
            conn = get_db()
            rows = conn.execute('SELECT * FROM events ORDER BY date, start').fetchall()
            conn.close()
            json_response(self, [dict(r) for r in rows])
        elif path == '/cal-api/health':
            json_response(self, {'status': 'ok'})
        else:
            json_response(self, {'error': 'Not found'}, 404)

    def do_POST(self):
        path = urlparse(self.path).path.rstrip('/')
        user = auth_check(self.headers)
        if not user:
            json_response(self, {'error': 'Unauthorized'}, 401); return
        length = int(self.headers.get('Content-Length', 0))
        body = json.loads(self.rfile.read(length) or '{}')
        now = datetime.utcnow().isoformat()

        if path == '/cal-api/events':
            ev_id = body.get('id') or str(uuid.uuid4())[:12]
            conn = get_db()
            conn.execute('''INSERT OR REPLACE INTO events
                (id,title,date,type,start,end,notes,created_by,created_at,updated_at)
                VALUES (?,?,?,?,?,?,?,?,?,?)''', (
                ev_id,
                body.get('title',''),
                body.get('date',''),
                body.get('type','meeting'),
                body.get('start',''),
                body.get('end',''),
                body.get('notes',''),
                user, now, now
            ))
            conn.commit()
            conn.close()
            json_response(self, {'id': ev_id, 'success': True})
        else:
            json_response(self, {'error': 'Not found'}, 404)

    def do_DELETE(self):
        path = urlparse(self.path).path.rstrip('/')
        user = auth_check(self.headers)
        if not user:
            json_response(self, {'error': 'Unauthorized'}, 401); return
        # DELETE /cal-api/events/{id}
        parts = path.split('/')
        if len(parts) >= 4 and parts[2] == 'events':
            ev_id = parts[3]
            conn = get_db()
            conn.execute('DELETE FROM events WHERE id=?', (ev_id,))
            conn.commit()
            conn.close()
            json_response(self, {'success': True})
        else:
            json_response(self, {'error': 'Not found'}, 404)

    def do_PUT(self):
        path = urlparse(self.path).path.rstrip('/')
        user = auth_check(self.headers)
        if not user:
            json_response(self, {'error': 'Unauthorized'}, 401); return
        parts = path.split('/')
        if len(parts) >= 4 and parts[2] == 'events':
            ev_id = parts[3]
            length = int(self.headers.get('Content-Length', 0))
            body = json.loads(self.rfile.read(length) or '{}')
            now = datetime.utcnow().isoformat()
            conn = get_db()
            conn.execute('''UPDATE events SET title=?,date=?,type=?,start=?,end=?,notes=?,updated_at=?
                WHERE id=?''', (
                body.get('title',''), body.get('date',''), body.get('type','meeting'),
                body.get('start',''), body.get('end',''), body.get('notes',''),
                now, ev_id
            ))
            conn.commit()
            conn.close()
            json_response(self, {'success': True})
        else:
            json_response(self, {'error': 'Not found'}, 404)

if __name__ == '__main__':
    init_db()
    server = HTTPServer(('127.0.0.1', 8090), CalHandler)
    print('Calendar API running on :8090')
    server.serve_forever()
