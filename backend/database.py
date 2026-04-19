"""
database.py — SQLite persistence layer for Quanby Legal backend.

Replaces JSON flat-file storage with WAL-mode SQLite.
Design:
  - threading.local() per-thread connections (safe for FastAPI + background threads)
  - WAL journal mode: concurrent reads, serialised writes
  - Appointments and sub-orgs stored as JSON blobs + indexed helper columns
    (they have many dynamic/ad-hoc fields; blobs avoid schema churn)
  - Users and registry stored with proper column schema for efficient queries
"""

import os
import json
import sqlite3
import threading
from contextlib import contextmanager
from typing import Optional

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "quanby_legal.db")

_local = threading.local()


# ─── Connection management ────────────────────────────────────────────────────

def _get_conn() -> sqlite3.Connection:
    """Return (creating if needed) a per-thread SQLite connection."""
    conn = getattr(_local, "conn", None)
    if conn is None:
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA cache_size=-8000")   # 8 MB page cache
        _local.conn = conn
    return conn


@contextmanager
def get_db():
    """Context manager yielding a connection; commits on exit, rolls back on error."""
    conn = _get_conn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise


# ─── Schema init ──────────────────────────────────────────────────────────────

def init_db() -> None:
    """Create all tables. Safe to call multiple times (CREATE IF NOT EXISTS)."""
    conn = _get_conn()
    conn.executescript("""
        -- Users: full column schema for efficient admin queries and cert lookups
        CREATE TABLE IF NOT EXISTS users (
            id                      TEXT PRIMARY KEY,
            email                   TEXT NOT NULL,
            first_name              TEXT DEFAULT '',
            last_name               TEXT DEFAULT '',
            picture                 TEXT DEFAULT '',
            provider                TEXT,
            provider_id             TEXT,
            email_verified          INTEGER DEFAULT 0,
            role                    TEXT,
            onboarding_step         TEXT DEFAULT 'role_select',
            profile                 TEXT DEFAULT '{}',
            test_result             TEXT,
            liveness_verified       INTEGER DEFAULT 0,
            national_id_uploaded    INTEGER DEFAULT 0,
            certificate_status      TEXT DEFAULT 'none',
            certificate_id          TEXT,
            retake_count            INTEGER DEFAULT 0,
            retake_payment_confirmed INTEGER DEFAULT 0,
            created_at              TEXT,
            last_login              TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_users_email   ON users(email);
        CREATE INDEX IF NOT EXISTS idx_users_cert_id ON users(certificate_id);
        CREATE INDEX IF NOT EXISTS idx_users_role    ON users(role);

        -- Appointments: JSON blob + indexed columns for fast filtering
        CREATE TABLE IF NOT EXISTS appointments (
            apt_id          TEXT PRIMARY KEY,
            client_id       TEXT,
            enp_id          TEXT,
            status          TEXT DEFAULT 'PENDING',
            session_status  TEXT,
            created_at      TEXT,
            data            TEXT NOT NULL DEFAULT '{}'
        );
        CREATE INDEX IF NOT EXISTS idx_apts_client  ON appointments(client_id);
        CREATE INDEX IF NOT EXISTS idx_apts_enp     ON appointments(enp_id);
        CREATE INDEX IF NOT EXISTS idx_apts_status  ON appointments(status);

        -- Registry acts: proper columns + JSON blob for extra/nested fields
        CREATE TABLE IF NOT EXISTS notarial_registry_acts (
            id                      TEXT PRIMARY KEY,
            enp_id                  TEXT NOT NULL,
            apt_id                  TEXT,
            doconchain_project_uuid TEXT,
            act_type                TEXT,
            executed_at             TEXT,
            sc_synced               INTEGER DEFAULT 0,
            created_at              TEXT,
            data                    TEXT NOT NULL DEFAULT '{}'
        );
        CREATE INDEX IF NOT EXISTS idx_acts_enp    ON notarial_registry_acts(enp_id);
        CREATE INDEX IF NOT EXISTS idx_acts_dc_uuid ON notarial_registry_acts(doconchain_project_uuid);

        -- Registry books: one row per ENP (INSERT OR IGNORE = idempotent)
        CREATE TABLE IF NOT EXISTS notarial_registry_books (
            enp_id          TEXT PRIMARY KEY,
            enp_name        TEXT,
            roll_no         TEXT,
            commission_no   TEXT,
            created_at      TEXT
        );

        -- Sub-orgs: JSON blob + indexed owner for fast list
        CREATE TABLE IF NOT EXISTS sub_orgs (
            id          TEXT PRIMARY KEY,
            owner_id    TEXT,
            name        TEXT,
            created_at  TEXT,
            data        TEXT NOT NULL DEFAULT '{}'
        );
        CREATE INDEX IF NOT EXISTS idx_suborgs_owner ON sub_orgs(owner_id);
    """)
    conn.commit()


# ─── JSON helpers ──────────────────────────────────────────────────────────────

def _j(value) -> str:
    """Serialize a value to a compact JSON string."""
    return json.dumps(value, default=str, ensure_ascii=False)


def _p(value: Optional[str]):
    """Parse a JSON string; return None if the value is None."""
    if value is None:
        return None
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        return value


# ─── User CRUD ─────────────────────────────────────────────────────────────────

def _row_to_user(row) -> dict:
    d = dict(row)
    d["profile"]    = _p(d.get("profile")) or {}
    d["test_result"] = _p(d.get("test_result"))
    # SQLite stores booleans as 0/1
    for field in ("email_verified", "liveness_verified", "national_id_uploaded",
                  "retake_payment_confirmed"):
        d[field] = bool(d.get(field))
    return d


def get_user(user_id: str) -> Optional[dict]:
    row = _get_conn().execute(
        "SELECT * FROM users WHERE id = ?", (user_id,)
    ).fetchone()
    return _row_to_user(row) if row else None


def get_user_by_email(email: str) -> Optional[dict]:
    row = _get_conn().execute(
        "SELECT * FROM users WHERE LOWER(email) = LOWER(?)", (email,)
    ).fetchone()
    return _row_to_user(row) if row else None


def upsert_user(data: dict) -> None:
    conn = _get_conn()
    conn.execute(
        """
        INSERT OR REPLACE INTO users (
            id, email, first_name, last_name, picture, provider, provider_id,
            email_verified, role, onboarding_step, profile, test_result,
            liveness_verified, national_id_uploaded, certificate_status,
            certificate_id, retake_count, retake_payment_confirmed,
            created_at, last_login
        ) VALUES (
            :id, :email, :first_name, :last_name, :picture, :provider, :provider_id,
            :email_verified, :role, :onboarding_step, :profile, :test_result,
            :liveness_verified, :national_id_uploaded, :certificate_status,
            :certificate_id, :retake_count, :retake_payment_confirmed,
            :created_at, :last_login
        )
        """,
        {
            "id":                       data["id"],
            "email":                    data.get("email", ""),
            "first_name":               data.get("first_name", "") or "",
            "last_name":                data.get("last_name", "") or "",
            "picture":                  data.get("picture", "") or "",
            "provider":                 data.get("provider"),
            "provider_id":              data.get("provider_id"),
            "email_verified":           int(bool(data.get("email_verified"))),
            "role":                     data.get("role"),
            "onboarding_step":          data.get("onboarding_step", "role_select"),
            "profile":                  _j(data.get("profile") or {}),
            "test_result":              (_j(data["test_result"])
                                         if data.get("test_result") is not None
                                         else None),
            "liveness_verified":        int(bool(data.get("liveness_verified"))),
            "national_id_uploaded":     int(bool(data.get("national_id_uploaded"))),
            "certificate_status":       data.get("certificate_status", "none"),
            "certificate_id":           data.get("certificate_id"),
            "retake_count":             data.get("retake_count", 0),
            "retake_payment_confirmed": int(bool(data.get("retake_payment_confirmed"))),
            "created_at":               data.get("created_at"),
            "last_login":               data.get("last_login"),
        },
    )
    conn.commit()


def list_users() -> list:
    rows = _get_conn().execute(
        "SELECT * FROM users ORDER BY created_at DESC"
    ).fetchall()
    return [_row_to_user(r) for r in rows]


def delete_user(user_id: str) -> None:
    conn = _get_conn()
    conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()


def lookup_user_by_certificate_id(certificate_id: str) -> Optional[dict]:
    row = _get_conn().execute(
        "SELECT * FROM users WHERE certificate_id = ?", (certificate_id,)
    ).fetchone()
    return _row_to_user(row) if row else None


# ─── Appointment CRUD ──────────────────────────────────────────────────────────

def get_apt(apt_id: str) -> Optional[dict]:
    row = _get_conn().execute(
        "SELECT data FROM appointments WHERE apt_id = ?", (apt_id,)
    ).fetchone()
    if row is None:
        return None
    return _p(row["data"]) or {}


def save_apt(data: dict) -> None:
    """Insert or replace an appointment (full dict stored as JSON)."""
    conn = _get_conn()
    conn.execute(
        """
        INSERT OR REPLACE INTO appointments
            (apt_id, client_id, enp_id, status, session_status, created_at, data)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            data["apt_id"],
            data.get("client_id"),
            data.get("enp_id"),
            data.get("status", "PENDING"),
            data.get("session_status"),
            data.get("created_at"),
            _j(data),
        ),
    )
    conn.commit()


def list_apts(filters: Optional[dict] = None) -> list:
    """
    Return all appointments as dicts.
    Optional filters dict keys: client_id, enp_id, status, session_status.
    """
    conn = _get_conn()
    if not filters:
        rows = conn.execute("SELECT data FROM appointments").fetchall()
    else:
        clauses, params = [], []
        for col in ("client_id", "enp_id", "status", "session_status"):
            if col in filters:
                clauses.append(f"{col} = ?")
                params.append(filters[col])
        where = " AND ".join(clauses) if clauses else "1"
        rows = conn.execute(
            f"SELECT data FROM appointments WHERE {where}", params
        ).fetchall()
    return [_p(r["data"]) or {} for r in rows]


def delete_apt(apt_id: str) -> None:
    conn = _get_conn()
    conn.execute("DELETE FROM appointments WHERE apt_id = ?", (apt_id,))
    conn.commit()


# ─── Registry CRUD ─────────────────────────────────────────────────────────────

def get_registry() -> dict:
    """Return the full registry in the legacy format: {books: {...}, acts: [...]}."""
    conn = _get_conn()
    act_rows  = conn.execute("SELECT data FROM notarial_registry_acts").fetchall()
    book_rows = conn.execute("SELECT * FROM notarial_registry_books").fetchall()
    acts  = [_p(r["data"]) or {} for r in act_rows]
    books = {r["enp_id"]: dict(r) for r in book_rows}
    return {"books": books, "acts": acts}


def upsert_registry_act(act: dict) -> None:
    """Insert or replace a registry act."""
    conn = _get_conn()
    conn.execute(
        """
        INSERT OR REPLACE INTO notarial_registry_acts
            (id, enp_id, apt_id, doconchain_project_uuid,
             act_type, executed_at, sc_synced, created_at, data)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            act["id"],
            act.get("enp_id"),
            act.get("apt_id"),
            act.get("doconchain_project_uuid"),
            act.get("act_type"),
            act.get("executed_at"),
            int(bool(act.get("sc_synced"))),
            act.get("created_at"),
            _j(act),
        ),
    )
    conn.commit()


def upsert_registry_book(book: dict) -> None:
    """Insert a registry book entry if one doesn't already exist for this ENP."""
    conn = _get_conn()
    conn.execute(
        """
        INSERT OR IGNORE INTO notarial_registry_books
            (enp_id, enp_name, roll_no, commission_no, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            book["enp_id"],
            book.get("enp_name"),
            book.get("roll_no"),
            book.get("commission_no"),
            book.get("created_at"),
        ),
    )
    conn.commit()


def list_acts(enp_id: Optional[str] = None) -> list:
    conn = _get_conn()
    if enp_id:
        rows = conn.execute(
            "SELECT data FROM notarial_registry_acts WHERE enp_id = ?", (enp_id,)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT data FROM notarial_registry_acts"
        ).fetchall()
    return [_p(r["data"]) or {} for r in rows]


def act_exists(enp_id: str, dc_uuid: str) -> bool:
    row = _get_conn().execute(
        """
        SELECT 1 FROM notarial_registry_acts
        WHERE enp_id = ? AND doconchain_project_uuid = ?
        """,
        (enp_id, dc_uuid),
    ).fetchone()
    return row is not None


def get_act_by_id(act_id: str, enp_id: Optional[str] = None) -> Optional[dict]:
    conn = _get_conn()
    if enp_id:
        row = conn.execute(
            "SELECT data FROM notarial_registry_acts WHERE id = ? AND enp_id = ?",
            (act_id, enp_id),
        ).fetchone()
    else:
        row = conn.execute(
            "SELECT data FROM notarial_registry_acts WHERE id = ?", (act_id,)
        ).fetchone()
    return _p(row["data"]) if row else None


# ─── Sub-org CRUD ──────────────────────────────────────────────────────────────

def get_suborg(org_id: str) -> Optional[dict]:
    row = _get_conn().execute(
        "SELECT data FROM sub_orgs WHERE id = ?", (org_id,)
    ).fetchone()
    return _p(row["data"]) if row else None


def save_suborg(data: dict) -> None:
    conn = _get_conn()
    conn.execute(
        """
        INSERT OR REPLACE INTO sub_orgs (id, owner_id, name, created_at, data)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            data["id"],
            data.get("owner_id"),
            data.get("name"),
            data.get("created_at"),
            _j(data),
        ),
    )
    conn.commit()


def list_suborgs() -> list:
    rows = _get_conn().execute("SELECT data FROM sub_orgs").fetchall()
    return [_p(r["data"]) or {} for r in rows]


def delete_suborg(org_id: str) -> None:
    conn = _get_conn()
    conn.execute("DELETE FROM sub_orgs WHERE id = ?", (org_id,))
    conn.commit()
