"""
migrate.py — Migrate Quanby Legal from JSON flat files to SQLite.

Reads data/*.json, initialises data/quanby_legal.db, and inserts all records.
Idempotent: uses INSERT OR REPLACE so it is safe to re-run.
The original JSON files are NOT modified or deleted (kept as backup).

Usage:
    python migrate.py
"""

import os
import sys
import json
import uuid

# Ensure the backend directory is on the path
sys.path.insert(0, os.path.dirname(__file__))

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")


def _load_json(filename: str, default):
    path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(path):
        print(f"  [SKIP] {filename} not found — skipping")
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        print(f"  [ERROR] Could not read {filename}: {exc}")
        return default


# ─── Init DB ──────────────────────────────────────────────────────────────────

import database
database.init_db()

from database import (
    upsert_user,
    save_apt,
    upsert_registry_act,
    upsert_registry_book,
    save_suborg,
)


# ─── Users ────────────────────────────────────────────────────────────────────

def migrate_users() -> int:
    raw = _load_json("users.json", {})
    if not isinstance(raw, dict):
        print("  users.json is not a dict object — skipping")
        return 0

    # Try to import Fernet decryption from onboarding; fall back to identity
    try:
        from onboarding import _decrypt_user
    except Exception:
        def _decrypt_user(u):
            return u

    count = 0
    for user_id, user_data in raw.items():
        try:
            decrypted = _decrypt_user(dict(user_data))
            # Ensure the id field is always present
            if not decrypted.get("id"):
                decrypted["id"] = user_id
            upsert_user(decrypted)
            count += 1
        except Exception as exc:
            print(f"  [WARN] User {user_id[:12]}: {exc}")
    return count


# ─── Appointments ─────────────────────────────────────────────────────────────

def migrate_appointments() -> int:
    raw = _load_json("appointments.json", {})
    if not isinstance(raw, dict):
        print("  appointments.json is not a dict object — skipping")
        return 0

    count = 0
    for apt_id, apt_data in raw.items():
        try:
            apt = dict(apt_data)
            if not apt.get("apt_id"):
                apt["apt_id"] = apt_id
            save_apt(apt)
            count += 1
        except Exception as exc:
            print(f"  [WARN] Appointment {apt_id[:12]}: {exc}")
    return count


# ─── Notarial Registry ────────────────────────────────────────────────────────

def migrate_registry() -> tuple:
    raw = _load_json("notarial_registry.json", {"books": {}, "acts": []})

    books = raw.get("books", {})
    acts  = raw.get("acts", [])

    book_count = 0
    for enp_id, book_data in books.items():
        try:
            book = dict(book_data)
            if not book.get("enp_id"):
                book["enp_id"] = enp_id
            upsert_registry_book(book)
            book_count += 1
        except Exception as exc:
            print(f"  [WARN] Book {enp_id[:12]}: {exc}")

    act_count = 0
    for act_data in acts:
        try:
            act = dict(act_data)
            if not act.get("id"):
                act["id"] = str(uuid.uuid4())
            upsert_registry_act(act)
            act_count += 1
        except Exception as exc:
            print(f"  [WARN] Act {act_data.get('id', '?')[:12]}: {exc}")

    return book_count, act_count


# ─── Sub-orgs ─────────────────────────────────────────────────────────────────

def migrate_suborgs() -> int:
    raw = _load_json("sub_orgs.json", [])
    if not isinstance(raw, list):
        print("  sub_orgs.json is not a list — skipping")
        return 0

    count = 0
    for org_data in raw:
        try:
            org = dict(org_data)
            if not org.get("id"):
                org["id"] = str(uuid.uuid4())
            save_suborg(org)
            count += 1
        except Exception as exc:
            print(f"  [WARN] Sub-org {org_data.get('id', '?')}: {exc}")
    return count


# ─── Main ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Quanby Legal — JSON → SQLite Migration")
    print("=" * 50)
    print(f"Target DB: {database.DB_PATH}\n")

    print("[1/4] Migrating users ...")
    n_users = migrate_users()
    print(f"      ✓ {n_users} users\n")

    print("[2/4] Migrating appointments ...")
    n_apts = migrate_appointments()
    print(f"      ✓ {n_apts} appointments\n")

    print("[3/4] Migrating notarial registry ...")
    n_books, n_acts = migrate_registry()
    print(f"      ✓ {n_books} books, {n_acts} acts\n")

    print("[4/4] Migrating sub-organisations ...")
    n_orgs = migrate_suborgs()
    print(f"      ✓ {n_orgs} sub-orgs\n")

    print("=" * 50)
    print(
        f"Done — {n_users} users · {n_apts} appointments · "
        f"{n_books} books · {n_acts} acts · {n_orgs} sub-orgs"
    )
    print("JSON files in data/ are untouched (kept as backup).")
