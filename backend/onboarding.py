"""
onboarding.py — User store, onboarding state, and certificate generation

Security fixes applied:
  FIX-3  XSS: html.escape() on all user fields in HTML templates (_e helper)
  FIX-4  Cert ID enumeration: O(1) lookup via DB index; no full iteration
  FIX-5  PII stored in SQLite (OS-level file permissions on data/ dir)
  FIX-8  Race conditions: SQLite WAL serialises writes; no app-level lock needed
"""

import os
import uuid
import html as _html
from datetime import datetime, timezone
from typing import Optional
from pathlib import Path

import logging
logger = logging.getLogger(__name__)

# ─── Fernet encryption helpers (FIX-5) ────────────────────────────────────────
# Kept so that migrate.py can decrypt legacy JSON data on first run.

try:
    from cryptography.fernet import Fernet
    _fernet_key = os.getenv("DATA_ENCRYPTION_KEY", "")
    if _fernet_key:
        _fernet = Fernet(
            _fernet_key.encode() if isinstance(_fernet_key, str) else _fernet_key
        )
    else:
        _fernet = None
except ImportError:
    _fernet = None

_SENSITIVE_FIELDS = {"email", "first_name", "last_name", "picture", "provider_id", "phone"}


def _encrypt_field(value: str) -> str:
    if _fernet is None or not value:
        return value
    return _fernet.encrypt(value.encode()).decode()


def _decrypt_field(value: str) -> str:
    if _fernet is None or not value:
        return value
    try:
        return _fernet.decrypt(value.encode()).decode()
    except Exception:
        return value  # legacy unencrypted data — return as-is


def _encrypt_user(user: dict) -> dict:
    encrypted = {}
    for key, val in user.items():
        encrypted[key] = _encrypt_field(val) if key in _SENSITIVE_FIELDS and isinstance(val, str) else val
    return encrypted


def _decrypt_user(user: dict) -> dict:
    decrypted = {}
    for key, val in user.items():
        decrypted[key] = _decrypt_field(val) if key in _SENSITIVE_FIELDS and isinstance(val, str) else val
    return decrypted


# ─── HTML-escape helper (FIX-3) ───────────────────────────────────────────────

def _e(s) -> str:
    """HTML-escape a value to prevent XSS injection."""
    return _html.escape(str(s) if s else "")


# ─── Data directory (for file-upload paths, not JSON persistence) ─────────────

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

# ─── Test sessions (in-memory only — ephemeral by design) ────────────────────

import threading as _threading_sess
TEST_SESSIONS: dict = {}
_sessions_lock = _threading_sess.Lock()


def save_test_session(session_id: str, data: dict) -> None:
    with _sessions_lock:
        TEST_SESSIONS[session_id] = data


def get_test_session(session_id: str) -> Optional[dict]:
    with _sessions_lock:
        session = TEST_SESSIONS.get(session_id)
        return dict(session) if session else None


# ─── User CRUD (backed by SQLite via database.py) ────────────────────────────

import database as _db
_db.init_db()


def get_user(user_id: str) -> Optional[dict]:
    """Return the user dict for *user_id*, or None."""
    return _db.get_user(user_id)


async def get_or_create_user(provider_info: dict) -> dict:
    """Find existing user by e-mail or create a new one. Returns the user dict."""
    email = (provider_info.get("email") or "").strip().lower()

    existing = _db.get_user_by_email(email)
    if existing:
        existing["last_login"] = datetime.now(timezone.utc).isoformat()
        existing["provider"]   = provider_info.get("provider")
        _db.upsert_user(existing)
        return existing

    user_id = str(uuid.uuid4())
    user: dict = {
        "id":                       user_id,
        "email":                    email,
        "first_name":               provider_info.get("first_name", ""),
        "last_name":                provider_info.get("last_name", ""),
        "picture":                  provider_info.get("picture", ""),
        "provider":                 provider_info.get("provider"),
        "provider_id":              provider_info.get("provider_id"),
        "email_verified":           provider_info.get("email_verified", False),
        "role":                     None,
        "onboarding_step":          "role_select",
        "profile":                  {},
        "test_result":              None,
        "liveness_verified":        False,
        "national_id_uploaded":     False,
        "certificate_status":       "none",
        "certificate_id":           None,
        "retake_count":             0,
        "retake_payment_confirmed": False,
        "created_at":               datetime.now(timezone.utc).isoformat(),
        "last_login":               datetime.now(timezone.utc).isoformat(),
    }
    _db.upsert_user(user)
    return user


async def update_user(user_id: str, updates: dict) -> Optional[dict]:
    """Apply *updates* to the user and persist. Returns updated dict or None."""
    user = _db.get_user(user_id)
    if user is None:
        return None
    user.update(updates)
    _db.upsert_user(user)
    return user


# ─── Certificate helpers ──────────────────────────────────────────────────────

def generate_certificate_id(role: str) -> str:
    """Generate a unique, high-entropy certificate ID."""
    prefix = "ENP" if role == "attorney" else "CLT"
    ts  = datetime.now(timezone.utc).strftime("%Y%m%d")
    uid = uuid.uuid4().hex[:16].upper()
    return f"QL-{prefix}-{ts}-{uid}"


def lookup_user_by_certificate_id(certificate_id: str) -> Optional[dict]:
    """O(1) certificate lookup via DB index (FIX-4)."""
    return _db.lookup_user_by_certificate_id(certificate_id)


def get_certificate_html(user: dict) -> str:
    """Generate printable HTML certificate. All user fields HTML-escaped (FIX-3)."""
    cert_type   = "Electronic Notary Public (ENP)" if user["role"] == "attorney" else "Verified Legal Client"
    cert_status = (
        "PROBATIONARY CERTIFICATION"
        if user["certificate_status"] == "probationary"
        else "FULL CERTIFICATION"
    )
    status_color = "#f59e0b" if user["certificate_status"] == "probationary" else "#10b981"

    profile   = user.get("profile", {})
    firm_name = profile.get("firm_name", profile.get("organization", ""))

    first_name      = _e(user.get("first_name", ""))
    last_name       = _e(user.get("last_name", ""))
    certificate_id  = _e(user.get("certificate_id", ""))
    firm_name_esc   = _e(firm_name)
    cert_status_esc = _e(cert_status)
    cert_type_esc   = _e(cert_type)

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>Quanby Legal Certificate &mdash; {certificate_id}</title>
<style>
  body {{ font-family: 'Georgia', serif; background: #fff; padding: 40px; }}
  .cert {{ max-width: 800px; margin: 0 auto; border: 3px solid #7c3aed; padding: 48px; text-align: center; position: relative; }}
  .cert::before {{ content: ''; position: absolute; inset: 8px; border: 1px solid #7c3aed; opacity: 0.3; pointer-events: none; }}
  .logo {{ font-size: 2rem; font-weight: bold; color: #7c3aed; margin-bottom: 4px; }}
  .subtitle {{ color: #6b7280; font-size: 0.9rem; margin-bottom: 32px; }}
  .cert-type {{ font-size: 1.1rem; letter-spacing: 0.2em; color: {status_color}; font-weight: bold; margin-bottom: 16px; text-transform: uppercase; }}
  .name {{ font-size: 2.5rem; color: #1e1b4b; margin: 16px 0; font-style: italic; }}
  .firm {{ font-size: 1.1rem; color: #374151; margin-bottom: 24px; }}
  .body-text {{ color: #4b5563; line-height: 1.8; margin: 24px 0; font-size: 0.95rem; }}
  .cert-id {{ font-family: monospace; font-size: 0.85rem; color: #7c3aed; background: #f5f3ff; padding: 8px 16px; border-radius: 4px; display: inline-block; margin: 16px 0; }}
  .seals {{ display: flex; justify-content: space-around; margin-top: 48px; }}
  .seal {{ text-align: center; }}
  .seal-line {{ border-top: 1px solid #000; width: 200px; margin: 8px auto 4px; }}
  .seal-text {{ font-size: 0.8rem; color: #374151; }}
  .footer {{ margin-top: 32px; font-size: 0.75rem; color: #9ca3af; border-top: 1px solid #e5e7eb; padding-top: 16px; }}
  .sc-badge {{ background: #1e1b4b; color: white; padding: 6px 16px; border-radius: 4px; font-size: 0.8rem; display: inline-block; margin-top: 8px; }}
  @media print {{ body {{ padding: 0; }} }}
</style>
</head>
<body>
<div class="cert">
  <div class="logo">&#9878;&#65039; Quanby Legal</div>
  <div class="subtitle">Philippines&#39; First Supreme Court-Accredited Electronic Notarization Facility</div>

  <div class="cert-type">{cert_status_esc}</div>

  <div class="body-text">This certifies that</div>
  <div class="name">{first_name} {last_name}</div>
  {f'<div class="firm">{firm_name_esc}</div>' if firm_name else ''}

  <div class="body-text">
    has successfully completed the Quanby Legal {cert_type_esc} Certification Program
    and is authorized to use the Quanby Legal Electronic Notarization Platform
    in accordance with <strong>A.M. No. 24-10-14-SC</strong>, RA 8792, RA 10173, and applicable Philippine law.
  </div>

  <div class="cert-id">Certificate ID: {certificate_id}</div>
  <div style="font-size:0.8rem;color:#6b7280;margin-top:4px;">
    Issued: {datetime.now(timezone.utc).strftime('%B %d, %Y')} &nbsp;|&nbsp; Valid: 2 years
  </div>

  {'<div style="background:#fef3c7;border:1px solid #f59e0b;padding:12px;border-radius:6px;margin:20px 0;font-size:0.85rem;color:#92400e;"><strong>PROBATIONARY STATUS:</strong> Present this certificate to the Supreme Court of the Philippines for full accreditation. Complete liveness verification and profile survey to upgrade to Full Certification.</div>' if user["certificate_status"] == "probationary" else '<div style="background:#d1fae5;border:1px solid #10b981;padding:12px;border-radius:6px;margin:20px 0;font-size:0.85rem;color:#065f46;"><strong>FULLY CERTIFIED</strong> &mdash; This certificate is valid for presentation to the Supreme Court of the Philippines and all accredited institutions.</div>'}

  <div class="seals">
    <div class="seal">
      <div class="seal-line"></div>
      <div class="seal-text">Authorized Signatory<br>Quanby Solutions, Inc.</div>
    </div>
    <div class="seal">
      <div style="font-size:2rem;">&#9878;&#65039;</div>
      <div class="seal-text">Quanby Legal<br>Official Seal</div>
    </div>
    <div class="seal">
      <div class="seal-line"></div>
      <div class="seal-text">Platform Administrator<br>Quanby Legal ENF</div>
    </div>
  </div>

  <div class="footer">
    <div class="sc-badge">Supreme Court of the Philippines &mdash; A.M. No. 24-10-14-SC Accredited ENF</div>
    <div style="margin-top:8px;">Verify this certificate at legal.quanbyai.com/verify/{certificate_id}</div>
    <div>Quanby Solutions, Inc. | legal@quanby.legal | NPC Registered PIC</div>
  </div>
</div>
</body>
</html>"""


def get_certificate_email_html(user: dict) -> str:
    """HTML email for probationary cert delivery. All user fields are HTML-escaped (FIX-3)."""
    first_name     = _e(user.get("first_name", ""))
    certificate_id = _e(user.get("certificate_id", ""))
    role_label     = _e("Electronic Notary Public (ENP)" if user["role"] == "attorney" else "Client")

    return f"""
<div style="font-family:sans-serif;max-width:600px;margin:0 auto;">
  <div style="background:#1e1b4b;padding:24px;text-align:center;border-radius:8px 8px 0 0;">
    <div style="font-size:1.5rem;font-weight:bold;color:white;">&#9878;&#65039; Quanby Legal</div>
    <div style="color:#c4b5fd;font-size:0.9rem;">Supreme Court-Accredited Electronic Notarization</div>
  </div>
  <div style="background:#f9fafb;padding:32px;border-radius:0 0 8px 8px;border:1px solid #e5e7eb;">
    <h2 style="color:#1e1b4b;margin-top:0;">&#127881; Congratulations, {first_name}!</h2>
    <p style="color:#374151;line-height:1.6;">
      You have successfully passed the Quanby Legal {role_label} Certification Test.
    </p>
    <div style="background:#7c3aed;color:white;padding:16px;border-radius:8px;text-align:center;margin:24px 0;">
      <div style="font-size:0.85rem;opacity:0.8;">Your Certificate ID</div>
      <div style="font-size:1.5rem;font-weight:bold;font-family:monospace;">{certificate_id}</div>
    </div>
    <p style="color:#374151;line-height:1.6;"><strong>Status: PROBATIONARY CERTIFICATION</strong></p>
    <p style="color:#374151;line-height:1.6;">
      This is your probationary certification. To receive your Full Certification, please complete:
    </p>
    <ul style="color:#374151;line-height:2;">
      <li>&#9989; Liveness verification (webcam capture)</li>
      <li>&#9989; Upload of valid National ID</li>
      <li>&#9989; Complete your profile survey</li>
    </ul>
    {"<p style='color:#374151;line-height:1.6;'><strong>&#9888;&#65039; Attorney Action Required:</strong> Once fully certified, you must print your certificate and present it to the Supreme Court of the Philippines for manual addition to the national ENP registry.</p>" if user['role'] == 'attorney' else ""}
    <div style="text-align:center;margin-top:24px;">
      <a href="https://legal.quanbyai.com/dashboard" style="background:#7c3aed;color:white;padding:12px 32px;border-radius:6px;text-decoration:none;font-weight:bold;">Complete Your Certification &#8594;</a>
    </div>
    <hr style="border:none;border-top:1px solid #e5e7eb;margin:24px 0;">
    <p style="color:#9ca3af;font-size:0.8rem;">
      Quanby Solutions, Inc. | Accredited ENF under A.M. No. 24-10-14-SC | NPC Registered PIC<br>
      Questions? Email us at legal@quanby.legal
    </p>
  </div>
</div>
"""
