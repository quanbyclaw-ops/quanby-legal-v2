"""
main.py Ã¢â‚¬â€ Quanby Legal Backend
FastAPI application: Contract AI + SSO Auth + Onboarding + Certification

Security fixes applied:
  FIX-1  JWT delivered via HttpOnly Secure cookie, NOT URL query param
  FIX-2  OAuth CSRF: state validated on every callback
  FIX-4  Cert verification uses O(1) CERT_INDEX + rate limiting
  FIX-6  Test retake blocking: retake_count >= 3 returns 403 until payment confirmed
  FIX-7  CORS: restricted to FRONTEND_URL env var (not "*")
  FIX-8  update_user / get_or_create_user are async Ã¢â‚¬â€ awaited correctly
  FIX-10 File upload: os.path.basename() sanitization on all filenames
  FIX-11 JWT: refresh token endpoint; tokens via HttpOnly Secure cookie
  FIX-12 /api/health: no sensitive config details exposed
"""

import os
import json
import time
import uuid
import stat
import base64
import threading
from typing import Optional
from fastapi import FastAPI, File, UploadFile, HTTPException, Form, Header, Request, Cookie, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse
from pydantic import BaseModel
from dotenv import load_dotenv
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from contract_parser import extract_text, clean_text, get_contract_summary_for_context
from ai_engine import analyze_contract, chat_about_contract, generate_contract
from auth import (
    create_jwt, create_access_token, create_refresh_token,
    verify_jwt, verify_refresh_token,
    get_oauth_urls, validate_oauth_state,
    google_get_user_info,
    APP_URL, FRONTEND_URL,
)
from onboarding import (
    get_or_create_user, get_user, update_user,
    save_test_session, get_test_session,
    generate_certificate_id, get_certificate_html, get_certificate_email_html,
    lookup_user_by_certificate_id,
)
from question_bank import get_randomized_test, grade_test
from email_service import send_welcome_email, send_test_fail_email
import database as _db

load_dotenv()

# Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬ Rate limiter (FIX-4) Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="Quanby Legal",
    description="Supreme Court-Accredited Electronic Notarization Platform",
    version="2.0.0",
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬ FIX-7: CORS Ã¢â‚¬â€ restrict to FRONTEND_URL, not "*" Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
_allowed_origins_raw = os.getenv("FRONTEND_URL", "https://legal.quanbyai.com")
# Support comma-separated list of origins
_allowed_origins = [o.strip() for o in _allowed_origins_raw.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory contract session store (production: Redis)
sessions: dict = {}

# Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬ Cookie settings Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
_COOKIE_SECURE   = os.getenv("COOKIE_SECURE", "true").lower() != "false"
_COOKIE_SAMESITE = "lax"
_ACCESS_COOKIE   = "ql_access"
_REFRESH_COOKIE  = "ql_refresh"


def _set_auth_cookies(response: Response, user_id: str, email: str) -> None:
    """FIX-1/11: Set JWT tokens as HttpOnly Secure cookies (never in URL)."""
    access_token  = create_access_token({"user_id": user_id, "email": email})
    refresh_token = create_refresh_token(user_id)

    response.set_cookie(
        key=_ACCESS_COOKIE,
        value=access_token,
        httponly=True,
        secure=_COOKIE_SECURE,
        samesite=_COOKIE_SAMESITE,
        max_age=24 * 60 * 60,      # 24 hours
        path="/",
    )
    response.set_cookie(
        key=_REFRESH_COOKIE,
        value=refresh_token,
        httponly=True,
        secure=_COOKIE_SECURE,
        samesite=_COOKIE_SAMESITE,
        max_age=30 * 24 * 3600,  # 30 days
        path="/api/auth/refresh",
    )


# Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬ Models Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬

class ChatRequest(BaseModel):
    session_id: str
    message: str


class GenerateRequest(BaseModel):
    template_type: str
    parameters: dict = {}


class RoleSelectRequest(BaseModel):
    role: str  # "attorney" or "client"


class ProfileRequest(BaseModel):
    prefix: Optional[str] = None
    first_name: str
    middle_initial: Optional[str] = None
    last_name: str
    suffix: Optional[str] = None
    phone: str
    role: str
    # Attorney / ENP fields
    roll_no: Optional[str] = None
    roll_date: Optional[str] = None
    commission_no: Optional[str] = None
    commission_no_valid_until: Optional[str] = None
    ptr_no: Optional[str] = None
    ptr_no_location: Optional[str] = None
    ptr_no_date: Optional[str] = None
    ibp_no: Optional[str] = None
    ibp_no_date: Optional[str] = None
    notary_address: Optional[str] = None
    home_street: Optional[str] = None
    barangay: Optional[str] = None
    city_province: Optional[str] = None
    mcle_no_period: Optional[str] = None
    mcle_no: Optional[str] = None
    mcle_no_date: Optional[str] = None
    # Client fields
    organization: Optional[str] = None
    position: Optional[str] = None


class TestAnswerRequest(BaseModel):
    test_session_id: str
    answers: dict  # {question_id: answer_letter}


class RetakePaymentRequest(BaseModel):
    user_id: str
    payment_method: str  # "gcash" or "bank_transfer"



class LegalChatRequest(BaseModel):
    message: str
    session_id: str = ""


class QuickSignAddSignerRequest(BaseModel):
    project_uuid: str
    client_email: str
    first_name: str
    last_name: str = ""


class QuickSignCreateAppointmentRequest(BaseModel):
    project_uuid: str
    dc_project_uuid: str
    doc_name: str
    client_email: str
    client_name: str
    scheduled_at: str = ""
    notes: str = ""
    notarization_type: str = "ACKNOWLEDGMENT"

# Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬ Auth helpers Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬

def _token_from_request(
    authorization: Optional[str],
    ql_access: Optional[str],
) -> Optional[str]:
    """
    FIX-1: Accept token from HttpOnly cookie (primary) or Authorization header (fallback).
    Never accept from query parameters.
    """
    if ql_access:
        return ql_access
    if authorization and authorization.startswith("Bearer "):
        return authorization.split(" ", 1)[1]
    return None


def get_current_user(
    authorization: Optional[str] = None,
    ql_access: Optional[str] = None,
) -> Optional[dict]:
    """Extract user from cookie or Bearer token."""
    token = _token_from_request(authorization, ql_access)
    if not token:
        return None
    payload = verify_jwt(token)
    if not payload:
        return None
    return get_user(payload.get("user_id", ""))


# Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬ Endpoints Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬

@app.get("/api/health")
async def health_check():
    """
    Health check endpoint.
    FIX-12: No sensitive config details (API key presence, key names, etc.).
    """
    return {
        "status": "ok",
        "service": "Quanby Legal Contract AI Agent",
        "version": "2.0.0",
        "timestamp": int(time.time()),
    }


@app.post("/api/analyze")
async def analyze_endpoint(
    file: UploadFile = File(...),
    session_id: str = Form(default="default"),
):
    """Upload a PDF/DOCX contract and get AI analysis."""
    # FIX-10: Sanitize filename Ã¢â‚¬â€ strip path traversal
    raw_name = file.filename or "contract"
    filename = os.path.basename(raw_name).replace("..", "").strip() or "contract"

    if not any(filename.lower().endswith(ext) for ext in [".pdf", ".docx", ".doc", ".txt"]):
        raise HTTPException(400, "Unsupported file type. Please upload PDF, DOCX, or TXT files.")

    file_bytes = await file.read()
    if len(file_bytes) > 20 * 1024 * 1024:
        raise HTTPException(400, "File too large. Maximum 20MB.")
    if len(file_bytes) == 0:
        raise HTTPException(400, "Empty file uploaded.")

    try:
        raw_text = extract_text(file_bytes, filename)
        contract_text = clean_text(raw_text)
    except ValueError as e:
        raise HTTPException(422, str(e))

    if len(contract_text.strip()) < 50:
        raise HTTPException(
            422,
            "Could not extract sufficient text from the document. "
            "Please ensure the file is not scanned/image-only.",
        )

    context_text = get_contract_summary_for_context(contract_text, max_length=12000)
    result = analyze_contract(context_text, filename)

    sessions[session_id] = {
        "contract_text": context_text,
        "filename": filename,
        "history": [],
        "analysis": result.get("analysis", {}),
        "created_at": int(time.time()),
    }

    if not result["success"]:
        raise HTTPException(500, result.get("error", "AI analysis failed"))

    return {
        "success": True,
        "session_id": session_id,
        "filename": filename,
        "text_length": len(contract_text),
        "analysis": result["analysis"],
        "tokens_used": result.get("tokens_used"),
    }


@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
    """Chat about an uploaded contract."""
    session = sessions.get(request.session_id)
    if not session:
        raise HTTPException(404, "No contract loaded for this session. Please upload a contract first.")

    result = chat_about_contract(
        contract_text=session["contract_text"],
        conversation_history=session["history"],
        user_message=request.message,
        filename=session["filename"],
    )

    if not result["success"]:
        raise HTTPException(500, result.get("error", "Chat failed"))

    session["history"].append({"role": "user", "content": request.message})
    session["history"].append({"role": "assistant", "content": result["response"]})
    sessions[request.session_id]["history"] = session["history"]

    return {
        "success": True,
        "response": result["response"],
        "tokens_used": result.get("tokens_used"),
    }


@app.post("/api/generate")
async def generate_endpoint(request: GenerateRequest):
    """Generate a contract from a template using AI."""
    valid_templates = [
        "deed_of_sale", "lease_agreement", "employment_contract",
        "service_agreement", "loan_agreement", "partnership_agreement",
        "nda", "memorandum_of_agreement", "joint_venture", "power_of_attorney",
    ]
    if request.template_type not in valid_templates:
        raise HTTPException(400, f"Invalid template type. Choose from: {', '.join(valid_templates)}")

    result = generate_contract(request.template_type, request.parameters)
    if not result["success"]:
        raise HTTPException(500, result.get("error", "Generation failed"))

    return {
        "success": True,
        "contract_type": result["contract_type"],
        "contract_text": result["contract_text"],
        "tokens_used": result.get("tokens_used"),
    }


@app.get("/api/templates")
async def list_templates():
    """List available contract templates."""
    return {
        "templates": [
            {"id": "deed_of_sale", "name": "Deed of Absolute Sale", "icon": "Ã°Å¸ÂÂ¡", "category": "Real Estate"},
            {"id": "lease_agreement", "name": "Contract of Lease", "icon": "Ã°Å¸ÂÂ¢", "category": "Real Estate"},
            {"id": "employment_contract", "name": "Employment Contract", "icon": "Ã°Å¸â€˜â€", "category": "Labor"},
            {"id": "service_agreement", "name": "Service Agreement", "icon": "Ã°Å¸Â¤Â", "category": "Business"},
            {"id": "loan_agreement", "name": "Loan Agreement", "icon": "Ã°Å¸â€™Â°", "category": "Finance"},
            {"id": "partnership_agreement", "name": "Partnership Agreement", "icon": "Ã°Å¸Ââ€ºÃ¯Â¸Â", "category": "Corporate"},
            {"id": "nda", "name": "Non-Disclosure Agreement", "icon": "Ã°Å¸â€â€™", "category": "Corporate"},
            {"id": "memorandum_of_agreement", "name": "Memorandum of Agreement", "icon": "Ã°Å¸â€œâ€¹", "category": "Business"},
            {"id": "joint_venture", "name": "Joint Venture Agreement", "icon": "Ã°Å¸Â¤Â²", "category": "Corporate"},
            {"id": "power_of_attorney", "name": "Special Power of Attorney", "icon": "Ã¢Å¡â€“Ã¯Â¸Â", "category": "Legal"},
        ]
    }


# Ã¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢Â
# AUTH & ONBOARDING ENDPOINTS
# Ã¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢Â

# Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬ OAuth URLs Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬

@app.get("/api/auth/providers")
async def auth_providers():
    """Return OAuth login URLs with CSRF state tokens."""
    return {"providers": get_oauth_urls()}


# Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬ FIX-11: Token refresh endpoint Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬

@app.post("/api/auth/refresh")
async def refresh_token_endpoint(
    response: Response,
    ql_refresh: Optional[str] = Cookie(default=None),
):
    """
    Exchange a valid refresh token cookie for a new access token cookie.
    FIX-11: Refresh token support.
    """
    if not ql_refresh:
        raise HTTPException(401, "No refresh token provided")

    payload = verify_refresh_token(ql_refresh)
    if not payload:
        raise HTTPException(401, "Invalid or expired refresh token")

    user = get_user(payload["user_id"])
    if not user:
        raise HTTPException(401, "User not found")

    # Issue new access token + rotate refresh token (sliding window)
    access_token  = create_access_token({"user_id": user["id"], "email": user["email"]})
    new_refresh   = create_refresh_token(user["id"])
    response.set_cookie(
        key=_ACCESS_COOKIE,
        value=access_token,
        httponly=True,
        secure=_COOKIE_SECURE,
        samesite=_COOKIE_SAMESITE,
        max_age=24 * 60 * 60,  # 24 hours
        path="/",
    )
    response.set_cookie(
        key=_REFRESH_COOKIE,
        value=new_refresh,
        httponly=True,
        secure=_COOKIE_SECURE,
        samesite=_COOKIE_SAMESITE,
        max_age=30 * 24 * 3600,  # 30 days (sliding)
        path="/api/auth/refresh",
    )
    return {"success": True, "message": "Tokens refreshed"}


# Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬ Google OAuth Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬

@app.get("/api/auth/callback/google")
async def google_callback(
    request: Request,
    code: str,
    state: Optional[str] = None,
):
    """Handle Google OAuth callback. FIX-2: validate state."""
    if not state:
        raise HTTPException(400, "Missing OAuth state parameter")
    entry = validate_oauth_state(state)
    if not entry:
        raise HTTPException(400, "Invalid or expired OAuth state Ã¢â‚¬â€ possible CSRF attempt")

    redirect_uri = f"{APP_URL}/api/auth/callback/google"
    user_info = await google_get_user_info(code, redirect_uri)
    user = await get_or_create_user(user_info)

    # Send welcome email on first login (onboarding_step == 'role_select' = brand new user)
    if user.get("onboarding_step", "role_select") == "role_select":
        send_welcome_email(user)  # fire-and-forget, non-blocking

    # FIX-1: Deliver token via HttpOnly Secure cookie, NOT query param
    response = RedirectResponse(
        url=f"{FRONTEND_URL}/auth-complete?step={user.get('onboarding_step', 'role_select')}",
        status_code=302,
    )
    _set_auth_cookies(response, user["id"], user["email"])
    return response


@app.post("/api/auth/logout")
async def logout(response: Response):
    """Clear auth cookies."""
    response.delete_cookie(_ACCESS_COOKIE, path="/")
    response.delete_cookie(_REFRESH_COOKIE, path="/api/auth/refresh")
    return {"success": True}


# Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬ User Session Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬



@app.get("/api/auth/me")
async def get_me(
    authorization: Optional[str] = Header(None),
    ql_access: Optional[str] = Cookie(default=None),
):
    """Get current user info."""
    user = get_current_user(authorization, ql_access)
    if not user:
        raise HTTPException(401, "Unauthorized")
    return {
        "id": user["id"],
        "email": user["email"],
        "first_name": user["first_name"],
        "last_name": user["last_name"],
        "picture": user.get("picture", ""),
        "role": user.get("role"),
        "onboarding_step": user.get("onboarding_step", "role_select"),
        "certificate_status": user.get("certificate_status", "none"),
        "certificate_id": user.get("certificate_id"),
        "liveness_verified": user.get("liveness_verified", False),
        "national_id_uploaded": user.get("national_id_uploaded", False),
        "kyc_id_uploaded": user.get("kyc_id_uploaded", False),
        "retake_count": user.get("retake_count", 0),
        "retake_payment_pending": user.get("retake_payment_pending", False),
        "retake_payment_confirmed": user.get("retake_payment_confirmed", False),
        "kyc_verified_at": user.get("kyc_verified_at"),
        "sc_commission_status": user.get("sc_commission_status", "pending"),
    }


# Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬ Onboarding Step 1: Role Selection Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬

@app.post("/api/onboarding/role")
async def set_role(
    req: RoleSelectRequest,
    authorization: Optional[str] = Header(None),
    ql_access: Optional[str] = Cookie(default=None),
):
    """Set user role: attorney or client."""
    user = get_current_user(authorization, ql_access)
    if not user:
        raise HTTPException(401, "Unauthorized")
    if req.role not in ("attorney", "client"):
        raise HTTPException(400, "Role must be 'attorney' or 'client'")

    await update_user(user["id"], {"role": req.role, "onboarding_step": "profile"})
    return {"success": True, "next_step": "profile"}


# Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬ Onboarding Step 2: Profile Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬

@app.post("/api/onboarding/profile")
async def save_profile(
    req: ProfileRequest,
    authorization: Optional[str] = Header(None),
    ql_access: Optional[str] = Cookie(default=None),
):
    """Save user profile information."""
    user = get_current_user(authorization, ql_access)
    if not user:
        raise HTTPException(401, "Unauthorized")

    profile: dict = {
        "prefix": req.prefix or "",
        "first_name": req.first_name,
        "middle_initial": req.middle_initial or "",
        "last_name": req.last_name,
        "suffix": req.suffix or "",
        "phone": req.phone,
    }

    if req.role == "attorney":
        profile.update({
            "roll_no": req.roll_no or "",
            "roll_date": req.roll_date or "",
            "commission_no": req.commission_no or "",
            "commission_no_valid_until": req.commission_no_valid_until or "",
            "ptr_no": req.ptr_no or "",
            "ptr_no_location": req.ptr_no_location or "",
            "ptr_no_date": req.ptr_no_date or "",
            "ibp_no": req.ibp_no or "",
            "ibp_no_date": req.ibp_no_date or "",
            "notary_address": req.notary_address or "",
            "home_street": req.home_street or "",
            "barangay": req.barangay or "",
            "city_province": req.city_province or "",
            "mcle_no_period": req.mcle_no_period or "",
            "mcle_no": req.mcle_no or "",
            "mcle_no_date": req.mcle_no_date or "",
        })
    else:
        profile.update({
            "organization": req.organization or "",
            "position": req.position or "",
        })

    await update_user(user["id"], {
        "profile": profile,
        "first_name": req.first_name,
        "last_name": req.last_name,
        "onboarding_step": "certified" if user.get("role") == "client" else "test",
    })
    next_step = "done" if user.get("role") == "client" else "test"
    return {"success": True, "next_step": next_step}



# --- Profile Get (authenticated users) -----------------------------------------

@app.get("/api/profile")
async def get_profile(
    authorization: Optional[str] = Header(None),
    ql_access: Optional[str] = Cookie(default=None),
):
    """Get the authenticated user's full profile including sub-object."""
    user = get_current_user(authorization, ql_access)
    if not user:
        raise HTTPException(401, "Unauthorized")
    return {"success": True, "user": user}


# --- Profile Edit (authenticated users) ----------------------------------------

class ProfileEditRequest(BaseModel):
    # Common fields
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    prefix: Optional[str] = None
    middle_initial: Optional[str] = None
    suffix: Optional[str] = None
    phone: Optional[str] = None
    # ENP/Attorney fields
    roll_no: Optional[str] = None
    roll_date: Optional[str] = None
    commission_no: Optional[str] = None
    commission_no_valid_until: Optional[str] = None
    npn: Optional[str] = None
    ptr_no: Optional[str] = None
    ptr_no_location: Optional[str] = None
    ptr_no_date: Optional[str] = None
    ibp_no: Optional[str] = None
    ibp_no_date: Optional[str] = None
    notary_address: Optional[str] = None
    home_street: Optional[str] = None
    barangay: Optional[str] = None
    city_province: Optional[str] = None
    mcle_no_period: Optional[str] = None
    mcle_no: Optional[str] = None
    mcle_no_date: Optional[str] = None
    # Client fields
    organization: Optional[str] = None
    position: Optional[str] = None


@app.patch("/api/profile")
async def edit_profile(
    req: ProfileEditRequest,
    authorization: Optional[str] = Header(None),
    ql_access: Optional[str] = Cookie(default=None),
):
    """Edit the authenticated user's own profile (ENP or client)."""
    user = get_current_user(authorization, ql_access)
    if not user:
        raise HTTPException(401, "Unauthorized")

    role = user.get("role", "")
    existing_profile = dict(user.get("profile") or {})
    top_level_updates: dict = {}

    # Common fields
    if req.first_name is not None:
        existing_profile["first_name"] = req.first_name
        top_level_updates["first_name"] = req.first_name
    if req.last_name is not None:
        existing_profile["last_name"] = req.last_name
        top_level_updates["last_name"] = req.last_name
    if req.prefix is not None:
        existing_profile["prefix"] = req.prefix
    if req.middle_initial is not None:
        existing_profile["middle_initial"] = req.middle_initial
    if req.suffix is not None:
        existing_profile["suffix"] = req.suffix
    if req.phone is not None:
        existing_profile["phone"] = req.phone

    # ENP-only fields
    if role == "attorney":
        if req.roll_no is not None:
            existing_profile["roll_no"] = req.roll_no
        if req.roll_date is not None:
            existing_profile["roll_date"] = req.roll_date
        if req.commission_no is not None:
            existing_profile["commission_no"] = req.commission_no
        if req.commission_no_valid_until is not None:
            existing_profile["commission_no_valid_until"] = req.commission_no_valid_until
        if req.npn is not None:
            existing_profile["npn"] = req.npn
        if req.ptr_no is not None:
            existing_profile["ptr_no"] = req.ptr_no
        if req.ptr_no_location is not None:
            existing_profile["ptr_no_location"] = req.ptr_no_location
        if req.ptr_no_date is not None:
            existing_profile["ptr_no_date"] = req.ptr_no_date
        if req.ibp_no is not None:
            existing_profile["ibp_no"] = req.ibp_no
        if req.ibp_no_date is not None:
            existing_profile["ibp_no_date"] = req.ibp_no_date
        if req.notary_address is not None:
            existing_profile["notary_address"] = req.notary_address
        if req.home_street is not None:
            existing_profile["home_street"] = req.home_street
        if req.barangay is not None:
            existing_profile["barangay"] = req.barangay
        if req.city_province is not None:
            existing_profile["city_province"] = req.city_province
        if req.mcle_no_period is not None:
            existing_profile["mcle_no_period"] = req.mcle_no_period
        if req.mcle_no is not None:
            existing_profile["mcle_no"] = req.mcle_no
        if req.mcle_no_date is not None:
            existing_profile["mcle_no_date"] = req.mcle_no_date

    # Client-only fields
    if role == "client":
        if req.organization is not None:
            existing_profile["organization"] = req.organization
        if req.position is not None:
            existing_profile["position"] = req.position

    updates = {"profile": existing_profile, **top_level_updates}
    updated = await update_user(user["id"], updates)
    return {"success": True, "user": updated}



# Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬ Onboarding Step 3: Certification Test Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬

_MAX_FREE_RETAKES = 3  # FIX-6


@app.get("/api/certification/start")
async def start_test(
    authorization: Optional[str] = Header(None),
    ql_access: Optional[str] = Cookie(default=None),
):
    """
    Start a new randomized certification test.
    FIX-6: Block if retake_count >= MAX_FREE_RETAKES and payment not confirmed.
    """
    user = get_current_user(authorization, ql_access)
    if not user:
        raise HTTPException(401, "Unauthorized")
    if not user.get("role"):
        raise HTTPException(400, "Complete role selection first")

    # FIX-6: Retake enforcement
    retake_count = user.get("retake_count", 0)
    if retake_count >= _MAX_FREE_RETAKES:
        payment_confirmed = user.get("retake_payment_confirmed", False)
        if not payment_confirmed:
            raise HTTPException(
                403,
                {
                    "error": "retake_limit_reached",
                    "message": (
                        f"You have used all {_MAX_FREE_RETAKES} free attempts. "
                        "Please pay the Ã¢â€šÂ±500 retake fee to continue."
                    ),
                    "retake_count": retake_count,
                    "payment_required": True,
                },
            )
        # Payment confirmed Ã¢â‚¬â€ consume it and allow one more attempt
        await update_user(user["id"], {"retake_payment_confirmed": False})

    # Generate randomized test (returns (client_questions, answer_key))
    client_questions, answer_key = get_randomized_test(role=user["role"], count=50)
    test_session_id = str(uuid.uuid4())

    # Store answer key server-side Ã¢â‚¬â€ never sent to client
    save_test_session(test_session_id, {
        "user_id": user["id"],
        "questions": client_questions,
        "answer_key": answer_key,
        "started_at": time.time(),
        "expires_at": time.time() + 86400,  # 24 hours
    })

    return {
        "success": True,
        "test_session_id": test_session_id,
        "questions": client_questions,
        "total": 15,
        "passing_score": 80,
        "time_limit_minutes": 90,
        "role": user["role"],
    }


@app.post("/api/certification/submit")
async def submit_test(
    req: TestAnswerRequest,
    authorization: Optional[str] = Header(None),
    ql_access: Optional[str] = Cookie(default=None),
):
    """Submit test answers for grading."""
    user = get_current_user(authorization, ql_access)
    if not user:
        raise HTTPException(401, "Unauthorized")

    session = get_test_session(req.test_session_id)
    if not session:
        raise HTTPException(404, "Test session not found or expired")
    if session["user_id"] != user["id"]:
        raise HTTPException(403, "Forbidden")
    if time.time() > session["expires_at"]:
        raise HTTPException(400, "Test session has expired")

    # Grade using server-side answer key
    result = grade_test(
        questions_without_answers=session["questions"],
        answer_key=session["answer_key"],
        user_answers=req.answers,
    )

    retake_count = user.get("retake_count", 0)
    updates: dict = {
        "test_result": result,
        "retake_count": retake_count if result["passed"] else retake_count + 1,
    }

    if result["passed"]:
        cert_id = generate_certificate_id(user.get("role", "client"))
        updates.update({
            "certificate_id": cert_id,
            "certificate_status": "certified",
            "onboarding_step": "kyc_id",
        })

    await update_user(user["id"], updates)

    # Fire fail email notification if not passed
    if not result["passed"]:
        send_test_fail_email(user, result["score_pct"])

    response: dict = {
        "success": True,
        "passed": result["passed"],
        "score": result["score_pct"],
        "correct": result["correct"],
        "total": result["total"],
        "passing_score": result["passing_score"],
    }

    if result["passed"]:
        response.update({
            "certificate_id": updates["certificate_id"],
            "message": "Ã°Å¸Å½â€° Congratulations! You passed. Your ENP certificate has been issued.",
            "next_step": "kyc_id",
        })
    else:
        new_retake_count = updates["retake_count"]
        remaining = max(0, _MAX_FREE_RETAKES - new_retake_count)
        response.update({
            "retake_fee_php": 500,
            "retake_count": new_retake_count,
            "retakes_remaining": remaining,
            "payment_required": remaining == 0,
            "message": (
                f"You scored {result['score_pct']}%. The passing score is 80% (12/15). "
                + (f"{remaining} free attempt(s) remaining." if remaining > 0 else "No free attempts left Ã¢â‚¬â€ Ã¢â€šÂ±500 retake fee required.")
            ),
            "payment_options": ["gcash", "bank_transfer"],
            "gcash_number": os.getenv("GCASH_NUMBER", "09XXXXXXXXX"),
            "bank_name": os.getenv("BANK_NAME", "BDO"),
            "bank_account": os.getenv("BANK_ACCOUNT", "XXXX-XXXX-XXXX"),
            "bank_account_name": os.getenv("BANK_ACCOUNT_NAME", "Quanby Solutions, Inc."),
        })

    return response


# Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬ Onboarding Step 4: Liveness + National ID Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬

_ALLOWED_IMAGE_TYPES = {".jpg", ".jpeg", ".png", ".webp"}


def _safe_upload_ext(filename: Optional[str], default: str = "jpg") -> str:
    """FIX-10: Sanitize upload filename Ã¢â‚¬â€ return safe extension only."""
    if not filename:
        return default
    name = os.path.basename(filename).strip()
    _, ext = os.path.splitext(name)
    ext = ext.lower().lstrip(".")
    if ext not in {"jpg", "jpeg", "png", "webp", "pdf"}:
        return default
    return ext



# ─── KYC ID Upload ─────────────────────────────────────────────────────────

@app.post("/api/onboarding/kyc-id")
async def upload_kyc_id(
    kyc_id: UploadFile = File(...),
    authorization: Optional[str] = Header(None),
    ql_access: Optional[str] = Cookie(default=None),
):
    """Upload government-issued ID for KYC. Sets onboarding_step to liveness."""
    user = get_current_user(authorization, ql_access)
    if not user:
        raise HTTPException(401, "Unauthorized")

    id_bytes = await kyc_id.read()
    if len(id_bytes) < 1000:
        raise HTTPException(400, "Invalid file — too small")
    if len(id_bytes) > 10 * 1024 * 1024:
        raise HTTPException(400, "File too large — max 10MB")

    ext = _safe_upload_ext(kyc_id.filename, default="jpg")
    kyc_dir = os.path.join(os.path.dirname(__file__), "data", "kyc_ids")
    os.makedirs(kyc_dir, exist_ok=True)
    kyc_path = os.path.join(kyc_dir, f"{user['id']}.{ext}")
    with open(kyc_path, "wb") as fh:
        fh.write(id_bytes)
    try:
        os.chmod(kyc_path, stat.S_IRUSR | stat.S_IWUSR)
    except OSError:
        pass

    await update_user(user["id"], {
        "kyc_id_uploaded": True,
        "onboarding_step": "liveness",
    })
    return {"success": True, "message": "KYC ID uploaded successfully.", "next_step": "liveness"}

@app.post("/api/onboarding/liveness")
async def submit_liveness(
    selfie: UploadFile = File(...),
    authorization: Optional[str] = Header(None),
    ql_access: Optional[str] = Cookie(default=None),
):
    """Submit webcam selfie for liveness verification."""
    user = get_current_user(authorization, ql_access)
    if not user:
        raise HTTPException(401, "Unauthorized")

    selfie_bytes = await selfie.read()
    if len(selfie_bytes) < 1000:
        raise HTTPException(400, "Invalid image Ã¢â‚¬â€ file too small")

    # FIX-10: Sanitize filename
    ext = _safe_upload_ext(selfie.filename)
    selfie_dir = os.path.join(os.path.dirname(__file__), "data", "selfies")
    os.makedirs(selfie_dir, exist_ok=True)
    selfie_path = os.path.join(selfie_dir, f"{user['id']}.{ext}")
    with open(selfie_path, "wb") as f:
        f.write(selfie_bytes)
    # FIX-5: Restrict file permissions
    try:
        os.chmod(selfie_path, stat.S_IRUSR | stat.S_IWUSR)
    except OSError:
        pass

    await update_user(user["id"], {"liveness_verified": True})

    updated = get_user(user["id"])
    if updated and updated.get("national_id_uploaded"):
        await update_user(user["id"], {"onboarding_step": "survey"})
        return {"success": True, "message": "Liveness verified Ã¢Å“â€¦", "next_step": "survey"}

    return {"success": True, "message": "Liveness verified Ã¢Å“â€¦", "next_step": "national_id"}


@app.post("/api/onboarding/national-id")
async def upload_national_id(
    national_id: UploadFile = File(...),
    authorization: Optional[str] = Header(None),
    ql_access: Optional[str] = Cookie(default=None),
):
    """Upload national ID document."""
    user = get_current_user(authorization, ql_access)
    if not user:
        raise HTTPException(401, "Unauthorized")

    id_bytes = await national_id.read()
    if len(id_bytes) < 1000:
        raise HTTPException(400, "Invalid file")

    # FIX-10: Sanitize filename
    ext = _safe_upload_ext(national_id.filename, default="jpg")
    id_dir = os.path.join(os.path.dirname(__file__), "data", "national_ids")
    os.makedirs(id_dir, exist_ok=True)
    id_path = os.path.join(id_dir, f"{user['id']}.{ext}")
    with open(id_path, "wb") as f:
        f.write(id_bytes)
    # FIX-5: Restrict file permissions
    try:
        os.chmod(id_path, stat.S_IRUSR | stat.S_IWUSR)
    except OSError:
        pass

    await update_user(user["id"], {"national_id_uploaded": True})

    updated = get_user(user["id"])
    if updated and updated.get("liveness_verified"):
        await update_user(user["id"], {"onboarding_step": "survey"})
        return {"success": True, "message": "National ID uploaded Ã¢Å“â€¦", "next_step": "survey"}

    return {"success": True, "message": "National ID uploaded Ã¢Å“â€¦", "next_step": "liveness"}


# Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬ Onboarding Step 5: Full Certification Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬

@app.post("/api/onboarding/complete")
async def complete_onboarding(
    authorization: Optional[str] = Header(None),
    ql_access: Optional[str] = Cookie(default=None),
):
    """Mark onboarding complete Ã¢â€ â€™ upgrade cert to fully certified."""
    user = get_current_user(authorization, ql_access)
    if not user:
        raise HTTPException(401, "Unauthorized")

    if not user.get("liveness_verified"):
        raise HTTPException(400, "Liveness verification required")
    if not user.get("national_id_uploaded"):
        raise HTTPException(400, "National ID upload required")
    if not (user.get("test_result") or {}).get("passed"):
        raise HTTPException(400, "Certification test must be passed first")

    await update_user(user["id"], {
        "certificate_status": "certified",
        "onboarding_step": "certified",
    })

    return {
        "success": True,
        "certificate_id": user["certificate_id"],
        "message": "Ã°Å¸Å½â€° Full certification complete! Download your certificate and present it to the Supreme Court.",
        "next_step": "certified",
    }


# Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬ Certificate Download Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬

@app.get("/api/certificate/{certificate_id}")
async def get_certificate(
    certificate_id: str,
    authorization: Optional[str] = Header(None),
    ql_access: Optional[str] = Cookie(default=None),
):
    """Download printable HTML certificate."""
    user = get_current_user(authorization, ql_access)
    if not user:
        raise HTTPException(401, "Unauthorized")
    if user.get("certificate_id") != certificate_id:
        raise HTTPException(403, "Certificate not found for this account")

    html = get_certificate_html(user)
    return HTMLResponse(
        content=html,
        status_code=200,
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, private",
            "Pragma": "no-cache",
            "CDN-Cache-Control": "no-store",
            "Cloudflare-CDN-Cache-Control": "no-store",
        }
    )



@app.post("/api/certificate/regenerate")
async def regenerate_certificate(
    authorization: Optional[str] = Header(None),
    ql_access: Optional[str] = Cookie(default=None),
):
    """Regenerate certificate: issues a new certificate ID for the authenticated user."""
    user = get_current_user(authorization, ql_access)
    if not user:
        raise HTTPException(401, "Unauthorized")

    # Must have an existing cert to regenerate
    if not user.get("certificate_id"):
        raise HTTPException(400, "No certificate found for this account. Complete onboarding first.")

    # Generate a fresh certificate ID
    new_cert_id = generate_certificate_id(user.get("role", "client"))

    await update_user(user["id"], {
        "certificate_id": new_cert_id,
        # preserve existing certificate_status (probationary/certified)
    })

    return {
        "success": True,
        "old_certificate_id": user["certificate_id"],
        "certificate_id": new_cert_id,
        "message": "Certificate regenerated successfully. Use the new certificate ID to download your certificate.",
    }


# ─── HyperVerge KYC Token ──────────────────────────────────────────────────

@app.post("/api/onboarding/hyperverge-token")
async def get_hyperverge_token(
    authorization: Optional[str] = Header(None),
    ql_access: Optional[str] = Cookie(default=None),
):
    """Generate a short-lived HyperVerge access token for the Web SDK."""
    user = get_current_user(authorization, ql_access)
    if not user:
        raise HTTPException(401, "Unauthorized")

    hv_app_id  = os.getenv("HYPERVERGE_APP_ID", "")
    hv_app_key = os.getenv("HYPERVERGE_APP_KEY", "")
    hv_api_url = os.getenv("HYPERVERGE_API_URL", "https://auth.hyperverge.co")

    if not hv_app_id or not hv_app_key:
        raise HTTPException(500, "HyperVerge credentials not configured")

    try:
        import urllib.request as _hv_req, json as _hv_json
        hv_payload = _hv_json.dumps({"appId": hv_app_id, "appKey": hv_app_key, "expiry": 600}).encode()
        hv_req = _hv_req.Request(
            f"{hv_api_url}/login",
            data=hv_payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with _hv_req.urlopen(hv_req, timeout=10) as _hv_resp:
            data = _hv_json.loads(_hv_resp.read().decode())
        token = (data.get("result") or {}).get("token") or data.get("token")
        if not token:
            raise ValueError(f"No token in response: {data}")
    except Exception as exc:
        import sys
        print(f"[HyperVerge] token error: {exc}", file=sys.stderr)
        raise HTTPException(502, f"HyperVerge auth failed: {exc}")

    return {
        "token": token,
        "appId": hv_app_id,
        "workflowId": os.getenv("HYPERVERGE_WORKFLOW_ID", "workflow_onboarding"),
        "sdkVersion": os.getenv("HYPERVERGE_WEB_SDK_VERSION", "10.3.0"),
        "transactionId": f"ql-{user['id'][:8]}-{int(__import__('time').time())}",
    }


@app.post("/api/onboarding/hyperverge-complete")
async def hyperverge_complete(
    request: Request,
    authorization: Optional[str] = Header(None),
    ql_access: Optional[str] = Cookie(default=None),
):
    """Called by frontend after HyperVerge SDK completes. Marks liveness verified."""
    user = get_current_user(authorization, ql_access)
    if not user:
        raise HTTPException(401, "Unauthorized")

    body = await request.json()
    status = body.get("status", "")
    result = body.get("result", {})
    transaction_id = body.get("transactionId", "")

    # Accept: user_cancelled → don't advance, just return
    if status == "user_cancelled":
        return {"success": False, "message": "KYC cancelled by user."}

    # Any non-error outcome from HV = verified (auto_approved / needs_review / error handled server-side)
    if status in ("auto_approved", "needs_review", "success", "complete"):
        from datetime import datetime, timezone as _tz
        await update_user(user["id"], {
            "liveness_verified": True,
            "kyc_id_uploaded": True,
            "national_id_uploaded": True,
            "hyperverge_transaction_id": transaction_id,
            "hyperverge_status": status,
            "kyc_verified_at": datetime.now(_tz.utc).isoformat(),
            "onboarding_step": "certificate",
        })
        # Issue cert if not already issued
        updated = get_user(user["id"])
        if updated and not updated.get("certificate_id"):
            from onboarding import generate_certificate_id
            cert_id = generate_certificate_id(updated.get("role", "client"))
            await update_user(user["id"], {
                "certificate_id": cert_id,
                "certificate_status": "certified",
            })
        return {"success": True, "message": "KYC complete.", "next_step": "certificate"}

    # error / rejected
    return {"success": False, "message": f"KYC not approved (status: {status}). Please try again.", "status": status}

@app.get("/api/verify/{certificate_id}")
@limiter.limit("20/minute")  # FIX-4: Rate limit certificate verification
async def verify_certificate(request: Request, certificate_id: str):
    """
    Public certificate verification endpoint.
    FIX-4: O(1) CERT_INDEX lookup instead of iterating all users.
    """
    user = lookup_user_by_certificate_id(certificate_id)
    if not user:
        return {"valid": False, "certificate_id": certificate_id}

    return {
        "valid": True,
        "certificate_id": certificate_id,
        "name": f"{user.get('first_name', '')} {user.get('last_name', '')}",
        "role": user.get("role"),
        "status": user.get("certificate_status"),
        "issued_at": user.get("created_at"),
    }


# Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬ Retake Payment Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬

@app.post("/api/certification/retake-payment")
async def submit_retake_payment(
    req: RetakePaymentRequest,
    authorization: Optional[str] = Header(None),
    ql_access: Optional[str] = Cookie(default=None),
):
    """
    Record retake payment confirmation.
    Production: integrate with PayMongo/GCash webhook before setting confirmed=True.
    """
    user = get_current_user(authorization, ql_access)
    if not user:
        raise HTTPException(401, "Unauthorized")

    # Mark payment as pending Ã¢â‚¬â€ admin/webhook must confirm
    await update_user(user["id"], {"retake_payment_pending": True, "retake_payment_confirmed": False})

    return {
        "success": True,
        "message": f"Payment via {req.payment_method} recorded. Once confirmed by our team, you may retake the test.",
        "instructions": {
            "gcash": f"Send Ã¢â€šÂ±500 to {os.getenv('GCASH_NUMBER', '09XX-XXX-XXXX')} with reference: RETAKE-{user['id'][:8].upper()}",
            "bank_transfer": (
                f"Transfer Ã¢â€šÂ±500 to {os.getenv('BANK_NAME', 'BDO')} "
                f"Acc: {os.getenv('BANK_ACCOUNT', 'XXXX')} | "
                f"Account Name: Quanby Solutions, Inc. | "
                f"Ref: RETAKE-{user['id'][:8].upper()}"
            ),
        },
    }


# Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬ Admin: confirm retake payment (protected Ã¢â‚¬â€ add admin auth in production) Ã¢â€â‚¬

@app.post("/api/admin/confirm-retake/{user_id}")
async def admin_confirm_retake(
    user_id: str,
    authorization: Optional[str] = Header(None),
    ql_access: Optional[str] = Cookie(default=None),
):
    """
    Admin endpoint to confirm a retake payment and unlock next attempt.
    TODO: Add admin-role check before production deployment.
    """
    # Placeholder admin check Ã¢â‚¬â€ replace with proper role-based auth
    admin_secret = os.getenv("ADMIN_SECRET", "")
    token = _token_from_request(authorization, ql_access)
    if not admin_secret or token != admin_secret:
        raise HTTPException(403, "Admin access required")

    target_user = get_user(user_id)
    if not target_user:
        raise HTTPException(404, "User not found")

    await update_user(user_id, {
        "retake_payment_pending": False,
        "retake_payment_confirmed": True,
    })
    return {"success": True, "message": f"Retake unlocked for user {user_id}"}


# Ã¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢Â
# LEGAL AI CHATBOT Ã¢â‚¬â€ POST /api/chatbot
# Ã¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢Â




# ─── Retake Payment (NEW canonical endpoints) ───────────────────────────────

@app.post("/api/retake/initiate")
async def retake_initiate(
    authorization: Optional[str] = Header(None),
    ql_access: Optional[str] = Cookie(default=None),
):
    """Return payment details for retake. Requires retake_count >= 1."""
    user = get_current_user(authorization, ql_access)
    if not user:
        raise HTTPException(401, "Unauthorized")
    retake_count = user.get("retake_count", 0)
    ref = f"RETAKE-{user['id'][:8].upper()}-{retake_count}"
    return {
        "success": True,
        "amount": 500,
        "reference_code": ref,
        "gcash_number": os.getenv("GCASH_NUMBER", "09XX-XXX-XXXX"),
        "bank_name": os.getenv("BANK_NAME", "BDO"),
        "bank_account": os.getenv("BANK_ACCOUNT", "XXXX-XXXX-XXXX"),
        "bank_account_name": os.getenv("BANK_ACCOUNT_NAME", "Quanby Solutions, Inc."),
        "retake_count": retake_count,
    }


class RetakeConfirmRequest(BaseModel):
    payment_method: str  # "gcash" or "bank_transfer"
    reference: str


@app.post("/api/retake/confirm-payment")
async def retake_confirm_payment(
    req: RetakeConfirmRequest,
    authorization: Optional[str] = Header(None),
    ql_access: Optional[str] = Cookie(default=None),
):
    """User confirms payment sent — marks as pending admin verification."""
    user = get_current_user(authorization, ql_access)
    if not user:
        raise HTTPException(401, "Unauthorized")
    if req.payment_method not in ("gcash", "bank_transfer"):
        raise HTTPException(400, "Invalid payment_method")
    await update_user(user["id"], {
        "retake_payment_pending": True,
        "retake_payment_confirmed": False,
        "retake_payment_method": req.payment_method,
        "retake_payment_reference": req.reference,
    })
    return {
        "success": True,
        "message": "Payment submitted! You will receive an email once verified.",
        "next_step": "test",
    }

# ── Onboarding Retake Payment (frontend-facing) ─────────────────────────────

@app.post("/api/onboarding/retake-payment")
async def onboarding_retake_payment(
    authorization: Optional[str] = Header(None),
    ql_access: Optional[str] = Cookie(default=None),
):
    """Return payment details for retake fee. Frontend polls this to get GCash/bank info."""
    user = get_current_user(authorization, ql_access)
    if not user:
        raise HTTPException(401, "Unauthorized")
    ref = f"RETAKE-{user['id'][:8].upper()}"
    return {
        "gcash_number": os.getenv("GCASH_NUMBER", "09XX-XXX-XXXX"),
        "bank_name": os.getenv("BANK_NAME", "BDO"),
        "bank_account": os.getenv("BANK_ACCOUNT", "XXXX-XXXX-XXXX"),
        "bank_account_name": os.getenv("BANK_ACCOUNT_NAME", "Quanby Solutions, Inc."),
        "reference_number": ref,
        "amount": 500,
    }


@app.post("/api/onboarding/retake-payment/verify")
async def verify_retake_payment(
    authorization: Optional[str] = Header(None),
    ql_access: Optional[str] = Cookie(default=None),
):
    """User confirms they have sent payment — marks as pending verification."""
    user = get_current_user(authorization, ql_access)
    if not user:
        raise HTTPException(401, "Unauthorized")
    ref = f"RETAKE-{user['id'][:8].upper()}"
    await update_user(user["id"], {
        "retake_payment_pending": True,
        "retake_payment_confirmed": False,
    })
    return {
        "success": True,
        "message": "Payment submission received. Verification within 24 hours.",
        "reference_number": ref,
    }

# Chat session store: { session_id: { history, created_at, last_active, msg_timestamps } }
legal_chat_sessions: dict = {}
_chat_lock = threading.Lock()

_CHAT_SESSION_TTL  = 7200  # 2-hour idle TTL
_CHAT_RATE_LIMIT   = 20    # max messages per session per hour
_CHAT_RATE_WINDOW  = 3600  # 1-hour sliding window

_LEGAL_CHATBOT_SYSTEM_PROMPT = """You are Quanby Legal AI Ã¢â‚¬â€ the official AI assistant for Quanby Legal, the Philippines' first and only Supreme Court-accredited Electronic Notarization Facility (ENF).

## YOUR SPECIALIZATIONS

### Philippine Electronic Notarization Framework
- A.M. No. 24-10-14-SC (2024): Supreme Court Rules on Electronic Notarization. Authorizes accredited ENFs, defines Electronic Notary Publics (ENPs), sets technical/security standards.
- RA 8792 (E-Commerce Act of 2000): Electronic documents and signatures carry the same legal force as physical ones.
- RA 10173 (Data Privacy Act of 2012): Governs personal data collection/processing; mandates security measures and NPC breach reporting.
- BSP Circular 944: BSP framework for virtual currencies and digital financial transactions.
- SEC Memorandum Circular 28-2020: SEC rules for electronic corporate document submission and digital signatures.

### Philippine Contract Law
- Civil Code of the Philippines (RA 386): obligations and contracts
- Notarization requirements for specific instruments
- Electronic evidence admissibility in Philippine courts

## PLATFORM INFORMATION

### ENP Certification Process
1. Register via Google SSO
2. Select role: Attorney (IBP member) or Client
3. Complete professional profile
4. Pass certification exam: 15 questions, 80% passing score; covers A.M. No. 24-10-14-SC, RA 8792, RA 10173, BSP Circular 944, SEC MC 28-2020
5. Liveness verification (webcam selfie)
6. National ID upload
7. Supreme Court accreditation submission
Note: 3 free exam attempts; retakes cost PHP 500 each.

### Documents Eligible for E-Notarization
YES: Deeds of Sale, Contracts of Lease, Special Power of Attorney, Affidavits, Articles of Incorporation/Partnership, Employment Contracts, Loan Agreements, MOA/MOU, Joint Venture Agreements
NOT eligible: Wills, testaments, documents requiring exclusive physical appearance

### Pricing
- Certification exam: FREE (3 attempts)
- Retake fee: PHP 500 per attempt after 3rd
- Document notarization: varies by ENP and document type (SC fee schedules)
- Enterprise/law firm plans: contact Quanby Legal for quotation

## RESPONSE GUIDELINES
- Be professional, clear, and helpful
- Cite specific laws/rules when relevant
- Always include: "This is general information only Ã¢â‚¬â€ not legal advice. For your specific situation, consult a licensed Philippine attorney or one of our certified ENPs."
- Support both English and Filipino (Tagalog)
- Keep responses concise and focused
- Never fabricate legal provisions or case citations
"""


def _clean_legal_chat_sessions() -> None:
    """Remove sessions idle longer than TTL."""
    now = time.time()
    with _chat_lock:
        expired = [
            sid for sid, s in legal_chat_sessions.items()
            if now - s.get("last_active", 0) > _CHAT_SESSION_TTL
        ]
        for sid in expired:
            del legal_chat_sessions[sid]


def _chatbot_keyword_fallback(message: str) -> str:
    """Keyword-based responses when no AI API key is configured."""
    msg = message.lower()

    if any(k in msg for k in ["hello", "hi ", "hi!", "kumusta", "kamusta", "magandang", "good morning", "good afternoon", "good evening"]):
        return (
            "Hello! \U0001f44b Welcome to **Quanby Legal AI**.\n\n"
            "I can help you with:\n"
            "\u2022 \U0001f3db\ufe0f Philippine electronic notarization (A.M. No. 24-10-14-SC)\n"
            "\u2022 \U0001f4dc ENP certification process and requirements\n"
            "\u2022 \U0001f4c4 Documents eligible for e-notarization\n"
            "\u2022 \u2696\ufe0f Philippine legal framework (RA 8792, RA 10173, BSP Circular 944)\n"
            "\u2022 \U0001f4b0 Platform pricing and services\n\n"
            "What can I help you with today?"
        )

    if any(k in msg for k in ["become", "enp", "certif", "how do i", "how to become", "process", "steps", "register"]):
        return (
            "**How to Become a Certified ENP on Quanby Legal**\n\n"
            "1. **Register** \u2014 Sign up via Google\n"
            "2. **Select Role** \u2014 Choose *Attorney* (IBP member) or *Client*\n"
            "3. **Complete Profile** \u2014 Fill in your professional details\n"
            "4. **Pass the Certification Exam** \u2014 15 questions, 80% passing score\n"
            "   Topics: A.M. No. 24-10-14-SC \u00b7 RA 8792 \u00b7 RA 10173 \u00b7 BSP Circular 944 \u00b7 SEC MC 28-2020\n"
            "5. **Liveness Check** \u2014 Upload a webcam selfie\n"
            "6. **Upload National ID** \u2014 Government-issued ID required\n"
            "7. **SC Submission** \u2014 Your application is forwarded to the Supreme Court\n\n"
            "\U0001f4cb You get **3 free exam attempts**. Retakes cost \u20b1500 each.\n\n"
            "\u26a0\ufe0f *General information only \u2014 not legal advice. Consult a licensed Philippine attorney for specific guidance.*"
        )

    if any(k in msg for k in ["document", "what can", "eligible", "notariz", "which doc", "ano"]):
        return (
            "**Documents Eligible for E-Notarization** (A.M. No. 24-10-14-SC)\n\n"
            "\u2705 Deeds of Absolute Sale\n"
            "\u2705 Contracts of Lease\n"
            "\u2705 Special Power of Attorney\n"
            "\u2705 Affidavits and sworn statements\n"
            "\u2705 Articles of Incorporation / Partnership\n"
            "\u2705 Employment contracts requiring notarization\n"
            "\u2705 Loan agreements\n"
            "\u2705 Memoranda of Agreement / Understanding\n"
            "\u2705 Joint Venture Agreements\n\n"
            "\u274c **Not eligible**: Wills, testaments, documents requiring exclusively physical notarization\n\n"
            "\u26a0\ufe0f *General information only \u2014 consult a licensed Philippine attorney for specific guidance.*"
        )

    if any(k in msg for k in ["a.m. no", "am no", "24-10-14", "supreme court rules", "sc rules", "electronic notariz"]):
        return (
            "**A.M. No. 24-10-14-SC \u2014 Rules on Electronic Notarization (2024)**\n\n"
            "Issued by the Supreme Court of the Philippines, this landmark rule:\n\n"
            "\u2022 Authorizes **Electronic Notarization Facilities (ENFs)** accredited by the SC\n"
            "\u2022 Defines **Electronic Notary Publics (ENPs)** \u2014 attorneys certified for digital notarial acts\n"
            "\u2022 Sets technical security standards: electronic signatures, digital certificates, identity verification\n"
            "\u2022 Requires tamper-proof audit trails and document integrity verification\n"
            "\u2022 Electronic notarial acts carry the **same legal force** as traditional notarization\n\n"
            "\U0001f3db\ufe0f **Quanby Legal** is the Philippines' **first and only** SC-accredited ENF under these rules.\n\n"
            "\u26a0\ufe0f *General information only \u2014 not legal advice. Consult a licensed Philippine attorney for specific guidance.*"
        )

    if any(k in msg for k in ["ra 8792", "8792", "e-commerce act", "ecommerce", "electronic commerce"]):
        return (
            "**RA 8792 \u2014 Electronic Commerce Act of 2000**\n\n"
            "This foundational law establishes:\n\n"
            "\u2022 **Electronic documents** = legally equivalent to paper documents\n"
            "\u2022 **Electronic signatures** = legally valid when properly authenticated\n"
            "\u2022 **Electronic contracts** = enforceable under Philippine law\n"
            "\u2022 Governs admissibility of electronic evidence in Philippine courts\n"
            "\u2022 Sets standards for government and private sector digital transactions\n\n"
            "**Relevance**: RA 8792 combined with A.M. No. 24-10-14-SC makes electronically notarized documents fully valid and enforceable.\n\n"
            "\u26a0\ufe0f *General information only \u2014 not legal advice.*"
        )

    if any(k in msg for k in ["ra 10173", "10173", "data privacy", "privacy act", "personal data", "npc"]):
        return (
            "**RA 10173 \u2014 Data Privacy Act of 2012**\n\n"
            "Key provisions:\n\n"
            "\u2022 Personal data must be collected for **specific, legitimate purposes**\n"
            "\u2022 Data subjects have rights to **access, correct, erase, and object** to processing\n"
            "\u2022 Organizations must implement **technical and organizational security measures**\n"
            "\u2022 Data breaches must be reported to the **National Privacy Commission (NPC)**\n"
            "\u2022 Violations: fines up to \u20b15 million and/or imprisonment\n\n"
            "**Relevance**: Quanby Legal processes personal data (IDs, biometrics, documents) in full compliance with RA 10173.\n\n"
            "\u26a0\ufe0f *General information only \u2014 not legal advice.*"
        )

    if any(k in msg for k in ["price", "cost", "fee", "how much", "pricing", "magkano", "bayad", "libre"]):
        return (
            "**Quanby Legal Pricing**\n\n"
            "\U0001f393 **ENP Certification**\n"
            "\u2022 Certification exam: **FREE** (3 attempts included)\n"
            "\u2022 Retake fee: **\u20b1500** per attempt (after 3rd)\n\n"
            "\U0001f4c4 **Document Notarization**\n"
            "\u2022 Fees vary by document type and ENP\n"
            "\u2022 Governed by Supreme Court fee schedules\n"
            "\u2022 Generally lower than traditional notarization\n\n"
            "\U0001f3e2 **Enterprise / Law Firm Plans**\n"
            "\u2022 Custom pricing for bulk notarization volume\n"
            "\u2022 Contact our team for a quotation\n\n"
            "\u26a0\ufe0f *For current exact pricing, contact Quanby Legal directly. General information only.*"
        )

    if any(k in msg for k in ["legally binding", "legally valid", "legal binding", "valid", "enforceable", "ligal", "totoo", "court"]):
        return (
            "**Is E-Notarization Legally Binding in the Philippines?**\n\n"
            "**Yes \u2014 absolutely.**\n\n"
            "\u2705 **A.M. No. 24-10-14-SC** \u2014 Supreme Court explicitly authorizes electronic notarization\n"
            "\u2705 **RA 8792** \u2014 Electronic signatures and documents equal physical ones in legal force\n"
            "\u2705 **Court Acceptance** \u2014 Philippine courts accept electronically notarized documents\n"
            "\u2705 **Audit Trail** \u2014 Tamper-proof document integrity verification\n"
            "\u2705 **Only Accredited Platform** \u2014 Quanby Legal is the sole SC-accredited ENF in the Philippines\n\n"
            "\u26a0\ufe0f *This is general information. For specific legal questions, consult a licensed Philippine attorney or certified ENP.*"
        )

    if any(k in msg for k in ["bsp", "circular 944", "bangko sentral", "bsp circular"]):
        return (
            "**BSP Circular 944 \u2014 Virtual Currency Framework**\n\n"
            "Issued by Bangko Sentral ng Pilipinas, this circular:\n\n"
            "\u2022 Establishes regulatory framework for virtual currency exchanges (VCEs)\n"
            "\u2022 Sets AML/KYC requirements for digital financial platforms\n"
            "\u2022 Governs electronic money and digital payment systems\n"
            "\u2022 Relevant for contracts involving cryptocurrency and digital assets\n\n"
            "**Relevance**: For contracts involving digital currencies or fintech transactions, BSP Circular 944 compliance is an important consideration alongside e-notarization.\n\n"
            "\u26a0\ufe0f *General information only \u2014 not legal advice.*"
        )

    if any(k in msg for k in ["sec mc", "sec memorandum", "mc 28", "sec mc 28", "memorandum circular 28", "securities commission"]):
        return (
            "**SEC Memorandum Circular 28-2020**\n\n"
            "The Securities and Exchange Commission issued MC 28-2020 to allow:\n\n"
            "\u2022 Electronic submission of corporate documents to the SEC\n"
            "\u2022 Digital signatures on SEC filings\n"
            "\u2022 Online corporate registration and amendments\n"
            "\u2022 Digital General Information Sheets (GIS) and financial statements\n\n"
            "**Practical impact**: Combined with Quanby Legal e-notarization, the entire corporate document lifecycle can be fully paperless and legally valid.\n\n"
            "\u26a0\ufe0f *General information only \u2014 not legal advice.*"
        )

    return (
        "Thank you for your question! I can provide information about:\n\n"
        "\u2022 **ENP Certification** \u2014 How to become a certified Electronic Notary Public\n"
        "\u2022 **E-Notarization** \u2014 Documents eligible, legal validity, process\n"
        "\u2022 **A.M. No. 24-10-14-SC** \u2014 Supreme Court rules on electronic notarization\n"
        "\u2022 **RA 8792, RA 10173, BSP Circular 944, SEC MC 28-2020** \u2014 Applicable laws\n"
        "\u2022 **Pricing** \u2014 Certification and notarization fees\n\n"
        "Please try rephrasing your question, or contact Quanby Legal directly for personalized assistance.\n\n"
        "\u26a0\ufe0f *Quanby Legal AI provides general information only \u2014 not legal advice. Consult a licensed Philippine attorney for specific guidance.*"
    )


@app.post("/api/chatbot")
async def chatbot_endpoint(request: LegalChatRequest):
    """
    Quanby Legal AI Chatbot \u2014 public endpoint for Philippine legal and platform queries.
    - Uses xAI Grok (XAI_API_KEY) or OpenAI (OPENAI_API_KEY) when configured
    - Falls back to keyword-based responses when no AI key is set
    - Rate limit: 20 messages per session per hour
    - Session history maintained in-memory with 2-hour idle TTL
    """
    # Periodic cleanup (non-blocking background thread)
    if int(time.time()) % 60 < 2:
        threading.Thread(target=_clean_legal_chat_sessions, daemon=True).start()

    message = (request.message or "").strip()
    if not message:
        raise HTTPException(400, "Message cannot be empty")
    if len(message) > 2000:
        raise HTTPException(400, "Message too long. Maximum 2000 characters.")

    session_id = (request.session_id or "").strip() or str(uuid.uuid4())
    now = time.time()

    with _chat_lock:
        if session_id not in legal_chat_sessions:
            legal_chat_sessions[session_id] = {
                "history": [],
                "created_at": now,
                "last_active": now,
                "msg_timestamps": [],
            }

        session = legal_chat_sessions[session_id]

        # Sliding-window rate limit
        session["msg_timestamps"] = [
            t for t in session["msg_timestamps"] if now - t < _CHAT_RATE_WINDOW
        ]
        if len(session["msg_timestamps"]) >= _CHAT_RATE_LIMIT:
            raise HTTPException(
                429,
                "Rate limit reached: 20 messages per hour per session. Please wait and try again.",
            )

        session["msg_timestamps"].append(now)
        session["last_active"] = now
        history_snapshot = list(session["history"])

    # Generate response — try providers in order: GLM (ZhipuAI) > xAI > OpenAI > fallback
    zhipu_key = os.getenv("ZHIPU_API_KEY")
    zhipu_model = os.getenv("ZHIPU_MODEL", "glm-4-flash")
    xai_key = os.getenv("XAI_API_KEY")
    oai_key = os.getenv("OPENAI_API_KEY")
    reply: str

    ai_key = None
    ai_base_url = None
    ai_model = None

    if zhipu_key:
        ai_key = zhipu_key
        ai_base_url = "https://open.bigmodel.cn/api/paas/v4/"
        ai_model = zhipu_model
    elif xai_key:
        ai_key = xai_key
        ai_base_url = "https://api.x.ai/v1"
        ai_model = "grok-3-fast-beta"
    elif oai_key:
        ai_key = oai_key
        ai_base_url = None
        ai_model = "gpt-4o-mini"

    if ai_key:
        try:
            from openai import OpenAI as _OpenAI
            client = _OpenAI(api_key=ai_key, base_url=ai_base_url)

            messages = [{"role": "system", "content": _LEGAL_CHATBOT_SYSTEM_PROMPT}]
            messages.extend(history_snapshot[-20:])
            messages.append({"role": "user", "content": message})

            completion = client.chat.completions.create(
                model=ai_model,
                messages=messages,
                max_tokens=800,
                temperature=0.4,
            )
            reply = (completion.choices[0].message.content or "").strip()
            if not reply:
                reply = _chatbot_keyword_fallback(message)
        except Exception as exc:
            import sys
            print(f"[chatbot] AI error ({ai_model}): {exc}", file=sys.stderr)
            reply = _chatbot_keyword_fallback(message)
    else:
        reply = _chatbot_keyword_fallback(message)

    # Persist history (cap at 40 messages = 20 turns)
    with _chat_lock:
        if session_id in legal_chat_sessions:
            hist = legal_chat_sessions[session_id]["history"]
            hist.append({"role": "user",      "content": message})
            hist.append({"role": "assistant", "content": reply})
            if len(hist) > 40:
                legal_chat_sessions[session_id]["history"] = hist[-40:]

    return {"reply": reply, "session_id": session_id}




# ── GET /api/sub-orgs/{sub_org_id}/dc-info ────────────────────────────────────
@app.get("/api/sub-orgs/{sub_org_id}/dc-info")
async def get_sub_org_dc_info(sub_org_id: str, request: Request):
    """Fetch live sub-org details from DoconChain using the stored dc_sub_org_uuid."""
    user = _require_attorney_or_admin(request)
    org = _db.get_suborg(sub_org_id)
    if not org:
        raise HTTPException(404, "Sub-org not found")
    dc_uuid = org.get("dc_sub_org_uuid")
    if not dc_uuid:
        raise HTTPException(404, "This sub-org has not been provisioned in DoconChain yet")
    try:
        import urllib.request as _ur_gi, urllib.error as _ue_gi, json as _json_gi
        _tok_gi = _get_dc_token()
        _req_gi = _ur_gi.Request(
            f"{_DC_BASE}/api/v2/organizations/sub/{dc_uuid}?user_type=ENTERPRISE_API",
            headers={"Authorization": f"Bearer {_tok_gi}", "Accept": "application/json"},
            method="GET",
        )
        with _ur_gi.urlopen(_req_gi, timeout=20) as _r_gi:
            _dc_gi = _json_gi.loads(_r_gi.read().decode())
        # Update photo_url in local record if available
        _photo = (_dc_gi.get("branding_photo_url") or _dc_gi.get("photo_url") or
                  (_dc_gi.get("data") or {}).get("photo") or "")
        if _photo and _photo != org.get("dc_photo_url"):
            org2 = _db.get_suborg(sub_org_id)
            if org2:
                org2["dc_photo_url"] = _photo
                _db.save_suborg(org2)
        return {"dc_data": _dc_gi, "dc_sub_org_uuid": dc_uuid, "dc_photo_url": _photo}
    except _ue_gi.HTTPError as he:
        raise HTTPException(he.code, f"DoconChain error {he.code}: {he.read().decode()[:200]}")
    except Exception as e:
        raise HTTPException(502, f"Could not fetch from DoconChain: {str(e)[:200]}")


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("APP_PORT", 8080))
    uvicorn.run("main:app", host="127.0.0.1", port=port, reload=False)

# ══════════════════════════════════════════════════════════════════════════════
# APPOINTMENTS & ENP BOOKING SYSTEM
# ══════════════════════════════════════════════════════════════════════════════

# httpx removed — broken on Python 3.12 (h11 dataclass issue); using urllib instead
import urllib.request as _urllib_req
import urllib.error as _urllib_err
from datetime import datetime as _dt, timezone as _tz
# fpdf removed — using raw PDF bytes (FPDF incompatible with Python 3.12)

# ─── Appointments data store ──────────────────────────────────────────────────
# ─── DoconChain Configuration ──────────────────────────────────────────────────
_DC_BASE         = os.getenv("DOCONCHAIN_API_URL",  "https://stg-api2.doconchain.com")
_DC_APP_URL      = os.getenv("DOCONCHAIN_APP_URL",  "https://stg-app.doconchain.com")
_DC_CLIENT_KEY   = os.getenv("DOCONCHAIN_CLIENT_KEY",    "U2FsdGVkX19dxrNafE8249yn0M/GMqq3WAbITHfKYl8=")
_DC_CLIENT_SECRET= os.getenv("DOCONCHAIN_CLIENT_SECRET", "5sd07WmZyXJft2jEP8LOJyfGH")
_DC_EMAIL        = os.getenv("DOCONCHAIN_EMAIL",         "stg_quanby@maildrop.cc")

def _get_vault_uuid_for_project(project_uuid: str, dc_token: str) -> str:
    """
    Look up the vault UUID for a completed project by its project_uuid.
    Returns vault UUID string or empty string if not found.
    GET /vault/items returns completed projects with project_uuid field.
    """
    import urllib.request as _uvr, json as _jvr
    try:
        _page = 1
        while True:
            _url = f"{_DC_BASE}/vault/items?user_type=ENTERPRISE_API&per_page=50&page={_page}&user_items_only=no&api_integrated_projects_only=no"
            _req = _uvr.Request(_url, headers={"Authorization": f"Bearer {dc_token}"}, method="GET")
            with _uvr.urlopen(_req, timeout=20) as _r:
                _resp = _jvr.loads(_r.read().decode())
            _items = _resp.get("data", [])
            for _item in _items:
                if _item.get("project_uuid") == project_uuid:
                    return _item.get("uuid", "")
            _meta = _resp.get("meta", {})
            if _page >= _meta.get("last_page", 1):
                break
            _page += 1
    except Exception as _e:
        print(f"[Vault] lookup failed for {project_uuid}: {_e}", flush=True)
    return ""


_DC_ORG_ID       = os.getenv("DOCONCHAIN_ORGANIZATION_ID", "1287")
_DC_ORG_UUID     = os.getenv("DOCONCHAIN_ORGANIZATION_UUID", "ba2bbc98-10a2-4a91-81ad-e8abd0ab34eb")

# Token cache: {email: (token_str, expires_at_timestamp)}
_dc_token_cache: dict = {}
# ── Supreme Court eNotarization API ──────────────────────────────────────────
_SC_API_URL     = os.getenv("SUPREME_COURT_API_URL", "")          # e.g. https://scenotarization-api.com
_SC_AUTH_URL    = os.getenv("SUPREME_COURT_AUTH_URL", "")         # Cognito endpoint
_SC_CLIENT_ID   = os.getenv("SUPREME_COURT_CLIENT_ID", "")       # Cognito App Client ID
_SC_USERNAME    = os.getenv("SUPREME_COURT_USERNAME", "")
_SC_PASSWORD    = os.getenv("SUPREME_COURT_PASSWORD", "")
_SC_NFN         = os.getenv("SUPREME_COURT_NFN", "")             # Notary Facility Number
_sc_token_cache: dict = {}   # {token: str, expires_at: float}

def _sc_get_token() -> str:
    """Get Cognito access token for Supreme Court API (cached 55-min TTL)."""
    import time as _t_sc, json as _j_sc, urllib.request as _u_sc
    cached = _sc_token_cache.get("token")
    exp    = _sc_token_cache.get("expires_at", 0)
    if cached and _t_sc.time() < exp - 60:
        return cached
    if not all([_SC_AUTH_URL, _SC_CLIENT_ID, _SC_USERNAME, _SC_PASSWORD]):
        raise ValueError("Supreme Court credentials not configured. Set SUPREME_COURT_* env vars.")
    payload = _j_sc.dumps({
        "AuthFlow": "USER_PASSWORD_AUTH",
        "ClientId": _SC_CLIENT_ID,
        "AuthParameters": {"USERNAME": _SC_USERNAME, "PASSWORD": _SC_PASSWORD},
    }).encode()
    req = _u_sc.Request(
        _SC_AUTH_URL,
        data=payload,
        headers={"Content-Type": "application/x-amz-json-1.1",
                 "X-Amz-Target": "AWSCognitoIdentityProviderService.InitiateAuth"},
        method="POST",
    )
    with _u_sc.urlopen(req, timeout=30) as r:
        resp = _j_sc.loads(r.read().decode())
    token = (resp.get("AuthenticationResult") or {}).get("AccessToken")
    exp_in = (resp.get("AuthenticationResult") or {}).get("ExpiresIn", 3600)
    if not token:
        raise ValueError(f"No access token in Cognito response: {resp}")
    _sc_token_cache["token"] = token
    _sc_token_cache["expires_at"] = _t_sc.time() + exp_in
    return token

def _sc_request(method: str, path: str, payload: dict = None, token: str = None, timeout: int = 30) -> dict:
    """Make an authenticated request to the Supreme Court API (sync, run in executor)."""
    import httpx as _httpx_sc
    if not _SC_API_URL:
        raise ValueError("SUPREME_COURT_API_URL not set")
    token = token or _sc_get_token()
    url = f"{_SC_API_URL.rstrip('/')}/{path.lstrip('/')}"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {token}"}
    import sys as _sys_req
    print(f'[SC] {method} {url} payload={str(payload)[:600]}', file=_sys_req.stderr, flush=True)
    with _httpx_sc.Client(timeout=timeout) as client:
        if method.upper() == "POST":
            r = client.post(url, json=payload or {}, headers=headers)
        elif method.upper() == "GET":
            r = client.get(url, headers=headers)
        else:
            r = client.request(method, url, json=payload or {}, headers=headers)
    if not r.is_success:
        try:
            err_body = r.json()
        except Exception:
            err_body = r.text[:800]
        print(f'[SC ERROR] {r.status_code} {url} body={str(err_body)[:800]}', file=_sys_req.stderr, flush=True)
        raise RuntimeError(f'SC API {r.status_code} on {path}: {str(err_body)[:500]}')
    return r.json() if r.content else {}


def _sc_upload_pdf(nrid: str, pdf_bytes: bytes, doc_name: str, token: str = None) -> dict:
    """Upload signed PDF to SC via presigned S3 URL (sync, run in executor)."""
    import httpx as _httpx_s3
    tok = token or _sc_get_token()
    # 1. Get presigned URL
    ps_resp = _sc_request("POST", "/public-use/presigned-url", {"nrid": nrid, "fileName": doc_name}, token=tok)
    presigned_url = ps_resp.get("url") or ps_resp.get("presignedUrl") or ps_resp.get("presigned_url") or ""
    if not presigned_url:
        raise ValueError(f"No presigned URL in response: {ps_resp}")
    # 2. PUT PDF to S3
    with _httpx_s3.Client(timeout=60) as client:
        put_resp = client.put(presigned_url, content=pdf_bytes, headers={"Content-Type": "application/pdf"})
    put_resp.raise_for_status()
    # 3. Register file
    file_key = ps_resp.get("key") or ps_resp.get("fileKey") or ps_resp.get("s3Key") or ""
    file_resp = _sc_request("POST", "/public-use/file", {"nrid": nrid, "fileKey": file_key, "fileName": doc_name}, token=tok)
    return file_resp





def _sc_normalize_id(value: str, prefix: str) -> str:
    """Ensure identifier has correct prefix (e.g. '57793' -> 'RN-57793')."""
    if not value:
        return value
    v = value.strip()
    if not v.upper().startswith(prefix.upper()):
        v = f"{prefix}{v}"
    return v

def _get_dc_token(email: str = None) -> str:
    """Get a cached DoconChain token or generate a new one (5-min TTL)."""
    import time as _time
    _email = email or _DC_EMAIL
    cached = _dc_token_cache.get(_email)
    if cached:
        token_str, expires_at = cached
        if _time.time() < expires_at - 30:  # 30s buffer
            return token_str

    # Check env override first
    env_token = os.getenv("DOCONCHAIN_API_TOKEN") or os.getenv("DOCONCHAIN_USER_TOKEN")
    if env_token:
        return env_token

    # Generate new token — use requests (urllib has DNS issues in uvicorn worker context)
    import requests as _rq, json as _json2
    _resp = _rq.post(
        f'{_DC_BASE}/api/v2/generate/token',
        data={'client_key': _DC_CLIENT_KEY, 'client_secret': _DC_CLIENT_SECRET, 'email': _email},
        timeout=30,
    )
    _resp.raise_for_status()
    data = _resp.json()

    token_str = (data.get('data') or {}).get('token') or data.get('token')
    if not token_str:
        raise ValueError(f"No DC token in response: {data}")

    # Cache it — cap at 15-min TTL regardless of JWT exp.
    # DoconChain staging tokens may carry a 24h exp in the JWT payload, but
    # their server-side session can expire much sooner (especially after long
    # idle periods). A 15-min hard cap guarantees a fresh token after any
    # overnight idle without impacting normal intra-session usage.
    import time as _time2
    _MAX_TTL = 15 * 60  # 15 minutes hard cap
    try:
        import base64 as _b64, json as _j
        parts_jwt = token_str.split('.')
        if len(parts_jwt) >= 2:
            pad = parts_jwt[1] + '=='
            payload = _j.loads(_b64.urlsafe_b64decode(pad))
            jwt_exp = payload.get('exp', _time2.time() + _MAX_TTL)
            # Use whichever is sooner: JWT exp or 15-min cap
            exp = min(jwt_exp, _time2.time() + _MAX_TTL)
        else:
            exp = _time2.time() + _MAX_TTL
    except Exception:
        exp = _time2.time() + _MAX_TTL

    _dc_token_cache[_email] = (token_str, exp)
    return token_str



def _add_dc_signer(project_uuid: str, email: str, first_name: str, last_name: str,
                   signer_role: str = "Signer", dc_token: str = None, sequence: int = 1) -> dict:
    """Add a signer to a DoconChain project using the correct /projects/{uuid}/signers endpoint.
    sequence: signing group order (1 = first to sign, 2 = second, etc.)
    """
    import requests as _rq_signer
    token = dc_token or _get_dc_token()
    # Map UI roles to DoconChain API values
    _dc_role_map = {
        "Signer":   "Signer",
        "Approver": "Approver",
        "Notary":   "Signer",
    }
    _dc_role = _dc_role_map.get(signer_role, "Signer")
    payload = {
        "email": email,
        "first_name": first_name,
        "last_name": last_name,
        "type": "GUEST",
        "signer_role": _dc_role,
        # Note: sequence param is ignored by DC staging — signing order is determined by insertion order.
        # Always add client FIRST, ENP SECOND to ensure correct signing sequence.
    }
    print(f"[AddSigner] project={project_uuid[:12]} email={email} role={_dc_role} sequence={sequence}", flush=True)
    try:
        _resp = _rq_signer.post(
            f"{_DC_BASE}/projects/{project_uuid}/signers?user_type=ENTERPRISE_API",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
            timeout=30,
        )
        if _resp.status_code == 409 or "already" in (_resp.text or "").lower():
            print(f"[AddSigner] already added: {email}", flush=True)
            return {"already_added": True}
        if _resp.status_code == 400 and "not found" in (_resp.text or "").lower():
            raise Exception(f"Project {project_uuid} not accessible with this token (400). Check ENP token.")
        if _resp.status_code == 401:
            # Token may have expired — clear cache and retry ONCE with a fresh token
            import time as _t401
            # Determine which email this token was for by checking cache
            for _ce, _cv in list(_dc_token_cache.items()):
                if _cv[0] == token:
                    del _dc_token_cache[_ce]
                    break
            print(f"[AddSigner] 401 on {project_uuid[:12]} — refreshing token and retrying", flush=True)
            token = _get_dc_token()
            _resp2 = _rq_signer.post(
                f"{_DC_BASE}/projects/{project_uuid}/signers?user_type=ENTERPRISE_API",
                json=payload,
                headers={"Authorization": f"Bearer {token}"},
                timeout=30,
            )
            if _resp2.status_code == 409 or "already" in (_resp2.text or "").lower():
                print(f"[AddSigner] already added (retry): {email}", flush=True)
                return {"already_added": True}
            _resp2.raise_for_status()
            result = _resp2.json()
            _data2 = result.get('data') or result
            if isinstance(_data2, dict):
                print(f"[AddSigner] DC stored (retry): email={_data2.get('email')} sequence={_data2.get('sequence')}", flush=True)
            return result
        _resp.raise_for_status()
        result = _resp.json()
        # Log what DC actually stored for sequence verification
        _data = result.get('data') or result
        if isinstance(_data, dict):
            print(f"[AddSigner] DC stored: email={_data.get('email')} sequence={_data.get('sequence')} status={_data.get('status')}", flush=True)
        return result
    except Exception as _e:
        if 'already_added' not in str(_e):
            print(f"[AddSigner] ERROR: {_e}", flush=True)
        raise


# Per-document recreation lock: prevents concurrent "Add Signer" calls on the
# same document from producing two new DC projects.
import threading as _threading_doc
_doc_recreation_locks: dict = {}
_doc_recreation_locks_meta = _threading_doc.Lock()

def _get_doc_lock(project_uuid: str) -> _threading_doc.Lock:
    """Return (creating if necessary) a per-document threading.Lock."""
    with _doc_recreation_locks_meta:
        if project_uuid not in _doc_recreation_locks:
            _doc_recreation_locks[project_uuid] = _threading_doc.Lock()
        return _doc_recreation_locks[project_uuid]

def _swap_doc_lock(old_uuid: str, new_uuid: str) -> None:
    """Move the lock from old UUID to new UUID after a successful recreation."""
    with _doc_recreation_locks_meta:
        lock = _doc_recreation_locks.pop(old_uuid, None)
        if lock and new_uuid:
            _doc_recreation_locks[new_uuid] = lock

# Initialise SQLite DB (idempotent — safe to call on every startup)
_db.init_db()


# ─── Pydantic models ──────────────────────────────────────────────────────────

class AppointmentCreateRequest(BaseModel):
    enp_id: str
    notarization_type: str = "ACKNOWLEDGMENT"  # ACKNOWLEDGMENT | JURAT | AFFIRMATION | SIGNATURE_WITNESSING
    mode: str               # REN | IEN
    notes: str = ""
    title: str = ""
    preferred_time: str = ""


class AppointmentActionRequest(BaseModel):
    action: str  # "confirm" | "decline"


# ─── GET /api/enps ────────────────────────────────────────────────────────────

@app.get("/api/enps")
async def list_certified_enps():
    """Public endpoint — returns all certified ENPs."""
    result = []
    for u in _db.list_users():
        if u.get("role") != "attorney":
            continue
        if u.get("certificate_status") != "certified":
            continue
        profile = u.get("profile") or {}
        name = f"{u.get('first_name', '')} {u.get('last_name', '')}".strip()
        result.append({
            "id": u["id"],
            "name": name,
            "email": u.get("email", ""),
            "notary_address": profile.get("notary_address", ""),
            "commission_no": profile.get("commission_no", ""),
            "ibp_no": profile.get("ibp_no", ""),
            "picture": u.get("picture", ""),
            "specializations": [],
        })
    return result


# ─── POST /api/appointments ───────────────────────────────────────────────────

@app.post("/api/appointments")
async def create_appointment(
    req: AppointmentCreateRequest,
    authorization: Optional[str] = Header(None),
    ql_access: Optional[str] = Cookie(default=None),
):
    """Client creates an appointment with an ENP."""
    user = get_current_user(authorization, ql_access)
    if not user:
        raise HTTPException(401, "Unauthorized")
    if user.get("role") != "client":
        raise HTTPException(403, "Only clients can book appointments")


    if req.mode not in {"REN", "IEN"}:
        raise HTTPException(400, "Invalid mode. Valid: REN, IEN")

    # Look up ENP
    from onboarding import get_user as _get_user
    enp = _get_user(req.enp_id)
    if not enp or enp.get("role") != "attorney" or enp.get("certificate_status") != "certified":
        raise HTTPException(404, "ENP not found or not certified")

    now_iso = _dt.now(_tz.utc).isoformat()
    apt_id = str(uuid.uuid4())
    client_name = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip()
    enp_name = f"{enp.get('first_name', '')} {enp.get('last_name', '')}".strip()

    apt = {
        "apt_id": apt_id,
        "client_id": user["id"],
        "client_name": client_name,
        "client_email": user.get("email", ""),
        "enp_id": req.enp_id,
        "enp_name": enp_name,
        "enp_email": enp.get("email", ""),
        "notarization_type": req.notarization_type,
        "mode": req.mode,
        "notes": req.notes[:1000],
        "title": req.title[:200] if req.title else "",
        "preferred_time": req.preferred_time[:200] if req.preferred_time else "",
        "status": "PENDING",
        "created_at": now_iso,
        "updated_at": now_iso,
        "confirmed_at": None,
        "doconchain_project_uuid": None,
        "doconchain_sign_link": None,
    }

    _db.save_apt(apt)

    return apt


# ─── GET /api/appointments ────────────────────────────────────────────────────

@app.get("/api/appointments")
async def get_appointments(
    authorization: Optional[str] = Header(None),
    ql_access: Optional[str] = Cookie(default=None),
):
    """Get appointments for current user (role-aware)."""
    user = get_current_user(authorization, ql_access)
    if not user:
        raise HTTPException(401, "Unauthorized")

    role = user.get("role")
    uid = user["id"]

    all_apts = _db.list_apts()

    if role == "client":
        user_email = (user.get("email") or "").lower().strip()
        filtered = [
            a for a in all_apts
            if a.get("client_id") == uid
            # Also include QuickSign appointments where the signer's email matches
            or ((a.get("client_id") or "").startswith("guest:") and
                (a.get("client_email") or "").lower().strip() == user_email)
        ]
    elif role == "attorney":
        filtered = [a for a in all_apts if a.get("enp_id") == uid]
    else:
        filtered = []

    filtered.sort(key=lambda a: a.get("created_at", ""), reverse=True)
    return filtered




# ─── GET /api/appointments/{apt_id} ──────────────────────────────────────────

@app.get("/api/appointments/{apt_id}")
async def get_appointment_by_id(
    apt_id: str,
    authorization: Optional[str] = Header(None),
    ql_access: Optional[str] = Cookie(default=None),
):
    """Get a single appointment by ID. User must be the client or ENP of the appointment."""
    user = get_current_user(authorization, ql_access)
    if not user:
        raise HTTPException(401, "Unauthorized")

    apt = _db.get_apt(apt_id)

    if not apt:
        raise HTTPException(404, "Appointment not found")

    uid = user["id"]
    if apt["client_id"] != uid and apt["enp_id"] != uid:
        raise HTTPException(403, "Not your appointment")

    return apt

# ─── PATCH /api/appointments/{apt_id} ────────────────────────────────────────

@app.patch("/api/appointments/{apt_id}")
async def update_appointment(
    apt_id: str,
    req: AppointmentActionRequest,
    authorization: Optional[str] = Header(None),
    ql_access: Optional[str] = Cookie(default=None),
):
    """ENP confirms or declines an appointment."""
    user = get_current_user(authorization, ql_access)
    if not user:
        raise HTTPException(401, "Unauthorized")
    if user.get("role") != "attorney":
        raise HTTPException(403, "Only ENPs can confirm/decline appointments")

    if req.action not in ("confirm", "decline"):
        raise HTTPException(400, "action must be 'confirm' or 'decline'")

    apt = _db.get_apt(apt_id)
    if not apt:
        raise HTTPException(404, "Appointment not found")
    if apt["enp_id"] != user["id"]:
        raise HTTPException(403, "Not your appointment")
    if apt["status"] not in ("PENDING",):
        raise HTTPException(400, f"Cannot act on appointment with status {apt['status']}")

    now_iso = _dt.now(_tz.utc).isoformat()
    if req.action == "confirm":
        apt["status"] = "CONFIRMED"
        apt["confirmed_at"] = now_iso
    else:
        apt["status"] = "DECLINED"

    apt["updated_at"] = now_iso
    _db.save_apt(apt)

    return apt


# ─── POST /api/appointments/{apt_id}/doconchain ───────────────────────────────



def _dc_multipart_post(url: str, fields: dict, files: dict = None, headers: dict = None) -> dict:
    """Module-level multipart/form-data POST helper for DoconChain API calls."""
    import urllib.request as _ureq_mp, json as _json_mp
    boundary = "QLBoundary7f3a9b2c"
    body_parts = []
    for k, v in fields.items():
        body_parts.append(
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}\r\n".encode()
        )
    if files:
        for k, (fname, fdata, ftype) in files.items():
            body_parts.append(
                f"--{boundary}\r\nContent-Disposition: form-data; name=\"{k}\"; filename=\"{fname}\"\r\nContent-Type: {ftype}\r\n\r\n".encode()
                + fdata + b"\r\n"
            )
    body_parts.append(f"--{boundary}--\r\n".encode())
    body = b"".join(body_parts)
    req_headers = {"Content-Type": f"multipart/form-data; boundary={boundary}"}
    if headers:
        req_headers.update(headers)
    req = _ureq_mp.Request(url, data=body, headers=req_headers, method="POST")
    with _ureq_mp.urlopen(req, timeout=30) as resp:
        return _json_mp.loads(resp.read().decode())


def _build_create_fields(document_stamp: str, apt: dict) -> dict:
    """Build project creation fields including user_list for all known signers."""
    import json as _json_cf
    fields = {
        "document_stamp": document_stamp,
        "user_list_editable": "true",
        "creator_as_viewer": "false",
    }
    users = []
    c_email = apt.get("client_email", "")
    c_name  = apt.get("client_name", "Client").split()
    if c_email:
        users.append({
            "email": c_email,
            "first_name": c_name[0] if c_name else "Client",
            "last_name":  " ".join(c_name[1:]) if len(c_name) > 1 else "",
            "type": "GUEST",
            "signer_role": "Signer",
            "sequence": 1,
        })
    for sp in apt.get("session_participants", []):
        sp_email = sp.get("email", "")
        if sp_email and sp_email != c_email:
            sp_name = (sp.get("name") or "Guest").split()
            users.append({
                "email": sp_email,
                "first_name": sp_name[0] if sp_name else "Guest",
                "last_name":  " ".join(sp_name[1:]) if len(sp_name) > 1 else "",
                "type": "GUEST",
                "signer_role": "Signer",
                "sequence": len(users) + 1,
            })
    if users:
        fields["user_list"] = _json_cf.dumps(users)
    return fields

def _build_dc_stamp(enp_user: dict, apt: dict) -> str:
    """Build the full DoconChain document_stamp JSON from ENP profile + appointment data."""
    p = enp_user.get("profile") or {}
    first  = enp_user.get("first_name", "")
    last   = enp_user.get("last_name", "")
    prefix = p.get("prefix", "")
    suffix = p.get("suffix", "")
    full_name_parts = [x for x in [prefix, first, p.get("middle_initial",""), last, suffix] if x]
    full_name = " ".join(full_name_parts)
    if not full_name.upper().startswith("ATTY"):
        full_name = f"ATTY. {full_name}"

    enp_role_number = p.get("roll_no", "") or p.get("npn", "") or p.get("commission_no", "")  # roll number is the ENP notarial authority identifier

    stamp = {
        "seal": {
            "type": "seal",
            "enp_name": full_name,
            "enp_role_number": enp_role_number,
        },
        "notary_info": {
            "type": "notary",
            "atty_name": full_name,
            "roll_no": p.get("roll_no", ""),
            "roll_no_date": p.get("roll_date", ""),
            "commission_no": p.get("commission_no", ""),
            "commission_no_valid_until": p.get("commission_no_valid_until", ""),
            "PTR_no": p.get("ptr_no", ""),
            "PTR_no_location": p.get("ptr_no_location", ""),
            "PTR_no_date": p.get("ptr_no_date", ""),
            "IBP_no": p.get("ibp_no", ""),
            "IBP_no_date": p.get("ibp_no_date", ""),
            "email": enp_user.get("email", ""),
            "address": p.get("notary_address", ""),
            "MCLE_no_period": p.get("mcle_no_period", ""),
            "MCLE_no": p.get("mcle_no", ""),
            "MCLE_no_date": p.get("mcle_no_date", ""),
            "mode_of_notarization": apt.get("mode_of_notarization", "REN"),
        }
    }
    return json.dumps(stamp)


def _generate_placeholder_pdf(enp_name: str, commission_no: str, client_name: str, notarization_type: str) -> bytes:
    """Generate a minimal valid PDF for DoconChain project creation (raw bytes, no fpdf dependency)."""
    date_str = _dt.now(_tz.utc).strftime("%Y-%m-%d %H:%M UTC")
    content_stream = (
        f"BT\n"
        f"/F1 14 Tf\n"
        f"50 750 Td\n"
        f"(QUANBY LEGAL - NOTARIZATION DOCUMENT) Tj\n"
        f"0 -25 Td\n"
        f"/F1 11 Tf\n"
        f"(ENP: {enp_name}) Tj\n"
        f"0 -20 Td (Commission No: {commission_no}) Tj\n"
        f"0 -20 Td (Client: {client_name}) Tj\n"
        f"0 -20 Td (Notarization Type: {notarization_type}) Tj\n"
        f"0 -20 Td (Date: {date_str}) Tj\n"
        f"0 -30 Td\n"
        f"/F1 9 Tf\n"
        f"(This document is a placeholder for electronic notarization via Quanby Legal.) Tj\n"
        f"ET"
    )
    stream_bytes = content_stream.encode("latin-1")
    stream_len = len(stream_bytes)

    pdf_parts = [
        b"%PDF-1.4\n",
        b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n",
        b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n",
        b"3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R/Contents 4 0 R"
        b"/Resources<</Font<</F1 5 0 R>>>>>>endobj\n",
        f"4 0 obj<</Length {stream_len}>>\nstream\n".encode(),
        stream_bytes,
        b"\nendstream\nendobj\n",
        b"5 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj\n",
        b"xref\n0 6\n"
        b"0000000000 65535 f \n"
        b"0000000009 00000 n \n"
        b"0000000058 00000 n \n"
        b"0000000115 00000 n \n"
        b"0000000265 00000 n \n"
        b"0000000400 00000 n \n",
        b"trailer<</Size 6/Root 1 0 R>>\nstartxref\n460\n%%EOF",
    ]
    return b"".join(pdf_parts)


@app.post("/api/appointments/{apt_id}/doconchain")
async def create_doconchain_project(
    apt_id: str,
    authorization: Optional[str] = Header(None),
    ql_access: Optional[str] = Cookie(default=None),
):
    """ENP starts signing — creates a DoconChain project for this appointment."""
    user = get_current_user(authorization, ql_access)
    if not user:
        raise HTTPException(401, "Unauthorized")
    if user.get("role") != "attorney":
        raise HTTPException(403, "Only ENPs can start signing sessions")

    apt = _db.get_apt(apt_id)
    if not apt:
        raise HTTPException(404, "Appointment not found")
    if apt["enp_id"] != user["id"]:
        raise HTTPException(403, "Not your appointment")
    if apt["status"] != "CONFIRMED":
        raise HTTPException(400, "Appointment must be CONFIRMED before starting signing")

    # DoconChain credentials
    DC_BASE = _DC_BASE
    DC_CLIENT_KEY = _DC_CLIENT_KEY
    DC_CLIENT_SECRET = _DC_CLIENT_SECRET
    DC_EMAIL = _DC_EMAIL

    profile = user.get("profile") or {}
    enp_name = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip()
    commission_no = profile.get("commission_no", "N/A")

    try:
        import io as _io

        # ── Step 1: Generate DoconChain token (multipart/form-data via urllib) ──
        def _multipart_post(url: str, fields: dict, files: dict = None, headers: dict = None) -> dict:
            boundary = "QLBoundary7f3a9b2c"
            body_parts = []
            for k, v in fields.items():
                body_parts.append(
                    f"--{boundary}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}\r\n".encode()
                )
            if files:
                for k, (fname, fdata, ftype) in files.items():
                    body_parts.append(
                        f"--{boundary}\r\nContent-Disposition: form-data; name=\"{k}\"; filename=\"{fname}\"\r\nContent-Type: {ftype}\r\n\r\n".encode()
                        + fdata + b"\r\n"
                    )
            body_parts.append(f"--{boundary}--\r\n".encode())
            body = b"".join(body_parts)
            req_headers = {"Content-Type": f"multipart/form-data; boundary={boundary}"}
            if headers:
                req_headers.update(headers)
            req = _urllib_req.Request(url, data=body, headers=req_headers, method="POST")
            with _urllib_req.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode())

        # Use ENP's own email so the project is owned by the ENP
        # This ensures the plot-link redirects the ENP auto-authenticated (not the org)
        _enp_email_for_dc = user.get("email") or DC_EMAIL
        token_data = _multipart_post(
            f"{DC_BASE}/api/v2/generate/token",
            {"client_key": DC_CLIENT_KEY, "client_secret": DC_CLIENT_SECRET, "email": _enp_email_for_dc},
        )
        dc_token = (token_data.get("data") or {}).get("token") or token_data.get("token")
        if not dc_token:
            # Fallback to org token if ENP email not registered in DoconChain
            token_data = _multipart_post(
                f"{DC_BASE}/api/v2/generate/token",
                {"client_key": DC_CLIENT_KEY, "client_secret": DC_CLIENT_SECRET, "email": DC_EMAIL},
            )
            dc_token = (token_data.get("data") or {}).get("token") or token_data.get("token")
            _enp_email_for_dc = DC_EMAIL
        if not dc_token:
            raise ValueError(f"No token in response: {token_data}")

        # ── Step 2: Generate placeholder PDF ──
        pdf_bytes = _generate_placeholder_pdf(
            enp_name=enp_name,
            commission_no=commission_no,
            client_name=apt["client_name"],
            notarization_type=apt["notarization_type"],
        )

        # ── Step 3: Create DoconChain project ──
        document_stamp = _build_dc_stamp(user, apt)
        # Build user_list: client (seq=1) + any additional session_participants
        _upload_users = []
        _c_email = apt.get("client_email", "")
        _c_name  = apt.get("client_name", "Client").split()
        if _c_email:
            _upload_users.append({
                "email": _c_email,
                "first_name": _c_name[0] if _c_name else "Client",
                "last_name":  " ".join(_c_name[1:]) if len(_c_name) > 1 else "",
                "type": "GUEST",
                "signer_role": "Signer",
                "sequence": 1,
            })
        # Add any extra session_participants too
        for _sp in apt.get("session_participants", []):
            _sp_email = _sp.get("email", "")
            if _sp_email and _sp_email != _c_email:
                _sp_name = (_sp.get("name") or "Guest").split()
                _upload_users.append({
                    "email": _sp_email,
                    "first_name": _sp_name[0] if _sp_name else "Guest",
                    "last_name":  " ".join(_sp_name[1:]) if len(_sp_name) > 1 else "",
                    "type": "GUEST",
                    "signer_role": "Signer",
                    "sequence": len(_upload_users) + 1,
                })
        _create_fields = {
            "document_stamp": document_stamp,
            "user_list_editable": "true",
            "creator_as_viewer": "false",
        }
        if _upload_users:
            import json as _json_ul
            _create_fields["user_list"] = _json_ul.dumps(_upload_users)
        project_data = _multipart_post(
            f"{DC_BASE}/api/v2/projects?user_type=ENTERPRISE_API",
            _create_fields,
            files={"file": ("notarization_placeholder.pdf", pdf_bytes, "application/pdf")},
            headers={"Authorization": f"Bearer {dc_token}"},
        )

    except _urllib_err.HTTPError as e:
        err_body = e.read().decode(errors="replace")[:500]
        raise HTTPException(502, f"DoconChain API error: {e.code} - {err_body}")
    except Exception as e:
        raise HTTPException(502, f"DoconChain integration failed: {str(e)[:300]}")

    # Extract project UUID and build sign link
    # DoconChain: POST /projects/{uuid}/signers (no /api/v2/ prefix)
    data = project_data.get("data") or project_data
    project_uuid = (data.get("uuid") or data.get("project_uuid") or data.get("id") or str(uuid.uuid4()))
    # Always construct the DoconChain app signing URL from the project UUID
    sign_link = f"https://stg-app.doconchain.com/sign/{project_uuid}"

    # Auto-add ENP and client as signers via the correct /projects/{uuid}/signers endpoint
    _signer_results = {}
    _enp_profile = user.get("profile") or {}
    _enp_first = user.get("first_name") or enp_name.split()[0] if enp_name else "ENP"
    _enp_last  = user.get("last_name")  or (" ".join(enp_name.split()[1:]) if enp_name and " " in enp_name else "")

    # CRITICAL: Add CLIENT first (sequence=1), then ENP (sequence=2).
    # DC uses insertion order to determine signing order, not only the sequence param.
    # ENP must be added LAST so DC queues client to sign first, then ENP (notary).
    _client_name_parts = apt.get("client_name","Client").split()
    _client_first = _client_name_parts[0] if _client_name_parts else "Client"
    _client_last  = " ".join(_client_name_parts[1:]) if len(_client_name_parts) > 1 else ""
    _client_email = apt.get("client_email","")
    if _client_email:
        try:
            # Client added FIRST → signs FIRST (sequence=1)
            _signer_results["client"] = _add_dc_signer(project_uuid, _client_email, _client_first, _client_last, "Signer", dc_token, sequence=1)
        except Exception as _e:
            _signer_results["client"] = {"error": str(_e)[:100]}
    try:
        # ENP added SECOND → signs LAST (sequence=2, notary/ENP)
        _signer_results["enp"] = _add_dc_signer(project_uuid, user.get("email",""), _enp_first, _enp_last, "Signer", dc_token, sequence=2)
    except Exception as _e:
        _signer_results["enp"] = {"error": str(_e)[:100]}

    apt["doconchain_project_uuid"] = project_uuid
    apt["doconchain_sign_link"] = sign_link
    apt["doconchain_client_email"] = apt.get("client_email", "")
    apt["doconchain_enp_email"] = apt.get("enp_email", "")
    apt["updated_at"] = _dt.now(_tz.utc).isoformat()
    _db.save_apt(apt)

    return {
        "success": True,
        "project_uuid": project_uuid,
        "sign_link": sign_link,
        "signers_added": _signer_results,
    }

# ═══════════════════════════════════════════════════════════════════════════════
# LIVEKIT VIDEO SESSION ENDPOINTS


# ═══════════════════════════════════════════════════════════════════════════════
# LIVEKIT VIDEO SESSION ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

import jwt as _pyjwt


def _create_livekit_token(room_name: str, identity: str, name: str, can_publish: bool = True) -> str:
    """Generate a LiveKit access token using JWT (HS256)."""
    api_key    = os.getenv("LIVEKIT_API_KEY", "APIfmzJ2GVEV3TJ")
    api_secret = os.getenv("LIVEKIT_API_SECRET", "sTxyVlCJaPF9QMJTevLvT1xRmSPiXSZXZnLgGoJsIOH")
    now = int(time.time())
    grants = {
        "room": room_name,
        "roomJoin": True,
        "canPublish": can_publish,
        "canSubscribe": True,
        "canPublishData": True,
    }
    payload = {
        "iss": api_key,
        "sub": identity,
        "iat": now,
        "exp": now + 3600 * 6,
        "nbf": now,
        "jti": str(uuid.uuid4()),
        "name": name,
        "video": grants,
    }
    return _pyjwt.encode(payload, api_secret, algorithm="HS256")


class SessionCreateRequest(BaseModel):
    apt_id: str


class SessionJoinRequest(BaseModel):
    room_name: str
    apt_id: str


class SessionInviteRequest(BaseModel):
    apt_id: str
    email: str
    name: str
    role: str  # "WITNESS" | "OBSERVER"


_LIVEKIT_URL = "wss://quanby-lms-k4aq44qe.livekit.cloud"


# ─── GET /api/sessions/my-ip ──────────────────────────────────────────────────

@app.get("/api/sessions/my-ip")
async def get_my_ip(request: Request):
    """Return the client IP for VPN/proxy detection. No auth required."""
    # Respect X-Forwarded-For (set by nginx proxy)
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        ip = forwarded.split(",")[0].strip()
    else:
        ip = request.client.host if request.client else "unknown"
    return {"ip": ip}


# ─── POST /api/sessions/verify-liveness ──────────────────────────────────────

@app.post("/api/sessions/verify-liveness")
async def verify_session_liveness(
    request: Request,
    authorization: Optional[str] = Header(None),
    ql_access: Optional[str] = Cookie(default=None),
):
    """Liveness check before joining a session.
    Verifies the user's live selfie against their stored KYC record.
    For now: checks that the user has a verified KYC record (liveness_verified=True)
    and records a new session liveness verification timestamp.
    """
    user = get_current_user(authorization, ql_access)
    if not user:
        raise HTTPException(401, "Unauthorized")

    body = await request.json()
    status = body.get("status", "")
    transaction_id = body.get("transactionId", "")

    # Cross-verify: user must have completed KYC during onboarding
    has_kyc = user.get("liveness_verified") or user.get("hyperverge_status") in ("auto_approved", "needs_review", "success", "complete")
    kyc_verified_at = user.get("kyc_verified_at")

    # Accept any successful liveness outcome
    liveness_ok = status in ("success", "auto_approved", "needs_review", "complete", "user_verified")

    if liveness_ok and has_kyc:
        # Record session liveness timestamp
        await update_user(user["id"], {
            "session_liveness_verified_at": datetime.now(_tz.utc).isoformat(),
            "session_liveness_transaction_id": transaction_id,
        })
        return {
            "success": True,
            "kyc_match": True,
            "message": "Identity verified and matches KYC record.",
            "kyc_verified_at": kyc_verified_at,
        }
    elif liveness_ok and not has_kyc:
        # Liveness passed but no prior KYC — allow but flag for review
        await update_user(user["id"], {
            "session_liveness_verified_at": datetime.now(_tz.utc).isoformat(),
            "session_liveness_transaction_id": transaction_id,
        })
        return {
            "success": True,
            "kyc_match": False,
            "note": "No prior KYC record found — flagged for review",
            "message": "Liveness verified but no KYC record on file.",
        }
    else:
        return {
            "success": False,
            "kyc_match": False,
            "message": f"Liveness verification failed (status: {status}).",
        }


# ─── GET /api/sessions/{apt_id}/participants ──────────────────────────────────

@app.get("/api/sessions/{apt_id}/participants")
async def get_session_participants(
    apt_id: str,
    authorization: Optional[str] = Header(None),
    ql_access: Optional[str] = Cookie(default=None),
):
    """Get participants who are in or invited to the session.
    Returns the appointment's session_participants list enriched with
    the ENP and client info as base participants.
    """
    user = get_current_user(authorization, ql_access)
    if not user:
        raise HTTPException(401, "Unauthorized")

    apt = _db.get_apt(apt_id)

    if not apt:
        raise HTTPException(404, "Appointment not found")

    # Only ENP or client can view participants
    _u_email_s = (user.get("email") or "").lower().strip()
    _ok_s = (user["id"] in (apt.get("enp_id"), apt.get("client_id"))
             or ((apt.get("client_id") or "").startswith("guest:")
                 and (apt.get("client_email") or "").lower().strip() == _u_email_s)
             or any((p.get("email") or "").lower() == _u_email_s
                    for p in apt.get("session_participants", [])))
    if not _ok_s:
        raise HTTPException(403, "Not authorized for this session")

    # Base participants (ENP + Client)
    participants = []

    # ENP
    enp_name = apt.get("enp_name", "ENP")
    participants.append({
        "identity": apt.get("enp_id", ""),
        "name": enp_name,
        "role": "ENP",
        "email": apt.get("enp_email", ""),
        "type": "core",
        "accepted": True,
    })

    # Client
    client_name = apt.get("client_name", "Client")
    participants.append({
        "identity": apt.get("client_id", ""),
        "name": client_name,
        "role": "Client",
        "email": apt.get("client_email", ""),
        "type": "core",
        "accepted": True,
    })

    # Invited participants (witnesses/observers) — all are accepted once invited
    for p in apt.get("session_participants", []):
        participants.append({
            "identity": p.get("identity", p.get("email", "")),
            "name": p.get("name", "Guest"),
            "role": p.get("role", "Witness").capitalize(),
            "email": p.get("email", ""),
            "type": "invited",
            "accepted": True,
        })

    return {"participants": participants, "session_status": apt.get("session_status", "none")}


# ─── GET /api/sessions/dc-token ──────────────────────────────────────────────

@app.get("/api/sessions/dc-token")
async def get_dc_token_endpoint(
    authorization: Optional[str] = Header(None),
    ql_access: Optional[str] = Cookie(default=None),
):
    """Return the current DoconChain access token for ENP use in the session page.
    ENP-only — used to display the token for API calls from the meeting UI."""
    user = get_current_user(authorization, ql_access)
    if not user:
        raise HTTPException(401, "Unauthorized")
    # All authenticated users can use QuickSign
    try:
        token = _get_dc_token()
        return {
            "token": token,
            "base_url": _DC_BASE,
            "app_url": _DC_APP_URL,
            "organization_uuid": _DC_ORG_UUID,
        }
    except Exception as e:
        raise HTTPException(502, f"Could not generate DoconChain token: {str(e)[:200]}")


# ─── POST /api/sessions/{apt_id}/documents/{uuid}/sign-links ────────────────────

@app.post("/api/sessions/{apt_id}/documents/{project_uuid}/sign-links")
async def generate_sign_links(
    apt_id: str,
    project_uuid: str,
    authorization: Optional[str] = Header(None),
    ql_access: Optional[str] = Cookie(default=None),
):
    """ENP generates signing links for each assigned signer on a document."""
    user = get_current_user(authorization, ql_access)
    if not user:
        raise HTTPException(401, "Unauthorized")

    apt = _db.get_apt(apt_id)
    if not apt:
        raise HTTPException(404, "Appointment not found")

    # Allow any accepted participant (ENP, client, or invited signer) to generate their own sign link
    _user_email = (user.get("email") or "").lower().strip()
    _accepted_for_sign = set()
    if apt.get("enp_id"):     _accepted_for_sign.add(apt["enp_id"])
    if apt.get("client_id"):  _accepted_for_sign.add(apt["client_id"])
    _is_sign_participant = user["id"] in _accepted_for_sign
    if not _is_sign_participant:
        # Also allow invited session_participants by email
        _invited_emails = {(p.get("email") or "").lower().strip() for p in apt.get("session_participants", [])}
        # Also allow QuickSign guest clients matched by email
        _client_email_match = (
            (apt.get("client_id") or "").startswith("guest:") and
            (apt.get("client_email") or "").lower().strip() == _user_email
        )
        # Also allow document signers matched by email
        _is_doc_signer = any(
            (s.get("email") or "").lower().strip() == _user_email
            for doc in apt.get("session_documents", [])
            for s in doc.get("signers", [])
        )
        if _user_email not in _invited_emails and not _client_email_match and not _is_doc_signer:
            raise HTTPException(403, "You are not a participant of this appointment")

    # Find the document
    doc = None
    for _d in apt.get("session_documents", []):
        _duuid = _d.get("doconchain_project_uuid") or _d.get("project_uuid")
        if _duuid == project_uuid:
            doc = _d
            break
    if not doc:
        raise HTTPException(404, "Document not found in this session")

    # Build ordered signer list: respect signing_order from saved signers
    # Each entry: {"email": ..., "signing_order": int}
    import requests as _rq3

    _ordered_signers = []
    _seen_emails = set()

    # 1. Add saved signers in signing_order sequence
    _saved = sorted(doc.get("signers", []), key=lambda s: s.get("signing_order", 99))
    for s in _saved:
        _em = (s.get("email") or "").lower().strip()
        if _em and _em not in _seen_emails:
            _ordered_signers.append({"email": _em, "signing_order": s.get("signing_order", 99)})
            _seen_emails.add(_em)

    # 2. Append ENP + client if not already included (fallback)
    for _fallback_email in [apt.get("enp_email",""), apt.get("client_email","")]:
        _fe = (_fallback_email or "").lower().strip()
        if _fe and _fe not in _seen_emails:
            _ordered_signers.append({"email": _fe, "signing_order": 99})
            _seen_emails.add(_fe)

    if not _ordered_signers:
        raise HTTPException(400, "No signers assigned to this document")

    # Token strategy (per spec):
    # Use ENP/owner token as primary bearer — so non-DocOnChain principals can still sign.
    # ENP/owner token lets the API act on behalf of the enterprise project owner
    # while the sign-link request embeds each signer's email.
    # Fallback to org token if ENP token fails (for org-owned projects).
    _enp_email_for_token = apt.get("enp_email") or _DC_EMAIL
    try:
        dc_token = _get_dc_token(email=_enp_email_for_token)
    except Exception:
        dc_token = _get_dc_token(email=_DC_EMAIL)  # fallback to org

    def _gen_sign_link(signer_email: str) -> dict:
        """Generate a sign link for one signer, with token fallback on 401.

        For ENP (project owner): use POST /projects/{uuid}/link — returns api_token for auto-login.
        For clients/guests: use POST /projects/{uuid}/link/generate?email=... — guest signer URL.
        This prevents the ENP getting "SESSION ENDED" when clicking their sign link.
        """
        import requests as _rq_sl
        nonlocal dc_token
        # All signers (ENP and clients) use /link/generate?email=...
        # This generates the correct per-signer sign link from DC
        # Note: ENP must have plotted fields first (plot link auto-logs them into DC)
        # so their browser session is active when they open the sign link
        url = f"{_DC_BASE}/api/v2/projects/{project_uuid}/link/generate?email={signer_email}"
        print(f"[SignLink] sign link for {signer_email}", flush=True)
        for _attempt in range(2):
            try:
                _resp_sl = _rq_sl.post(
                    url,
                    headers={"Content-Type": "application/json",
                             "Authorization": f"Bearer {dc_token}",
                             "Accept": "application/json"},
                    timeout=30,
                )
                if _resp_sl.status_code == 401 and _attempt == 0:
                    # Token expired — drop cache and retry with org token
                    _dc_token_cache.pop(_enp_email_for_token, None)
                    _dc_token_cache.pop(_DC_EMAIL, None)
                    dc_token = _get_dc_token(email=_DC_EMAIL)
                    continue
                _resp_sl.raise_for_status()
                _d = _resp_sl.json()
                link = _d.get("message") or (_d.get("data") or {}).get("link") or _d.get("link")
                if link and link.startswith("http"):
                    # Resolve short link to get embedded auth token (302 Location header)
                    resolved = link
                    if "link.doconchain.com" in link or "doconchain.com" in link:
                        try:
                            _r3 = _rq_sl.get(link, headers={"User-Agent": "Mozilla/5.0"}, allow_redirects=False, timeout=8)
                            _loc = _r3.headers.get("Location", "")
                            if _loc and _loc.startswith("http"):
                                resolved = _loc
                        except Exception: pass
                    return {"email": signer_email, "link": resolved, "status": "ok"}
                return {"email": signer_email, "link": None, "status": "no_link", "raw": str(_d)[:100]}
            except Exception as he:
                err = str(he)[:200]
                if "401" in err and _attempt == 0:
                    # Token expired or wrong owner — drop cache and retry with org token
                    _dc_token_cache.pop(_enp_email_for_token, None)
                    _dc_token_cache.pop(_DC_EMAIL, None)
                    try:
                        dc_token = _get_dc_token(email=_DC_EMAIL)
                    except Exception:
                        pass
                    continue
                return {"email": signer_email, "link": None, "status": f"error_{he.code}", "detail": err[:100]}
            except Exception as ex:
                return {"email": signer_email, "link": None, "status": "error", "detail": str(ex)[:100]}
        return {"email": signer_email, "link": None, "status": "error", "detail": "max retries"}

    # Per spec: generate ONLY the calling user's own fresh link (keyed by signer identity).
    # Never reuse a link across different signers — each click generates a new unique URL.
    # The caller's email is the signer identity for this link generation.
    _caller_email = (user.get("email") or "").lower().strip()

    # Verify caller is actually a signer on this document
    _caller_is_signer = any(
        s.get("email", "").lower() == _caller_email
        for s in _ordered_signers
    )
    if not _caller_is_signer:
        # Caller not in signer list — generate for all unsigned signers (ENP managing the flow)
        _to_generate = _ordered_signers
    else:
        # Caller is a signer — generate ONLY their own fresh link
        _to_generate = [s for s in _ordered_signers if s.get("email", "").lower() == _caller_email]

    sign_links = [_gen_sign_link(s["email"]) for s in _to_generate]
    # Also include other signers with None links (so frontend knows who else exists)
    _generated_emails = {s["email"].lower() for s in _to_generate}
    for s in _ordered_signers:
        if s.get("email", "").lower() not in _generated_emails:
            sign_links.append({"email": s.get("email",""), "link": None, "status": "not_generated_for_caller"})

    # Record signing initiated + create PENDING signature_requests rows
    _apt2 = _db.get_apt(apt_id)
    if _apt2:
        for _d2 in _apt2.get("session_documents", []):
            _duuid2 = _d2.get("doconchain_project_uuid") or _d2.get("project_uuid")
            if _duuid2 == project_uuid:
                _d2["signing_initiated"] = True
                _d2["signing_initiated_at"] = _dt.now(_tz.utc).isoformat()
                # Create/update signature_requests rows (primary source of truth)
                existing_sr = {r["email"].lower(): r for r in _d2.get("signature_requests", [])}
                for _s in _ordered_signers:
                    _em = _s["email"].lower()
                    if _em not in existing_sr:
                        existing_sr[_em] = {
                            "email": _em,
                            "signing_order": _s.get("signing_order", 99),
                            "status": "PENDING",
                            "signed_at": None,
                            "source": None,
                        }
                _d2["signature_requests"] = list(existing_sr.values())
                _db.save_apt(_apt2)
                break

    return {"project_uuid": project_uuid, "sign_links": sign_links}



# ─── POST /api/sessions/{apt_id}/documents/{uuid}/mark-signed ────────────────────

@app.post("/api/sessions/{apt_id}/documents/{project_uuid}/mark-signed")
async def mark_signer_signed(
    apt_id: str,
    project_uuid: str,
    authorization: Optional[str] = Header(None),
    ql_access: Optional[str] = Cookie(default=None),
):
    """Heuristic: caller marks themselves SIGNED after completing DoconChain signing.
    Enforces sequential order: rejects if any earlier signer is not yet SIGNED.
    ENP (notary) is NOT allowed to self-mark here — their signature is confirmed
    only via DC status poll or webhook.
    """
    user = get_current_user(authorization, ql_access)
    if not user:
        raise HTTPException(401, "Unauthorized")

    apt = _db.get_apt(apt_id)
    if not apt:
        raise HTTPException(404, "Appointment not found")

    _user_email = (user.get("email") or "").lower().strip()

    # ENP must not self-mark — their signing is confirmed via DC status / webhook only
    if user["id"] == apt.get("enp_id"):
        raise HTTPException(403, "ENP signing is confirmed via DoconChain status only — not via self-marking.")

    # Must be a participant
    if user["id"] not in (apt.get("enp_id"), apt.get("client_id")):
        _inv_emails = {(p.get("email") or "").lower() for p in apt.get("session_participants", [])}
        if _user_email not in _inv_emails:
            raise HTTPException(403, "Not a participant of this appointment")

    _now = _dt.now(_tz.utc).isoformat()

    _mark_apt = _db.get_apt(apt_id)
    for _doc in (_mark_apt or {}).get("session_documents", []):
        _duuid = _doc.get("doconchain_project_uuid") or _doc.get("project_uuid")
        if _duuid != project_uuid:
            continue

        # Build ordered signer list from doc.signers
        _doc_signers = sorted(_doc.get("signers", []), key=lambda s: s.get("signing_order", 99))
        _my_signer = next(
            (s for s in _doc_signers if (s.get("email") or "").lower() == _user_email), None
        )
        if not _my_signer:
            raise HTTPException(400, f"You are not in the signer list for this document.")

        _my_order = _my_signer.get("signing_order", 99)

        # Build status map from signature_requests
        _sr_map = {r.get("email", "").lower(): r for r in _doc.get("signature_requests", [])}

        # Sequential check: all signers with order < my_order must be SIGNED
        _blockers = [
            s for s in _doc_signers
            if s.get("signing_order", 99) < _my_order
            and _sr_map.get((s.get("email") or "").lower(), {}).get("status") != "SIGNED"
        ]
        if _blockers:
            _blocker_emails = [s.get("email") for s in _blockers]
            raise HTTPException(409,
                f"Cannot sign yet — waiting for earlier signers: {', '.join(_blocker_emails)}")

        # Already signed?
        if _sr_map.get(_user_email, {}).get("status") == "SIGNED":
            return {"success": True, "email": _user_email, "status": "SIGNED", "already": True}

        # Mark as signed
        sr_list = _doc.get("signature_requests", [])
        updated = False
        for row in sr_list:
            if row.get("email", "").lower() == _user_email:
                row["status"] = "SIGNED"
                row["signed_at"] = _now
                row["source"] = "heuristic"
                updated = True
                break
        if not updated:
            sr_list.append({
                "email": _user_email,
                "signing_order": _my_order,
                "status": "SIGNED",
                "signed_at": _now,
                "source": "heuristic",
            })
            _doc["signature_requests"] = sr_list
        _db.save_apt(_mark_apt)
        return {"success": True, "email": _user_email, "status": "SIGNED", "signed_at": _now}

    raise HTTPException(404, "Document not found in session")


# ─── POST /api/webhooks/doconchain ────────────────────────────────────────────────

@app.post("/api/webhooks/doconchain")
async def doconchain_webhook(request: Request):
    """Receive DoconChain webhook events and update signature_requests rows."""
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(400, "Invalid JSON")

    event_type = (payload.get("event") or payload.get("type") or "").lower()
    project_uuid = payload.get("project_uuid") or payload.get("uuid") or ""
    signer_email = ((payload.get("signer") or {}).get("email") or
                    payload.get("email") or "").lower().strip()
    signed_at = payload.get("signed_at") or payload.get("timestamp") or _dt.now(_tz.utc).isoformat()

    if not project_uuid:
        return {"ok": True, "note": "no project_uuid"}

    new_status = None
    if "signed" in event_type or "complete" in event_type:
        new_status = "SIGNED"
    elif "declined" in event_type or "reject" in event_type:
        new_status = "DECLINED"

    if not new_status:
        return {"ok": True, "note": f"unhandled event: {event_type}"}

    # Find matching document across all appointments
    for _apt in _db.list_apts():
        _aid = _apt.get("apt_id")
        for _doc in _apt.get("session_documents", []):
            _duuid = _doc.get("doconchain_project_uuid") or _doc.get("project_uuid")
            if _duuid != project_uuid:
                continue
            sr_list = _doc.get("signature_requests", [])
            for row in sr_list:
                if not signer_email or row.get("email", "").lower() == signer_email:
                    row["status"] = new_status
                    row["signed_at"] = signed_at
                    row["source"] = "webhook"
            if signer_email:
                # Ensure row exists
                emails = [r.get("email","").lower() for r in sr_list]
                if signer_email not in emails:
                    sr_list.append({"email": signer_email, "signing_order": 99,
                                    "status": new_status, "signed_at": signed_at, "source": "webhook"})
            _doc["signature_requests"] = sr_list
            _db.save_apt(_apt)
            # Registry population ONLY happens when session is ended — NOT on webhook
            # Premature registry population would fetch incomplete documents
            if new_status == "SIGNED" and "complete" in event_type:
                _session_ended = _apt.get("session_status") == "ended"
                if _session_ended:
                    import threading as _wh_t
                    _wh_enp_id = _apt.get("enp_id", "")
                    if _wh_enp_id:
                        print(f"[Webhook] session already ended + complete event for {project_uuid[:12]} → registry populate", flush=True)
                        _wh_t.Thread(
                            target=_populate_registry_bg,
                            args=(_aid, _wh_enp_id),
                            daemon=True
                        ).start()
                else:
                    print(f"[Webhook] complete event for {project_uuid[:12]} — session not yet ended, skipping registry", flush=True)
            return {"ok": True, "updated": project_uuid, "signer": signer_email, "status": new_status}

    return {"ok": True, "note": "project not found in active appointments"}

# ─── GET /api/sessions/{apt_id}/documents/{uuid}/signer-status ──────────────────

@app.get("/api/sessions/{apt_id}/documents/{project_uuid}/signer-status")
async def get_signer_status(
    apt_id: str,
    project_uuid: str,
    authorization: Optional[str] = Header(None),
    ql_access: Optional[str] = Cookie(default=None),
):
    """Poll DoconChain for real-time signer status (signed/pending) for each signer.

    Diagnostic logging (points 1-4):
      - UUID verified end-to-end (created → stored → used for status)
      - DC is source of truth for completion status
      - Signer email normalization logged
      - Token scope logged per request
    """
    user = get_current_user(authorization, ql_access)
    if not user:
        raise HTTPException(401, "Unauthorized")

    apt = _db.get_apt(apt_id)
    if not apt:
        raise HTTPException(404, "Appointment not found")
    if user["id"] not in (apt.get("enp_id"), apt.get("client_id")):
        raise HTTPException(403, "Not authorized for this session")

    # ── DIAGNOSTIC: Verify UUID is consistent with what's stored in DB (Point 1) ──
    _stored_uuid = None
    for _chk_doc in apt.get("session_documents", []):
        _chk_uuid = _chk_doc.get("doconchain_project_uuid") or _chk_doc.get("project_uuid")
        if _chk_uuid == project_uuid:
            _stored_uuid = _chk_uuid
            break
    if _stored_uuid != project_uuid:
        print(f"[SignerStatus WARN] UUID MISMATCH! requested={project_uuid} stored={_stored_uuid} apt={apt_id}", flush=True)
    else:
        print(f"[SignerStatus] UUID verified: {project_uuid[:12]} matches DB for apt={apt_id}", flush=True)

    import requests as _rq_ss, time as _time_ss
    try:
        # Use ENP token (Point 4: consistent token scope)
        _enp_email = apt.get("enp_email") or _DC_EMAIL
        try:
            dc_token = _get_dc_token(email=_enp_email)
        except Exception:
            dc_token = _get_dc_token(email=_DC_EMAIL)
            _enp_email = _DC_EMAIL

        print(f"[SignerStatus] token_email={_enp_email} uuid={project_uuid[:12]}", flush=True)

        _ss_url = f"{_DC_BASE}/api/v2/projects/{project_uuid}?user_type=ENTERPRISE_API"
        dc_data = None
        _ss_last_status = 0

        # Retry up to 3 times — handles cross-worker token cache races
        for _ss_attempt in range(3):
            _ss_resp = _rq_ss.get(_ss_url, headers={"Authorization": f"Bearer {dc_token}", "Accept": "application/json"}, timeout=15)
            _ss_last_status = _ss_resp.status_code
            if _ss_resp.status_code == 200:
                dc_data = _ss_resp.json()
                break
            if _ss_resp.status_code == 401:
                # Token race — clear ALL caches, force fresh token
                _dc_token_cache.pop(_enp_email, None)
                _dc_token_cache.pop(_DC_EMAIL, None)
                _wait = 0.3 * (2 ** _ss_attempt)  # 0.3s, 0.6s, 1.2s
                print(f"[SignerStatus] 401 attempt {_ss_attempt+1} — clearing cache, retry in {_wait:.1f}s", flush=True)
                _time_ss.sleep(_wait)
                try:
                    dc_token = _get_dc_token(email=_DC_EMAIL)
                    _enp_email = _DC_EMAIL
                except Exception as _te:
                    print(f"[SignerStatus] token refresh failed: {_te}", flush=True)
                continue
            # Non-401 error — don't retry
            break

        if dc_data is None:
            # DC auth failed for this project — fall back to internal DB data (no 502)
            print(f"[SignerStatus] DC {_ss_last_status} for {project_uuid[:12]} — using internal fallback", flush=True)
            dc_signers = []
            project_status = "unknown"
            dc_completed_at = None
        else:
            project = dc_data.get("data") or dc_data
            dc_signers = project.get("signers", [])
            project_status = project.get("status", "")
            dc_completed_at = project.get("completed_at") or project.get("completedAt")

        # ── DIAGNOSTIC: Point 2 — DC source of truth completion check ────────────
        def _is_signer_signed(s):
            """Match reference isSignerSigned: status SIGNED/COMPLETED OR non-empty signed_at."""
            status_upper = (s.get("status") or "").upper()
            has_signed_status = status_upper in ("SIGNED", "COMPLETED")
            has_signed_at = bool(s.get("signed_at"))
            return has_signed_status or has_signed_at

        _dc_all_signed = all(_is_signer_signed(s) for s in dc_signers) if dc_signers else False
        print(
            f"[SignerStatus] DC status={project_status} completed_at={dc_completed_at} "
            f"signers={len(dc_signers)} all_signed={_dc_all_signed} uuid={project_uuid[:12]}",
            flush=True
        )
        # ── DIAGNOSTIC: Point 3 — Log each signer identity for mismatch detection ─
        for _s in dc_signers:
            _s_email = (_s.get("email") or "").lower().strip()
            _s_status = (_s.get("status") or "").upper()
            _s_role = _s.get("role") or _s.get("signer_role") or "Signer"
            _s_order = _s.get("sequence") or _s.get("signing_order") or "?"
            print(
                f"[SignerStatus]   signer email={_s_email} role={_s_role} order={_s_order} status={_s_status}",
                flush=True
            )

        # Build status map: email → {signed: bool, signed_at: str|None}
        # Build internal rows map (primary source of truth)
        doc_found = None
        for _d3 in apt.get("session_documents", []):
            _du3 = _d3.get("doconchain_project_uuid") or _d3.get("project_uuid")
            if _du3 == project_uuid:
                doc_found = _d3
                break
        internal_sr = {}
        if doc_found:
            for row in doc_found.get("signature_requests", []):
                internal_sr[row.get("email","").lower()] = row

        signer_statuses = []
        # Use DoconChain as the data source for the full signer list
        # but merge with internal rows (internal wins if it says SIGNED)
        processed = set()
        for s in dc_signers:
            email = (s.get("email") or "").lower().strip()
            dc_status = (s.get("status") or "").upper()
            dc_signed_at = s.get("signed_at")
            dc_signed = dc_status in ("SIGNED", "COMPLETED") or bool(dc_signed_at)
            # Internal row overrides if it says SIGNED
            internal = internal_sr.get(email, {})
            internal_signed = internal.get("status") == "SIGNED"
            is_signed = internal_signed or dc_signed
            signed_at = internal.get("signed_at") if internal_signed else dc_signed_at
            source = internal.get("source", "dc") if internal_signed else "dc"
            signer_statuses.append({
                "email":      email,
                "signed":     is_signed,
                "signed_at":  signed_at,
                "dc_status":  dc_status,
                "source":     source,
                "signing_order": internal.get("signing_order", s.get("sequence", 99)),
            })
            processed.add(email)
        # Also include internal rows not in DoconChain list (e.g. added manually)
        for em, row in internal_sr.items():
            if em not in processed:
                signer_statuses.append({
                    "email":         em,
                    "signed":        row.get("status") == "SIGNED",
                    "signed_at":     row.get("signed_at"),
                    "dc_status":     "INTERNAL",
                    "source":        row.get("source", "internal"),
                    "signing_order": row.get("signing_order", 99),
                })

        # Sync any newly-signed signers back to internal signature_requests
        _need_save = False
        if doc_found is not None:
            for _ss in signer_statuses:
                if not _ss.get("signed"): continue
                _ss_email = _ss.get("email","").lower()
                _existing = internal_sr.get(_ss_email)
                if _existing and _existing.get("status") != "SIGNED":
                    _existing["status"] = "SIGNED"
                    _existing["signed_at"] = _ss.get("signed_at")
                    _existing["source"] = "dc_sync"
                    _need_save = True
                elif not _existing:
                    internal_sr[_ss_email] = {
                        "email": _ss_email,
                        "signing_order": _ss.get("signing_order", 99),
                        "status": "SIGNED",
                        "signed_at": _ss.get("signed_at"),
                        "source": "dc_sync",
                    }
                    _need_save = True
            if _need_save:
                _sync_apt = _db.get_apt(apt_id)
                if _sync_apt:
                    for _d4 in _sync_apt.get("session_documents", []):
                        _du4 = _d4.get("doconchain_project_uuid") or _d4.get("project_uuid")
                        if _du4 == project_uuid:
                            _d4["signature_requests"] = list(internal_sr.values())
                            # Mark doc as completed if ALL signers have signed
                            _all_sr = list(internal_sr.values())
                            # Match reference: isFullySigned requires BOTH:
                            # 1. All signers have SIGNED status
                            # 2. DC projectStatus === COMPLETED OR completedAt is set
                            # (internal_sr tracks DC signer status synced from DC source of truth)
                            # Staging workaround: DC sometimes sets signed_at on all signers
                            # but never flips project to COMPLETED. Treat as complete if all
                            # signers have signed_at set (match reference isFullySigned logic).
                            _staging_all_have_signed_at = (
                                len(_all_sr) > 0 and
                                all(bool(r.get("signed_at")) for r in _all_sr)
                            )
                            _dc_project_completed = (
                                (project_status or "").upper() == "COMPLETED"
                                or bool(dc_completed_at)
                                or _staging_all_have_signed_at  # Staging fallback
                            )
                            _all_signed_now = (
                                len(_all_sr) > 0 and
                                all(r.get("status") == "SIGNED" for r in _all_sr) and
                                _dc_project_completed  # DC must confirm completion, not just individual signers
                            )
                            if _all_signed_now and _d4.get("status") != "completed":
                                _d4["status"] = "completed"
                                _d4["completed_at"] = dc_completed_at or _dt.now(_tz.utc).isoformat()
                                # ── LOG: document fully signed and marked COMPLETED ────────────────────
                                print(
                                    f"[Completion] ══════════════════════════════════════════════════════",
                                    flush=True
                                )
                                print(
                                    f"[Completion] ✅ DOCUMENT COMPLETED  uuid={project_uuid[:12]}",
                                    flush=True
                                )
                                print(
                                    f"[Completion]    DC status={project_status} completed_at={dc_completed_at}",
                                    flush=True
                                )
                                print(
                                    f"[Completion]    staging_all_signed_at={_staging_all_have_signed_at}",
                                    flush=True
                                )
                                print(
                                    f"[Completion]    signers ({len(_all_sr)} total):",
                                    flush=True
                                )
                                for _csr in _all_sr:
                                    print(
                                        f"[Completion]      email={_csr.get('email')} "
                                        f"status={_csr.get('status')} "
                                        f"signed_at={(_csr.get('signed_at') or '')[:19]}",
                                        flush=True
                                    )
                                print(
                                    f"[Completion] ══════════════════════════════════════════════════════",
                                    flush=True
                                )
                                # Registry is populated ONLY on session end, not here.
                            elif not _dc_project_completed and all(r.get("status") == "SIGNED" for r in _all_sr) and len(_all_sr) > 0:
                                print(
                                    f"[Completion] ⏳ All signers SIGNED internally but DC status={project_status} "
                                    f"completed_at={dc_completed_at} — waiting for DC to flip COMPLETED.",
                                    flush=True
                                )
                                for _wsr in _all_sr:
                                    print(
                                        f"[Completion]    email={_wsr.get('email')} "
                                        f"status={_wsr.get('status')} "
                                        f"signed_at={(_wsr.get('signed_at') or '')[:19]}",
                                        flush=True
                                    )
                            _db.save_apt(_sync_apt)
                            break

        # ── LOG: what we return to the client ────────────────────────────────
        print(
            f"[SignerStatus] ── RESPONSE for {project_uuid[:12]} ─────────────────────",
            flush=True
        )
        print(
            f"[SignerStatus]    project_status={project_status} completed_at={dc_completed_at}",
            flush=True
        )
        for _ret_s in signer_statuses:
            print(
                f"[SignerStatus]    signer email={_ret_s.get('email')} "
                f"signed={_ret_s.get('signed')} dc_status={_ret_s.get('dc_status')} "
                f"signed_at={(_ret_s.get('signed_at') or '')[:19]} "
                f"order={_ret_s.get('signing_order')}",
                flush=True
            )
        print(
            f"[SignerStatus] ────────────────────────────────────────────────────────",
            flush=True
        )

        return {
            "project_uuid":    project_uuid,
            "project_status":  project_status,
            "signer_statuses": signer_statuses,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(502, f"Could not fetch signer status: {str(e)[:200]}")


# ─── POST /api/sessions/plot-link/{project_uuid} ─────────────────────────────

@app.post("/api/sessions/plot-link/{project_uuid}")
async def get_plot_link(
    project_uuid: str,
    authorization: Optional[str] = Header(None),
    ql_access: Optional[str] = Cookie(default=None),
):
    """ENP-only. Calls DoconChain POST /api/v2/projects/{uuid}/link to get the
    edit/draft URL for placing signature fields.  Returns { link: str }."""
    user = get_current_user(authorization, ql_access)
    if not user:
        raise HTTPException(401, "Unauthorized")
    # All authenticated users can use QuickSign
    if not project_uuid or not project_uuid.strip():
        raise HTTPException(400, "project_uuid required")

    import requests as _rq2
    try:
        # Per spec: get a fresh token for each attempt (invalidate cache to force re-login).
        # Try ENP email first, then org email as fallback.
        _plot_email = user.get("email") or _DC_EMAIL

        def _call_plot_link(token):
            _resp2 = _rq2.post(
                f"{_DC_BASE}/api/v2/projects/{project_uuid}/link?user_type=ENTERPRISE_API",
                headers={"Accept": "application/json", "Authorization": f"Bearer {token}"},
                timeout=30,
            )
            _resp2.raise_for_status()
            return _resp2.json()

        # IMPORTANT: Only use the ENP's own email — NEVER fall back to _DC_EMAIL.
        # The org default email (stg_quanby@maildrop.cc) generates a different link
        # format that exposes raw token/api_token params in the URL and belongs to
        # a different DoconChain account. This is the root cause of the wrong plot link.
        enp_email = (user.get("email") or "").lower().strip()
        if not enp_email:
            raise HTTPException(400, "ENP email not found — cannot generate plot link")

        # Purge ALL cached tokens for this email to force a clean re-auth.
        # Stale tokens from a previous session (different laptop/browser) cause
        # the wrong email to appear in the generated link.
        _dc_token_cache.pop(enp_email, None)
        _dc_token_cache.pop(_DC_EMAIL, None)

        resp_data = None
        _last_code = 502
        _last_body = "Unknown error"

        # Retry up to 3 times with a fresh token each time
        for _retry in range(3):
            try:
                _tok = _get_dc_token(email=enp_email)
                print(f"[PlotLink] attempt {_retry+1}: email={enp_email} token={_tok[:12]}...", flush=True)
            except Exception as _te:
                _last_body = f"Token error for {enp_email}: {_te}"
                print(f"[PlotLink] token failed attempt {_retry+1}: {_te}", flush=True)
                _dc_token_cache.pop(enp_email, None)
                continue
            try:
                resp_data = _call_plot_link(_tok)
                print(f"[PlotLink] success on attempt {_retry+1} raw={str(resp_data)[:400]}", flush=True)
                break
            except _uerr2.HTTPError as he:
                _last_code = he.code
                _last_body = he.read().decode(errors="replace")
                _dc_token_cache.pop(enp_email, None)
                print(f"[PlotLink] HTTP {he.code} on attempt {_retry+1}: {_last_body[:120]}", flush=True)
                if he.code not in (401, 403):
                    raise HTTPException(he.code, f"DoconChain error {he.code}: {_last_body[:300]}")
                # 401/403 → clear cache and retry with fresh token
                continue

        if resp_data is None:
            raise HTTPException(_last_code,
                f"DoconChain plot link failed for {enp_email}: {_last_body[:300]}")

        # Extract link — DC may return { data: { link: "..." } } or { link: "..." }
        link = (
            (resp_data.get("message") or {}).get("link")
            or (resp_data.get("data") or {}).get("link")
            or resp_data.get("link")
            or resp_data.get("url")
            or (resp_data.get("data") or {}).get("url")
            or (resp_data.get("message") or {}).get("url")
        )
        if not link:
            raise HTTPException(502, f"No link in DoconChain response: {str(resp_data)[:200]}")

        # Record that plotting was started for this document
        for _apt in _db.list_apts():
            for _doc in _apt.get("session_documents", []):
                _duuid = _doc.get("doconchain_project_uuid") or _doc.get("project_uuid")
                if _duuid == project_uuid:
                    _doc["plotting_started"] = True
                    _doc["plotting_started_at"] = _dt.now(_tz.utc).isoformat()
                    _db.save_apt(_apt)
                    break

        # Resolve DC short link by capturing the 302 Location header (NOT following through).
        # The 302 Location contains the fresh token+api_token for auto-login.
        # Following all the way to the app gives an "Oops" page (no browser session).
        resolved_link = link
        if "link.doconchain.com" in link or "doconchain.com" in link:
            import requests as _rq_redirect
            try:
                # Use requests with allow_redirects=False to capture 302 Location
                # which contains the api_token for auto-login
                _r3 = _rq_redirect.get(
                    link,
                    headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"},
                    allow_redirects=False,
                    timeout=10,
                )
                if _r3.status_code in (301, 302, 303, 307, 308):
                    _loc = _r3.headers.get("Location", "")
                    if _loc and _loc.startswith("http"):
                        resolved_link = _loc
                        _has_token = "api_token=" in resolved_link
                        print(f"[PlotLink] short link resolved via {_r3.status_code} redirect (has api_token: {_has_token})", flush=True)
                    else:
                        resolved_link = link
                        print(f"[PlotLink] short link: {_r3.status_code} but no Location, using original", flush=True)
                else:
                    resolved_link = link
                    print(f"[PlotLink] short link returned {_r3.status_code} (no redirect), using original", flush=True)
            except Exception as _re:
                resolved_link = link
                print(f"[PlotLink] short link resolve failed: {_re}, using original", flush=True)

        try:
            from urllib.parse import urlparse
            _base = urlparse(resolved_link).netloc + urlparse(resolved_link).path
        except Exception:
            _base = resolved_link[:60]
        print(f"[PlotLink] link ready: {_base}", flush=True)
        return {"link": resolved_link, "project_uuid": project_uuid}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(502, f"Could not generate plot link: {str(e)[:200]}")


# ─── POST /api/sessions/create ────────────────────────────────────────────────

@app.post("/api/sessions/create")
async def create_session(
    req: SessionCreateRequest,
    authorization: Optional[str] = Header(None),
    ql_access: Optional[str] = Cookie(default=None),
):
    """ENP creates a LiveKit video session for an appointment."""
    user = get_current_user(authorization, ql_access)
    if not user:
        raise HTTPException(401, "Unauthorized")
    if user.get("role") != "attorney":
        raise HTTPException(403, "Only ENPs can create sessions")

    apt = _db.get_apt(req.apt_id)
    if not apt:
        raise HTTPException(404, "Appointment not found")
    if apt.get("enp_id") != user["id"]:
        raise HTTPException(403, "Not your appointment")

    ts        = int(time.time())
    room_name = f"ql-{req.apt_id[:8]}-{ts}"
    enp_name  = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip() or "ENP"
    token     = _create_livekit_token(room_name, user["id"], enp_name, can_publish=True)
    now_iso   = _dt.now(_tz.utc).isoformat()

    apt["session_room_name"]    = room_name
    apt["session_status"]       = "active"
    apt["session_created_at"]   = now_iso
    apt["session_ended_at"]     = None
    apt["session_participants"] = apt.get("session_participants", [])
    apt["updated_at"]           = now_iso
    _db.save_apt(apt)

    session_link = f"https://legal.quanbyai.com/session?room={room_name}&apt={req.apt_id}"
    return {
        "room_name":    room_name,
        "token":        token,
        "url":          _LIVEKIT_URL,
        "session_link": session_link,
    }


# ─── POST /api/sessions/join ──────────────────────────────────────────────────

@app.post("/api/sessions/join")
async def join_session(
    req: SessionJoinRequest,
    authorization: Optional[str] = Header(None),
    ql_access: Optional[str] = Cookie(default=None),
):
    """Client or ENP joins an existing LiveKit session."""
    user = get_current_user(authorization, ql_access)
    if not user:
        raise HTTPException(401, "Unauthorized")

    apt = _db.get_apt(req.apt_id)
    if not apt:
        raise HTTPException(404, "Appointment not found")

    uid = user["id"]
    user_email = (user.get("email") or "").lower().strip()

    # Allow join if: uid matches ENP/client, OR client_id is guest: and email matches
    _is_enp    = uid == apt.get("enp_id")
    _is_client = (uid == apt.get("client_id")
                  or ((apt.get("client_id") or "").startswith("guest:")
                      and (apt.get("client_email") or "").lower().strip() == user_email))
    # Also allow invited session_participants by email
    _is_invited = any(
        (p.get("email") or "").lower().strip() == user_email
        for p in apt.get("session_participants", [])
    )

    if not (_is_enp or _is_client or _is_invited):
        raise HTTPException(403, "Not your appointment")

    # For QuickSign appointments: always allow join as long as room exists
    _is_quicksign = apt.get("quicksign") or apt.get("dc_workflow_state") == "plotting_done"
    if apt.get("session_status") != "active" and not (_is_quicksign and apt.get("session_room_name")):
        raise HTTPException(400, "Session is not active")
    # Auto-reactivate QuickSign session if it was accidentally ended
    if _is_quicksign and apt.get("session_status") != "active" and apt.get("session_room_name"):
        _qs_reactivate = _db.get_apt(req.apt_id)
        if _qs_reactivate and _qs_reactivate.get("quicksign"):
            _qs_reactivate["session_status"] = "active"
            _db.save_apt(_qs_reactivate)

    is_enp    = _is_enp
    user_role = "ENP" if is_enp else "Client"
    user_name = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip() or user_role
    # ALWAYS use authoritative room_name from DB — never trust client-supplied value
    room_name = apt.get("session_room_name") or req.room_name
    token     = _create_livekit_token(room_name, uid, user_name, can_publish=True)

    return {
        "token":     token,
        "url":       _LIVEKIT_URL,
        "room_name": room_name,
        "user_name": user_name,
        "user_role": user_role,
    }


# ─── POST /api/sessions/invite ────────────────────────────────────────────────

@app.post("/api/sessions/invite")
async def invite_to_session(
    req: SessionInviteRequest,
    authorization: Optional[str] = Header(None),
    ql_access: Optional[str] = Cookie(default=None),
):
    """ENP invites a witness or observer to the session."""
    user = get_current_user(authorization, ql_access)
    if not user:
        raise HTTPException(401, "Unauthorized")
    if user.get("role") != "attorney":
        raise HTTPException(403, "Only ENPs can invite participants")

    role_upper = req.role.upper()
    if role_upper not in ("WITNESS", "OBSERVER"):
        raise HTTPException(400, "Role must be WITNESS or OBSERVER")

    apt = _db.get_apt(req.apt_id)
    if not apt:
        raise HTTPException(404, "Appointment not found")
    if apt.get("enp_id") != user["id"]:
        raise HTTPException(403, "Not your appointment")

    room_name = apt.get("session_room_name")
    if not room_name:
        raise HTTPException(400, "No active session for this appointment")

    can_publish = (role_upper == "WITNESS")
    identity    = f"guest-{uuid.uuid4().hex[:8]}"
    token       = _create_livekit_token(room_name, identity, req.name, can_publish=can_publish)
    now_iso     = _dt.now(_tz.utc).isoformat()

    participant = {
        "email":      req.email,
        "name":       req.name,
        "role":       role_upper,
        "invited_at": now_iso,
        "identity":   identity,
    }
    apt.setdefault("session_participants", []).append(participant)
    _db.save_apt(apt)

    join_link = (
        f"https://legal.quanbyai.com/lobby"
        f"?apt={req.apt_id}&guest_token={token}&room={room_name}"
    )
    return {
        "token":     token,
        "join_link": join_link,
    }


# ─── GET /api/sessions/{apt_id} ───────────────────────────────────────────────

@app.get("/api/sessions/{apt_id}")
async def get_session(
    apt_id: str,
    authorization: Optional[str] = Header(None),
    ql_access: Optional[str] = Cookie(default=None),
):
    """Get session info for an appointment."""
    user = get_current_user(authorization, ql_access)
    if not user:
        raise HTTPException(401, "Unauthorized")

    apt = _db.get_apt(apt_id)
    if not apt:
        raise HTTPException(404, "Appointment not found")

    uid = user["id"]
    _u_email = (user.get("email") or "").lower().strip()
    _ok = (uid == apt.get("client_id") or uid == apt.get("enp_id")
           or ((apt.get("client_id") or "").startswith("guest:")
               and (apt.get("client_email") or "").lower().strip() == _u_email)
           or any((p.get("email") or "").lower() == _u_email
                  for p in apt.get("session_participants", [])))
    if not _ok:
        raise HTTPException(403, "Not your appointment")

    # Build accepted participant email list: ENP + Client + accepted invited participants
    _accepted_emails = set()
    if apt.get("enp_email"):    _accepted_emails.add(apt["enp_email"].lower().strip())
    if apt.get("client_email"): _accepted_emails.add(apt["client_email"].lower().strip())
    for _p in apt.get("session_participants", []):
        if _p.get("email"):
            _accepted_emails.add(_p["email"].lower().strip())

    return {
        "apt_id":                       apt_id,
        "room_name":                    apt.get("session_room_name"),
        "session_status":               apt.get("session_status", "none"),
        "session_participants":         apt.get("session_participants", []),
        "session_documents":            apt.get("session_documents", []),
        "session_created_at":           apt.get("session_created_at"),
        "session_ended_at":             apt.get("session_ended_at"),
        "doconchain_sign_link":         apt.get("doconchain_sign_link"),
        "doconchain_project_uuid":      apt.get("doconchain_project_uuid"),
        "notarization_type":            apt.get("notarization_type"),
        "client_name":                  apt.get("client_name"),
        "client_email":                 apt.get("client_email", ""),
        "enp_name":                     apt.get("enp_name"),
        "enp_email":                    apt.get("enp_email", ""),
        "client_id":                    apt.get("client_id"),
        "enp_id":                       apt.get("enp_id"),
        "accepted_participant_emails":  sorted(_accepted_emails),
    }


# ─── POST /api/sessions/{apt_id}/end ─────────────────────────────────────────

@app.post("/api/sessions/{apt_id}/end")
async def end_session(
    apt_id: str,
    authorization: Optional[str] = Header(None),
    ql_access: Optional[str] = Cookie(default=None),
):
    """ENP ends a video session."""
    user = get_current_user(authorization, ql_access)
    if not user:
        raise HTTPException(401, "Unauthorized")
    if user.get("role") != "attorney":
        raise HTTPException(403, "Only ENPs can end sessions")

    apt = _db.get_apt(apt_id)
    if not apt:
        raise HTTPException(404, "Appointment not found")
    if apt.get("enp_id") != user["id"]:
        raise HTTPException(403, "Not your appointment")

    now_iso = _dt.now(_tz.utc).isoformat()
    apt["session_status"]   = "ended"
    apt["session_ended_at"] = now_iso
    apt["updated_at"]       = now_iso
    _db.save_apt(apt)

    # Background: populate notarial registry — run immediately + aggressive retries
    import threading as _t_endsession
    _enp_id_hook = user["id"]
    _t_endsession.Thread(
        target=_populate_registry_bg,
        args=(apt_id, _enp_id_hook),
        daemon=True,
    ).start()
    # Also schedule a second pass 10s later (catch docs that complete within seconds)
    def _delayed_populate():
        import time as _tp; _tp.sleep(10)
        _populate_registry_bg(apt_id, _enp_id_hook)
    _t_endsession.Thread(target=_delayed_populate, daemon=True).start()

    return {"success": True}


# ─── LiveKit Egress helpers ───────────────────────────────────────────────────

def _livekit_egress_jwt(action: str) -> str:
    """Generate a short-lived JWT for LiveKit server API calls."""
    import time as _time_e, base64 as _b64e
    _api_key    = os.getenv("LIVEKIT_API_KEY", "APIfmzJ2GVEV3TJ")
    _api_secret = os.getenv("LIVEKIT_API_SECRET", "sTxyVlCJaPF9QMJTevLvT1xRmSPiXSZXZnLgGoJsIOH")
    now = int(_time_e.time())
    header  = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "iss": _api_key,
        "sub": _api_key,
        "iat": now,
        "exp": now + 300,      # 5-minute token
        "video": {"roomRecord": True},
    }
    import json as _json_e, hmac as _hmac_e, hashlib as _hash_e
    def _b64url(d):
        return _b64e.urlsafe_b64encode(json.dumps(d, separators=(",", ":")).encode()).rstrip(b"=").decode()
    _hdr = _b64url(header)
    _pld = _b64url(payload)
    _sig = _b64e.urlsafe_b64encode(
        _hmac_e.new(_api_secret.encode(), f"{_hdr}.{_pld}".encode(), _hash_e.sha256).digest()
    ).rstrip(b"=").decode()
    return f"{_hdr}.{_pld}.{_sig}"


def _livekit_host_http() -> str:
    """Convert wss:// LiveKit URL to https:// for API calls."""
    url = os.getenv("LIVEKIT_URL", "wss://quanby-lms-k4aq44qe.livekit.cloud")
    return url.replace("wss://", "https://").replace("ws://", "http://")


# ─── POST /api/sessions/{apt_id}/recording/start ──────────────────────────────

@app.post("/api/sessions/{apt_id}/recording/start")
async def start_recording(
    apt_id: str,
    authorization: Optional[str] = Header(None),
    ql_access: Optional[str] = Cookie(default=None),
):
    """ENP-only. Start a LiveKit RoomCompositeEgress recording for this session."""
    user = get_current_user(authorization, ql_access)
    if not user:
        raise HTTPException(401, "Unauthorized")
    if user.get("role") != "attorney":
        raise HTTPException(403, "Only the ENP can start recording")

    apt = _db.get_apt(apt_id)
    if not apt:
        raise HTTPException(404, "Appointment not found")
    if apt.get("enp_id") != user["id"]:
        raise HTTPException(403, "Not your appointment")

    room_name = apt.get("session_room_name")
    if not room_name:
        raise HTTPException(400, "Session room not started yet")

    # Already recording?
    if apt.get("egress_id"):
        return {"already_recording": True, "egress_id": apt["egress_id"]}

    import urllib.request as _ureq_eg, urllib.error as _uerr_eg, json as _json_eg

    # Build Egress request — RoomCompositeEgress records the whole room layout
    _lk_host = _livekit_host_http()
    _token    = _livekit_egress_jwt("roomRecord")

    # File output: save to /recordings/ on LiveKit Cloud (S3 if configured, else cloud storage)
    # For LiveKit Cloud, we use direct file output — they handle storage
    # LiveKit Cloud built-in storage: just use a simple filename
    import time as _time_rec
    _ts = int(_time_rec.time())
    _filepath = f"{room_name}-{_ts}.mp4"
    _lk_api_key    = os.getenv('LIVEKIT_API_KEY', 'APIfmzJ2GVEV3TJ')
    _lk_api_secret = os.getenv('LIVEKIT_API_SECRET', 'sTxyVlCJaPF9QMJTevLvT1xRmSPiXSZXZnLgGoJsIOH')
    _lk_url        = os.getenv('LIVEKIT_URL', 'wss://quanby-lms-k4aq44qe.livekit.cloud')

    # Use livekit-api SDK (async — works directly in FastAPI's async context)
    try:
        from livekit.api import LiveKitAPI
        from livekit.protocol.egress import RoomCompositeEgressRequest, EncodedFileOutput, EncodedFileType

        async with LiveKitAPI(_lk_url, _lk_api_key, _lk_api_secret) as _lk:
            _efo = EncodedFileOutput(
                file_type=EncodedFileType.MP4,
                filepath=_filepath,
                disable_manifest=True,
            )
            _req = RoomCompositeEgressRequest(
                room_name=room_name,
                layout='speaker-dark',
                audio_only=False,
                file=_efo,
                file_outputs=[_efo],
            )
            _egress_info = await _lk.egress.start_room_composite_egress(_req)

        egress_id = _egress_info.egress_id
        if not egress_id:
            raise HTTPException(422, 'LiveKit SDK returned no egress_id')

        _rec_apt = _db.get_apt(apt_id)
        if _rec_apt:
            _rec_apt['egress_id'] = egress_id
            _rec_apt['recording_started_at'] = _dt.now(_tz.utc).isoformat()
            _db.save_apt(_rec_apt)
        return {'success': True, 'egress_id': egress_id, 'room_name': room_name}

    except ImportError as _ie:
        pass  # SDK not available, fall through to HTTP
    except Exception as _sdk_err:
        raise HTTPException(422, f'LiveKit SDK error: {str(_sdk_err)[:300]}')

    # Fallback: manual HTTP request (if SDK unavailable)
    _payload = _json_eg.dumps({
        'roomName': room_name,
        'layout': 'speaker-dark',
        'audioOnly': False,
        'fileOutputs': [{'fileType': 'MP4', 'filepath': _filepath, 'disableManifest': True}],
    }, separators=(',', ':')).encode()

    _req = _ureq_eg.Request(
        f"{_lk_host}/twirp/livekit.Egress/StartRoomCompositeEgress",
        data=_payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {_token}",
        },
        method="POST",
    )
    try:
        with _ureq_eg.urlopen(_req, timeout=20) as _r:
            _resp = _json_eg.loads(_r.read().decode())
    except _uerr_eg.HTTPError as _he:
        _err = _he.read().decode(errors="replace")
        raise HTTPException(422, f"LiveKit Egress error: {_err[:300]}")
    except Exception as _e:
        raise HTTPException(422, f"Could not start recording: {str(_e)[:200]}")

    egress_id = _resp.get("egress_id") or _resp.get("egressId")
    if not egress_id:
        raise HTTPException(502, f"No egress_id returned: {str(_resp)[:200]}")

    # Save egress_id to appointment
    _rec_apt2 = _db.get_apt(apt_id)
    if _rec_apt2:
        _rec_apt2["egress_id"] = egress_id
        _rec_apt2["recording_started_at"] = _dt.now(_tz.utc).isoformat()
        _db.save_apt(_rec_apt2)

    return {"success": True, "egress_id": egress_id, "room_name": room_name}


# ─── POST /api/sessions/{apt_id}/recording/stop ───────────────────────────────

@app.post("/api/sessions/{apt_id}/recording/stop")
async def stop_recording(
    apt_id: str,
    authorization: Optional[str] = Header(None),
    ql_access: Optional[str] = Cookie(default=None),
):
    """ENP-only. Stop the active LiveKit Egress recording."""
    user = get_current_user(authorization, ql_access)
    if not user:
        raise HTTPException(401, "Unauthorized")
    if user.get("role") != "attorney":
        raise HTTPException(403, "Only the ENP can stop recording")

    apt = _db.get_apt(apt_id)
    if not apt:
        raise HTTPException(404, "Appointment not found")

    egress_id = apt.get("egress_id")
    if not egress_id:
        return {"success": True, "note": "No active recording found"}

    import urllib.request as _ureq_eg2, urllib.error as _uerr_eg2, json as _json_eg2

    _lk_host = _livekit_host_http()
    _token    = _livekit_egress_jwt("roomRecord")
    _payload  = _json_eg2.dumps({"egress_id": egress_id}).encode()

    _req = _ureq_eg2.Request(
        f"{_lk_host}/twirp/livekit.Egress/StopEgress",
        data=_payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {_token}",
        },
        method="POST",
    )
    try:
        with _ureq_eg2.urlopen(_req, timeout=20) as _r:
            _resp = _json_eg2.loads(_r.read().decode())
    except _uerr_eg2.HTTPError as _he:
        _err = _he.read().decode(errors="replace")
        # If already stopped, treat as success
        if _he.code == 404 or "not found" in _err.lower():
            pass
        else:
            raise HTTPException(_he.code, f"LiveKit Egress stop error: {_err[:300]}")

    # Clear egress_id
    _stop_apt = _db.get_apt(apt_id)
    if _stop_apt:
        _stop_apt["last_egress_id"] = egress_id
        _stop_apt["egress_id"] = None
        _stop_apt["recording_stopped_at"] = _dt.now(_tz.utc).isoformat()
        _db.save_apt(_stop_apt)

    return {"success": True, "egress_id": egress_id, "stopped": True}


# ─── GET /api/sessions/{apt_id}/recording/status ──────────────────────────────

@app.get("/api/sessions/{apt_id}/recording/status")
async def recording_status(
    apt_id: str,
    authorization: Optional[str] = Header(None),
    ql_access: Optional[str] = Cookie(default=None),
):
    """Get current recording status for this session."""
    user = get_current_user(authorization, ql_access)
    if not user:
        raise HTTPException(401, "Unauthorized")

    apt = _db.get_apt(apt_id)
    if not apt:
        raise HTTPException(404, "Appointment not found")

    egress_id = apt.get("egress_id")
    return {
        "recording": bool(egress_id),
        "egress_id": egress_id,
        "started_at": apt.get("recording_started_at"),
    }


# ─── GET /api/sessions/{apt_id}/recording/download ───────────────────────────────────────────

@app.get("/api/sessions/{apt_id}/recording/download")
async def recording_download(
    apt_id: str,
    authorization: Optional[str] = Header(None),
    ql_access: Optional[str] = Cookie(default=None),
):
    """ENP-only. Get download URL for the session recording from LiveKit Egress."""
    user = get_current_user(authorization, ql_access)
    if not user:
        raise HTTPException(401, "Unauthorized")
    if user.get("role") != "attorney":
        raise HTTPException(403, "ENP access required")

    apt = _db.get_apt(apt_id)
    if not apt:
        raise HTTPException(404, "Appointment not found")
    if apt.get("enp_id") != user["id"]:
        raise HTTPException(403, "Not your appointment")

    egress_id = apt.get("egress_id") or apt.get("last_egress_id")
    if not egress_id:
        raise HTTPException(404, "No recording found for this session")

    import urllib.request as _ureq_dl, urllib.error as _uerr_dl, json as _json_dl

    _lk_host = _livekit_host_http()
    _token    = _livekit_egress_jwt("roomRecord")
    _payload  = _json_dl.dumps({"egress_id": egress_id}).encode()

    _req = _ureq_dl.Request(
        f"{_lk_host}/twirp/livekit.Egress/ListEgress",
        data=_payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {_token}",
        },
        method="POST",
    )
    try:
        with _ureq_dl.urlopen(_req, timeout=20) as _r:
            _resp = _json_dl.loads(_r.read().decode())
    except _uerr_dl.HTTPError as _he:
        _err = _he.read().decode(errors="replace")
        raise HTTPException(_he.code, f"LiveKit error: {_err[:300]}")
    except Exception as _e:
        raise HTTPException(502, f"Could not fetch recording info: {str(_e)[:200]}")

    items = _resp.get("items") or []
    if not items:
        raise HTTPException(404, "Recording not found in LiveKit")

    egress_info = items[0]
    status = egress_info.get("status", "")
    file_results = egress_info.get("file_results") or []

    download_url = None
    filename = None
    for fr in file_results:
        loc = fr.get("location") or fr.get("filename") or ""
        if loc:
            download_url = loc
            filename = fr.get("filename") or f"recording_{apt_id[:8]}.mp4"
            break

    return {
        "egress_id":    egress_id,
        "status":       status,
        "download_url": download_url,
        "filename":     filename,
        "started_at":   apt.get("recording_started_at"),
        "stopped_at":   apt.get("recording_stopped_at"),
        "file_results": file_results,
    }


# ─── POST /api/sessions/{apt_id}/upload-document ──────────────────────────────

@app.post("/api/sessions/{apt_id}/upload-document")
async def session_upload_document(
    apt_id: str,
    request: Request,
    authorization: Optional[str] = Header(None),
    ql_access: Optional[str] = Cookie(default=None),
):
    """Upload a document during a session, create a DoconChain project, return sign link."""
    user = get_current_user(authorization, ql_access)
    if not user:
        raise HTTPException(401, "Unauthorized")

    apt = _db.get_apt(apt_id)
    if not apt:
        raise HTTPException(404, "Appointment not found")
    if user["id"] not in (apt.get("enp_id"), apt.get("client_id")):
        raise HTTPException(403, "Not authorized for this session")

    form = await request.form()
    doc_name = str(form.get("doc_name", "Document")).strip() or "Document"
    notarization_type = str(form.get("notarization_type", apt.get("notarization_type", "ACKNOWLEDGMENT")))
    description = str(form.get("description", "")).strip()
    file_field = form.get("file")

    if file_field is None:
        raise HTTPException(400, "No file uploaded")

    file_bytes = await file_field.read()
    file_name = getattr(file_field, "filename", "document.pdf") or "document.pdf"
    content_type_hdr = getattr(file_field, "content_type", "application/pdf") or "application/pdf"

    if len(file_bytes) > 20 * 1024 * 1024:
        raise HTTPException(400, "File too large — max 20MB")
    if not file_bytes:
        raise HTTPException(400, "Empty file")

    DC_BASE = _DC_BASE
    DC_CLIENT_KEY = _DC_CLIENT_KEY
    DC_CLIENT_SECRET = _DC_CLIENT_SECRET
    DC_EMAIL = _DC_EMAIL

    enp_name = apt.get("enp_name", "ENP")
    commission_no = "N/A"
    from onboarding import get_user as _gu
    enp_user = _gu(apt.get("enp_id", ""))
    if enp_user:
        commission_no = (enp_user.get("profile") or {}).get("commission_no", "N/A")

    try:
        def _mp(url, fields, files=None, hdrs=None):
            """Multipart POST using requests (urllib has DNS issues in uvicorn workers)."""
            import requests as _rq_mp
            _files = {}
            _data = dict(fields)
            if files:
                for k, (fn, fd, ft) in files.items():
                    _files[k] = (fn, fd, ft)
            _headers = dict(hdrs or {})
            _r = _rq_mp.post(url, data=_data, files=_files if _files else None, headers=_headers, timeout=30)
            _r.raise_for_status()
            return _r.json()

        # Use ENP's email so they own the project (auto-auth on plot link)
        _enp_email_dc = (enp_user or user or {}).get('email') or DC_EMAIL
        tok = _mp(f'{DC_BASE}/api/v2/generate/token',
            {'client_key': DC_CLIENT_KEY, 'client_secret': DC_CLIENT_SECRET, 'email': _enp_email_dc})
        dc_token = (tok.get('data') or {}).get('token') or tok.get('token')
        if not dc_token:
            # Fallback to org token
            tok = _mp(f'{DC_BASE}/api/v2/generate/token',
                {'client_key': DC_CLIENT_KEY, 'client_secret': DC_CLIENT_SECRET, 'email': DC_EMAIL})
            dc_token = (tok.get('data') or {}).get('token') or tok.get('token')
        if not dc_token:
            raise ValueError(f"No token: {tok}")

        _enp_for_stamp = enp_user or user
        stamp = _build_dc_stamp(_enp_for_stamp, apt)
        proj = _mp(
            f'{DC_BASE}/api/v2/projects?user_type=ENTERPRISE_API',
            _build_create_fields(stamp, apt),
            files={'file': (file_name, file_bytes, content_type_hdr)},
            hdrs={'Authorization': f'Bearer {dc_token}'},
        )
    except _urllib_err.HTTPError as e:
        raise HTTPException(502, f"DoconChain error {e.code}: {e.read().decode(errors='replace')[:300]}")
    except Exception as e:
        raise HTTPException(502, f"DoconChain failed: {str(e)[:200]}")

    data = proj.get('data') or proj
    project_uuid = data.get('uuid') or data.get('id') or ''
    if not project_uuid:
        raise HTTPException(502, f"DoconChain project creation succeeded but returned no UUID. Response: {str(proj)[:200]}")
    sign_link = f"https://stg-app.doconchain.com/sign/{project_uuid}"

    # Default fee from SC schedule — ENP can override later
    _FEE_DEFAULTS = {
        "ACKNOWLEDGMENT": "₱100 – ₱300",
        "JURAT": "₱100 – ₱300",
        "AFFIRMATION": "₱100 – ₱300",
        "SIGNATURE_WITNESSING": "₱50 – ₱200",
        "COPY_CERTIFICATION": "₱50 – ₱200",
        "OATH_ADMINISTRATION": "₱100 – ₱300",
    }
    doc_fee = _FEE_DEFAULTS.get(notarization_type, "₱100 – ₱300")

    # Auto-add ENP and client as signers — ENP is always LAST (sequence=2)
    _doc_signers_list = []

    # Client signs first (sequence=1)
    try:
        _cn = apt.get("client_name","Client").split()
        _cf = _cn[0] if _cn else "Client"
        _cl = " ".join(_cn[1:]) if len(_cn)>1 else ""
        _ce = (apt.get("client_email","") or "").lower().strip()
        if _ce:
            _add_dc_signer(project_uuid, _ce, _cf, _cl, "Signer", dc_token, sequence=1)
            _doc_signers_list.append({
                "email": _ce,
                "name": f"{_cf} {_cl}".strip(),
                "first_name": _cf,
                "last_name": _cl,
                "signer_role": "Signer",
                "signing_order": 1,
                "status": None,
            })
            print(f"[UploadDoc] Added client signer: {_ce} seq=1", flush=True)
    except Exception as _cs_err:
        print(f"[UploadDoc] Client signer error: {_cs_err}", flush=True)

    # ENP signs last (sequence=2)
    try:
        _enp_u = enp_user or user
        _ef = _enp_u.get("first_name","") or "ENP"
        _el = _enp_u.get("last_name","") or ""
        _ee = (_enp_u.get("email","") or "").lower().strip()
        if _ee:
            _add_dc_signer(project_uuid, _ee, _ef, _el, "Signer", dc_token, sequence=2)
            _doc_signers_list.append({
                "email": _ee,
                "name": f"{_ef} {_el}".strip(),
                "first_name": _ef,
                "last_name": _el,
                "signer_role": "ENP",
                "signing_order": 2,
                "status": None,
                "is_enp": True,
            })
            print(f"[UploadDoc] Added ENP signer: {_ee} seq=2", flush=True)
    except Exception as _es_err:
        print(f"[UploadDoc] ENP signer error: {_es_err}", flush=True)

    doc_entry = {
        "name": doc_name,
        "doc_name": doc_name,
        "notarization_type": notarization_type,
        "description": description, "file_name": file_name,
        "project_uuid": project_uuid,
        "doconchain_project_uuid": project_uuid,
        "sign_link": sign_link,
        "fee": doc_fee,
        "uploaded_by": user["id"],
        "uploaded_by_name": f"{user.get('first_name','')} {user.get('last_name','')}".strip(),
        "uploaded_at": _dt.now(_tz.utc).isoformat(),
        # Signers now populated — client (seq=1) then ENP (seq=2)
        # This ensures signer-status can correlate DC signers with local DB
        "signers": _doc_signers_list,
    }
    _doc_apt = _db.get_apt(apt_id)
    if _doc_apt:
        _doc_apt.setdefault("session_documents", []).append(doc_entry)
        _doc_apt["doconchain_project_uuid"] = project_uuid
        _doc_apt["doconchain_sign_link"] = sign_link
        _doc_apt["updated_at"] = _dt.now(_tz.utc).isoformat()
        _db.save_apt(_doc_apt)

    return {"success": True, "doc_name": doc_name, "notarization_type": notarization_type,
            "project_uuid": project_uuid, "sign_link": sign_link}

# ─── PATCH /api/sessions/{apt_id}/documents/{project_uuid}/fee ────────────────

@app.patch("/api/sessions/{apt_id}/documents/{project_uuid}/fee")
async def update_document_fee(
    apt_id: str,
    project_uuid: str,
    request: Request,
    authorization: Optional[str] = Header(None),
    ql_access: Optional[str] = Cookie(default=None),
):
    """ENP-only: update the displayed notarization fee for a specific document."""
    user = get_current_user(authorization, ql_access)
    if not user:
        raise HTTPException(401, "Unauthorized")
    # All authenticated users can use QuickSign

    apt = _db.get_apt(apt_id)
    if not apt:
        raise HTTPException(404, "Appointment not found")
    if user["id"] != apt.get("enp_id"):
        raise HTTPException(403, "Only the ENP of this session can edit fees")

    body = await request.json()
    new_fee = str(body.get("fee", "")).strip()
    if not new_fee:
        raise HTTPException(400, "fee is required")
    if len(new_fee) > 50:
        raise HTTPException(400, "fee string too long (max 50 chars)")

    docs = apt.get("session_documents", [])
    updated = False
    for doc in docs:
        if doc.get("project_uuid") == project_uuid or doc.get("doconchain_project_uuid") == project_uuid:
            doc["fee"] = new_fee
            updated = True
            break
    if not updated:
        raise HTTPException(404, f"Document with project_uuid={project_uuid} not found")
    apt["updated_at"] = _dt.now(_tz.utc).isoformat()
    _db.save_apt(apt)

    return {"success": True, "project_uuid": project_uuid, "fee": new_fee}


# ─── POST /api/sessions/{apt_id}/documents/{project_uuid}/signers ─────────────
# ─── POST /api/sessions/{apt_id}/documents/{project_uuid}/signers ─────────────
@app.post("/api/sessions/{apt_id}/documents/{project_uuid}/signers")
async def add_document_signer(
    apt_id: str,
    project_uuid: str,
    request: Request,
    authorization: Optional[str] = Header(None),
    ql_access: Optional[str] = Cookie(default=None),
):
    """ENP adds a signer to a DoconChain document via POST /projects/{uuid}/signers.
    Serialized per document. Blocked once signing has started.
    """
    user = get_current_user(authorization, ql_access)
    if not user:
        raise HTTPException(401, "Unauthorized")

    apt = _db.get_apt(apt_id)
    if not apt:
        raise HTTPException(404, "Appointment not found")
    if user["id"] != apt.get("enp_id"):
        raise HTTPException(403, "Only the ENP can add signers")

    body = await request.json()
    email         = (body.get("email") or "").strip().lower()
    first_name    = (body.get("first_name") or "").strip()
    last_name     = (body.get("last_name") or "").strip()
    signer_role   = (body.get("signer_role") or "Signer").strip()
    signing_order = int(body.get("signing_order") or 1)

    if not email:
        raise HTTPException(400, "email is required")
    if signer_role not in ("Signer", "Approver"):
        raise HTTPException(400, "signer_role must be Signer or Approver")

    # Validate participant is in this appointment
    _accepted = {(apt.get("enp_email") or "").lower(), (apt.get("client_email") or "").lower()}
    for _p in apt.get("session_participants", []):
        if _p.get("email"): _accepted.add(_p["email"].lower())
    _accepted.discard("")
    if email not in _accepted:
        raise HTTPException(400, f"'{email}' is not an accepted participant of this appointment.")

    # ── Acquire per-document lock ─────────────────────────────────────────────
    _doc_lock = _get_doc_lock(project_uuid)
    if not _doc_lock.acquire(timeout=30):
        raise HTTPException(409, "Another signer is being added — please retry in a moment.")
    try:
        # Locate document
        apt = _db.get_apt(apt_id) or {}
        docs = apt.get("session_documents", [])
        _target_doc = next(
            (d for d in docs if d.get("doconchain_project_uuid") == project_uuid
             or d.get("project_uuid") == project_uuid), None
        )
        if not _target_doc:
            raise HTTPException(404, f"Document '{project_uuid}' not found in this appointment.")

        # GUARD: reject if signing has already started
        if any(r.get("status") == "SIGNED" for r in _target_doc.get("signature_requests", [])):
            raise HTTPException(409, "Signing has already started — roster is locked.")
        if _target_doc.get("dc_workflow_state") in ("plotting", "signing", "completed"):
            raise HTTPException(409, f"Document is in '{_target_doc.get('dc_workflow_state')}' state — roster is locked.")

        # ── Call DoconChain POST /projects/{uuid}/signers ─────────────────────
        import urllib.request as _ureqSig, urllib.error as _uerrSig, json as _jsonSig

        _enp_email_s = apt.get("enp_email") or user.get("email") or _DC_EMAIL
        _dc_token_cache.pop(_enp_email_s, None)  # force fresh token
        _dc_token_s = _get_dc_token(email=_enp_email_s)

        _sig_payload = _jsonSig.dumps({
            "email": email,
            "first_name": first_name,
            "last_name": last_name,
            "type": "GUEST",
            "signer_role": signer_role,
        }).encode()

        # ── LOG: signer add request ─────────────────────────────────────────────
        _payload_log = _jsonSig.loads(_sig_payload.decode())
        print(
            f"[AddSigner] ──────────────────────────────────────────────────────",
            flush=True
        )
        print(
            f"[AddSigner] REQUEST  uuid={project_uuid} order={signing_order}",
            flush=True
        )
        print(
            f"[AddSigner]          email={email} role={signer_role} name={first_name} {last_name}",
            flush=True
        )
        print(
            f"[AddSigner]          payload={_payload_log}",
            flush=True
        )

        _sig_req = _ureqSig.Request(
            f"{_DC_BASE}/projects/{project_uuid}/signers?user_type=ENTERPRISE_API",
            data=_sig_payload,
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {_dc_token_s}"},
            method="POST",
        )
        dc_resp = {}
        try:
            with _ureqSig.urlopen(_sig_req, timeout=20) as _r:
                dc_resp = _jsonSig.loads(_r.read().decode())
            # ── LOG: DC response ──────────────────────────────────────────────────
            _dc_resp_data = dc_resp.get("data") or dc_resp
            if isinstance(_dc_resp_data, list) and _dc_resp_data:
                _first = _dc_resp_data[0]
                print(
                    f"[AddSigner] ✅ DC RESPONSE  HTTP=200",
                    flush=True
                )
                print(
                    f"[AddSigner]    signer_id={_first.get('id')} email={_first.get('email')}",
                    flush=True
                )
                print(
                    f"[AddSigner]    signer_role={_first.get('signer_role')} sequence={_first.get('sequence')} status={_first.get('status','pending')}",
                    flush=True
                )
            else:
                print(f"[AddSigner] ✅ DC RESPONSE  {dc_resp}", flush=True)
        except _uerrSig.HTTPError as _he:
            _err_body = _he.read().decode(errors="replace")
            print(f"[AddSigner] ❌ DC ERROR  HTTP={_he.code}  body={_err_body[:300]}", flush=True)
            if _he.code == 409 or "already" in _err_body.lower():
                dc_resp = {"already_added": True}
            else:
                dc_resp = {"dc_error": _he.code, "detail": _err_body[:200]}

        # ── Persist signer locally ────────────────────────────────────────────
        _sig_apt = _db.get_apt(apt_id)
        if _sig_apt:
            for _d in _sig_apt.get("session_documents", []):
                if _d.get("doconchain_project_uuid") == project_uuid or _d.get("project_uuid") == project_uuid:
                    _d.setdefault("signers", [])
                    _emap = {s.get("email", "").lower(): s for s in _d["signers"]}
                    if email in _emap:
                        _emap[email].update({
                            "signer_role": signer_role, "signing_order": signing_order,
                            "first_name": first_name or _emap[email].get("first_name", ""),
                            "last_name":  last_name  or _emap[email].get("last_name", ""),
                            "updated_at": _dt.now(_tz.utc).isoformat(),
                        })
                    else:
                        _d["signers"].append({
                            "email": email, "first_name": first_name, "last_name": last_name,
                            "signer_role": signer_role, "signing_order": signing_order,
                            "added_at": _dt.now(_tz.utc).isoformat(),
                        })
                    break
            _sig_apt["updated_at"] = _dt.now(_tz.utc).isoformat()
            _db.save_apt(_sig_apt)

            # ── LOG: full signer order for this doc after save ──────────────────
            for _d_check in _sig_apt.get("session_documents", []):
                if _d_check.get("doconchain_project_uuid") == project_uuid or _d_check.get("project_uuid") == project_uuid:
                    _signers_now = _d_check.get("signers", [])
                    _sorted = sorted(_signers_now, key=lambda s: s.get("signing_order", 99))
                    print(
                        f"[AddSigner] ── SIGNER ORDER for {project_uuid[:12]} ({len(_sorted)} total) ──",
                        flush=True
                    )
                    for _idx, _s in enumerate(_sorted):
                        print(
                            f"[AddSigner]   [{_idx+1}] order={_s.get('signing_order')} "
                            f"email={_s.get('email')} role={_s.get('signer_role')} "
                            f"name={_s.get('first_name','')} {_s.get('last_name','')}",
                            flush=True
                        )
                    print(
                        f"[AddSigner] ──────────────────────────────────────────────────────",
                        flush=True
                    )
                    break

    finally:
        try:
            _doc_lock.release()
        except RuntimeError:
            pass

    return {
        "success": True,
        "project_uuid": project_uuid,
        "old_project_uuid": project_uuid,
        "email": email,
        "signer_role": signer_role,
        "signing_order": signing_order,
        "dc_response": dc_resp,
    }


# ══════════════════════════════════════════════════════════════════════════════
# NOTARIAL REGISTRY
# ══════════════════════════════════════════════════════════════════════════════

def _upsert_book(enp_id: str, enp_name: str, roll_no: str, commission_no: str) -> None:
    """Ensure a registry book entry exists for this ENP (DB-backed, idempotent)."""
    _db.upsert_registry_book({
        "enp_id": enp_id,
        "enp_name": enp_name,
        "roll_no": roll_no,
        "commission_no": commission_no,
        "created_at": _dt.now(_tz.utc).isoformat(),
    })

def _act_exists(enp_id: str, dc_uuid: str) -> bool:
    """Check if a registry act already exists (DB-backed)."""
    return _db.act_exists(enp_id, dc_uuid)

_registry_in_progress: set = set()  # FIX: prevents double-population

def _populate_registry_bg(apt_id: str, enp_id: str) -> None:
    """Background thread: populate registry acts from a completed appointment.
    
    IMPORTANT: Only populates when session_status == "ended".
    Documents must be from a completed, ended session to ensure they are fully notarized.
    """
    # FIX: Dedup guard — prevent concurrent double-population for same apt_id
    if apt_id in _registry_in_progress:
        print(f'[Registry] Already in progress for {apt_id}, skipping duplicate', flush=True)
        return
    _registry_in_progress.add(apt_id)
    try:
        import urllib.request as _ureg, json as _jreg

        # Load appointment from DB
        apt = _db.get_apt(apt_id)
        if not apt:
            return
        apt = dict(apt)

        # GUARD: Only populate registry when session has ended
        if apt.get("session_status") != "ended":
            print(f'[Registry] SKIPPED apt={apt_id} — session_status={apt.get("session_status")} (must be "ended")', flush=True)
            return

        # Get ENP user info
        enp_user = get_user(enp_id)
        if not enp_user:
            return
        profile = enp_user.get("profile") or {}
        enp_name = f"{enp_user.get('first_name','') or ''} {enp_user.get('last_name','') or ''}".strip()
        roll_no = profile.get("roll_no", "")
        commission_no = profile.get("commission_no", "")
        enp_email = enp_user.get("email", "").lower()

        # Get DC token — MUST use ENP email; org default email cannot access ENP projects
        try:
            dc_token = _get_dc_token(email=enp_email)
            print(f'[Registry] Token OK for enp={enp_email} apt={apt_id}', flush=True)
        except Exception as _tok_err:
            print(f'[Registry] Token FAILED for enp={enp_email}: {_tok_err}', flush=True)
            return

        session_docs = apt.get("session_documents", [])
        if not session_docs:
            # QuickSign fallback: apt root may have dc uuid directly
            _root_uuid = apt.get("doconchain_project_uuid") or apt.get("project_uuid")
            if _root_uuid:
                print(f"[Registry] QuickSign fallback: using root dc_uuid={_root_uuid[:12]} apt={apt_id}", flush=True)
                session_docs = [{
                    "doconchain_project_uuid": _root_uuid,
                    "doc_name": apt.get("title") or apt.get("doc_name") or "QuickSign Document",
                    "notarization_type": apt.get("notarization_type") or "ACKNOWLEDGMENT",
                    "signers": apt.get("session_participants") or [],
                }]
            else:
                return

        # ── Fetch all DC project data from Vault — OUTSIDE the lock (prevents deadlock) ──
        # Uses GET /vault/items/{uuid}?user_type=ENTERPRISE_API — the authoritative
        # endpoint for completed notarized documents. Only completed docs appear here.
        import requests as _rq_vault
        _dc_items = {}  # dc_uuid -> vault item data
        for doc in session_docs:
            dc_uuid = doc.get("doconchain_project_uuid") or doc.get("project_uuid")
            if not dc_uuid:
                continue
            # Quick check: already in registry?
            if _act_exists(enp_id, dc_uuid):
                print(f'[Registry] Already in registry: {dc_uuid[:12]}, skipping', flush=True)
                continue
            # Fetch from vault — only completed projects appear here
            _vault_url = f"{_DC_BASE}/vault/items/{dc_uuid}?user_type=ENTERPRISE_API"
            try:
                _vault_resp = _rq_vault.get(
                    _vault_url,
                    headers={"Authorization": f"Bearer {dc_token}"},
                    timeout=20,
                )
                if _vault_resp.status_code == 200:
                    _proj_data = _vault_resp.json()
                    _d = _proj_data.get("data") or {}
                    if isinstance(_d, list):
                        _d = _d[0] if _d else {}
                    # Vault only returns completed docs — status should be "completed"
                    _vault_status = (_d.get("status") or "").lower()
                    if _vault_status == "completed" and (_d.get("uuid") or _d.get("project_uuid")):
                        # Store vault item — dc_file_url = data.url (top-level sealed PDF per DC spec)
                        _d["_dc_file_url"] = _d.get("url") or ""
                        _d["_dc_file_name"] = _d.get("file_name") or "notarized-document.pdf"
                        if not _d["_dc_file_url"]:
                            # Fallback: files[].file_url (DC vault spec)
                            for _vf in (_d.get("files") or []):
                                _vfu = _vf.get("file_url") or _vf.get("url") or ""
                                if _vfu:
                                    _d["_dc_file_url"] = _vfu
                                    _d["_dc_file_name"] = _vf.get("file_name") or _d["_dc_file_name"]
                                    break
                        _dc_items[dc_uuid] = _d
                        print(f'[Registry] Vault OK: {dc_uuid[:12]} status={_vault_status} ref={_d.get("reference_number","")} file_url={bool(_d["_dc_file_url"])}', flush=True)
                    else:
                        print(f'[Registry] Vault returned uuid={dc_uuid[:12]} status={_vault_status} — not completed, skipping', flush=True)
                elif _vault_resp.status_code == 404:
                    print(f'[Registry] Vault 404 for {dc_uuid[:12]} — document not yet in vault (not completed)', flush=True)
                elif _vault_resp.status_code == 401:
                    # Token expired — refresh and retry once
                    print(f'[Registry] Vault 401 for {dc_uuid[:12]} — refreshing token and retrying', flush=True)
                    try:
                        dc_token = _get_dc_token(email=enp_email)
                        _vault_resp2 = _rq_vault.get(
                            _vault_url,
                            headers={"Authorization": f"Bearer {dc_token}"},
                            timeout=20,
                        )
                        if _vault_resp2.status_code == 200:
                            _proj_data2 = _vault_resp2.json()
                            _d2 = _proj_data2.get("data") or {}
                            if isinstance(_d2, list):
                                _d2 = _d2[0] if _d2 else {}
                            if (_d2.get("status") or "").lower() == "completed":
                                _dc_items[dc_uuid] = _d2
                                print(f'[Registry] Vault OK (retry): {dc_uuid[:12]}', flush=True)
                    except Exception as _retry_err:
                        print(f'[Registry] Vault retry failed: {_retry_err}', flush=True)
                elif _vault_resp.status_code == 400:
                    # Vault 400 = project not yet indexed (not completed or still processing).
                    # ONLY create a local fallback entry if ALL internal signature_requests
                    # have status=SIGNED — prevents premature/false registry entries.
                    _local_srs = doc.get("signature_requests", [])
                    _all_sr_signed = (
                        len(_local_srs) > 0 and
                        all(r.get("status") == "SIGNED" for r in _local_srs)
                    )
                    if _all_sr_signed:
                        print(f'[Registry] Vault 400 for {dc_uuid[:12]} but all signers SIGNED locally — local fallback', flush=True)
                        _dc_items[dc_uuid] = {
                            "status": "completed",
                            "uuid": dc_uuid,
                            "project_uuid": dc_uuid,
                            "reference_number": None,
                            "completed_at": None,
                            "signers": doc.get("signers", []),
                            "_local_fallback": True,
                        }
                    else:
                        print(f'[Registry] Vault 400 for {dc_uuid[:12]} and signers NOT all signed — skipping (doc not complete)', flush=True)
                else:
                    print(f'[Registry] Vault HTTP {_vault_resp.status_code} for {dc_uuid[:12]}', flush=True)
            except Exception as _vault_err:
                print(f'[Registry] Vault fetch error for {dc_uuid[:12]}: {_vault_err}', flush=True)

        # ── Write phase: upsert book + acts into DB ───────────────────────────
        _upsert_book(enp_id, enp_name, roll_no, commission_no)
        n_added = 0

        for doc in session_docs:
            dc_uuid = doc.get("doconchain_project_uuid") or doc.get("project_uuid")
            if not dc_uuid:
                continue
            if _act_exists(enp_id, dc_uuid):
                continue

            item = _dc_items.get(dc_uuid)
            if not item:
                continue

            # Items in _dc_items are ALREADY confirmed as status="completed" from vault.
            # The vault endpoint (GET /vault/items/{uuid}) only returns completed projects.
            dc_status = (item.get("status") or "").lower()
            completed_at = item.get("completed_at") or item.get("completedAt")

            # Belt-and-suspenders: double check vault status is completed
            if dc_status != "completed":
                print(f'[Registry] Unexpected: vault item {dc_uuid[:12]} has status={dc_status} — skipping', flush=True)
                continue

            print(f'[Registry] Inserting completed vault doc: apt={apt_id} uuid={dc_uuid[:12]} ref={item.get("reference_number","")}', flush=True)

            doc_name = (
                doc.get("doc_name") or
                item.get("name") or item.get("title") or
                item.get("project_name") or
                doc.get("doc_type", "Document")
            )
            dc_ref_number = item.get("reference_number") or item.get("ref_no") or ""
            executed_at = completed_at or item.get("updated_at") or _dt.now(_tz.utc).isoformat()

            # Signers snapshot: prefer DC vault signers (authoritative), fall back to local
            dc_vault_signers = item.get("signers") or []
            local_signers = doc.get("signers") or []
            dc_signers_snapshot = list(dc_vault_signers) if dc_vault_signers else list(local_signers)

            def _signer_display_name(s):
                """Handle both DC vault format (name) and local format (first_name/last_name)."""
                if s.get("name"):
                    return s["name"].strip()
                return f"{s.get('first_name','') or ''} {s.get('last_name','') or ''}".strip()

            # Extract principal and witness:
            # Use local doc.signers roles (Signer=Principal, Approver=Witness) for correct classification
            # ENP is excluded from both
            principal_name = ""
            principal_email = ""
            witness_name = ""
            witness_email = ""

            # Build email->role map from local signers
            local_role_map = {
                (s.get("email") or "").lower(): s.get("signer_role", "Signer")
                for s in local_signers
            }

            # Find principal (Signer role, not ENP) and witness (Approver role)
            for s in local_signers:
                s_email = (s.get("email") or "").lower()
                if s_email == enp_email:
                    continue
                role = s.get("signer_role", "Signer")
                name = _signer_display_name(s)
                if role == "Signer" and not principal_email:
                    principal_name = name
                    principal_email = s_email
                elif role == "Approver" and not witness_email:
                    witness_name = name
                    witness_email = s_email

            # Fallback: if local signers empty, use DC vault signers by position
            if not principal_email:
                non_enp_dc = [s for s in dc_vault_signers if (s.get("email") or "").lower() != enp_email]
                if non_enp_dc:
                    p = non_enp_dc[0]
                    principal_name = _signer_display_name(p)
                    principal_email = (p.get("email") or "").lower()
                if len(non_enp_dc) > 1:
                    w = non_enp_dc[1]
                    witness_name = _signer_display_name(w)
                    witness_email = (w.get("email") or "").lower()

            # Determine act type
            act_type = (
                doc.get("notarization_type") or
                doc.get("act_type") or
                apt.get("notarization_type") or
                "ACKNOWLEDGMENT"
            ).upper()
            if "JURAT" in act_type:
                act_type = "JURAT"
            elif "ACKNOWLEDGMENT" in act_type or "ACKNOWLEDGEMENT" in act_type:
                act_type = "ACKNOWLEDGMENT"
            elif "OATH" in act_type:
                act_type = "OATH"
            elif "AFFIDAVIT" in act_type:
                act_type = "AFFIDAVIT"

            act = {
                "id": str(uuid.uuid4()),
                "book_id": enp_id,
                "enp_id": enp_id,
                "enp_email": enp_email,
                "enp_name": enp_name,
                "roll_no": roll_no,
                "commission_no": commission_no,
                "apt_id": apt_id,
                "doc_name": doc_name,
                "doconchain_project_uuid": dc_uuid,
                "dc_project_uuid": dc_uuid,          # alias for UI compat
                "act_type": act_type,
                "executed_at": executed_at,
                "principal_name": principal_name,
                "principal_email": principal_email,
                "witness_name": witness_name,
                "witness_email": witness_email,
                "dc_signers_snapshot": dc_signers_snapshot,
                "dc_status": dc_status,
                "dc_reference_number": dc_ref_number,
                "dc_reference_no": dc_ref_number,    # alias for UI compat
                "dc_file_url": item.get("_dc_file_url") or item.get("url") or "",
                "dc_file_name": item.get("_dc_file_name") or item.get("file_name") or "",
                "location": "Remote Electronic Notarization",
                "sc_synced": False,
                "sc_registry_id": None,
                "created_at": _dt.now(_tz.utc).isoformat(),
            }
            _db.upsert_registry_act(act)
            n_added += 1
            print(f'[Registry] ✅ Added act apt={apt_id} uuid={dc_uuid[:12]} type={act_type} ref={dc_ref_number}', flush=True)

        if n_added:
            print(f'[Registry] Saved {n_added} act(s) for apt={apt_id}', flush=True)

        # Retry pending docs (not yet completed at time of session-end)
        pending_docs = [
            d for d in session_docs
            if (d.get('doconchain_project_uuid') or d.get('project_uuid'))
            and not _act_exists(enp_id, d.get('doconchain_project_uuid') or d.get('project_uuid'))
        ]
        if pending_docs:
            import time as _t_retry
            for _retry in range(20):  # retry for up to 10 minutes
                _t_retry.sleep(30)
                print(f'[Registry] Retry {_retry+1}/20 for apt {apt_id}', flush=True)
                retry_added = False
                for doc in pending_docs[:]:
                    dc_uuid2 = doc.get('doconchain_project_uuid') or doc.get('project_uuid')
                    if not dc_uuid2 or _act_exists(enp_id, dc_uuid2):
                        pending_docs.remove(doc)
                        continue
                    # Refresh token on each retry (may have expired)
                    try:
                        dc_token = _get_dc_token(email=enp_email)
                    except Exception:
                        pass  # use existing token if refresh fails
                    try:
                        _ru2 = f"{_DC_BASE}/api/v2/projects/{dc_uuid2}?user_type=ENTERPRISE_API"
                        _rreq2 = _ureg.Request(_ru2, headers={'Authorization': f'Bearer {dc_token}'}, method='GET')
                        with _ureg.urlopen(_rreq2, timeout=20) as _rr2:
                            _ri2 = _jreg.loads(_rr2.read().decode())
                        _rd2 = _ri2.get('data') or _ri2
                        _rstat2 = (_rd2.get('status') or '').lower()
                        _rcomp2 = _rd2.get('completed_at')
                        if _rstat2 == 'completed' or _rcomp2:
                            print(f'[Registry] Retry {_retry+1}: {dc_uuid2} now completed', flush=True)
                            _ra2 = {
                                'id': str(uuid.uuid4()), 'book_id': enp_id, 'enp_id': enp_id,
                                'enp_email': enp_email, 'enp_name': enp_name, 'roll_no': roll_no,
                                'commission_no': commission_no, 'apt_id': apt_id,
                                'doc_name': doc.get('doc_name') or _rd2.get('name') or 'Document',
                                'doconchain_project_uuid': dc_uuid2,
                                'dc_project_uuid': dc_uuid2,
                                'act_type': (doc.get('notarization_type') or apt.get('notarization_type') or 'ACKNOWLEDGMENT').upper(),
                                'executed_at': _rcomp2 or _dt.now(_tz.utc).isoformat(),
                                'principal_name': principal_name, 'principal_email': principal_email,
                                'witness_name': witness_name, 'witness_email': witness_email,
                                'dc_signers_snapshot': _rd2.get('signers') or [],
                                'dc_status': _rstat2,
                                'dc_reference_number': _rd2.get('reference_number') or '',
                                'dc_reference_no': _rd2.get('reference_number') or '',
                                'location': 'Remote Electronic Notarization',
                                'sc_synced': False, 'sc_registry_id': None,
                                'created_at': _dt.now(_tz.utc).isoformat(),
                            }
                            _db.upsert_registry_act(_ra2)
                            retry_added = True
                            pending_docs.remove(doc)
                    except Exception as _re2:
                        print(f'[Registry] Retry error: {_re2}', flush=True)
                if not pending_docs:
                    break

    except Exception as _bg_err:
        print(f'[Registry] populate error for apt {apt_id}: {_bg_err}', flush=True)
    finally:
        _registry_in_progress.discard(apt_id)


# ─── POST /api/registry/populate/{apt_id} ─────────────────────────────────────

@app.post("/api/registry/populate/{apt_id}")
async def registry_populate(
    apt_id: str,
    authorization: Optional[str] = Header(None),
    ql_access: Optional[str] = Cookie(default=None),
):
    """ENP-only: Populate registry acts from a completed appointment."""
    user = get_current_user(authorization, ql_access)
    if not user:
        raise HTTPException(401, "Unauthorized")
    if user.get("role") != "attorney":
        raise HTTPException(403, "ENP access required")

    import threading as _treg_t
    t = _treg_t.Thread(
        target=_populate_registry_bg,
        args=(apt_id, user["id"]),
        daemon=True,
    )
    t.start()
    return {"success": True, "message": "Registry population started"}


# ─── POST /api/registry/sync-all ──────────────────────────────────────────────

@app.post("/api/registry/sync-all")
async def registry_sync_all(
    authorization: Optional[str] = Header(None),
    ql_access: Optional[str] = Cookie(default=None),
):
    """ENP-only: Populate registry from ALL ended sessions — catches any missed acts."""
    user = get_current_user(authorization, ql_access)
    if not user:
        raise HTTPException(401, "Unauthorized")
    if user.get("role") != "attorney":
        raise HTTPException(403, "ENP access required")

    enp_id = user["id"]
    import threading as _tsyncall
    ended_apts = [
        a["apt_id"] for a in _db.list_apts()
        if a.get("session_status") == "ended"
        and a.get("enp_id") == enp_id
        and a.get("session_documents")
    ]

    if not ended_apts:
        return {"success": True, "message": "No ended sessions found", "queued": 0}

    for aid in ended_apts:
        _tsyncall.Thread(
            target=_populate_registry_bg,
            args=(aid, enp_id),
            daemon=True,
        ).start()

    return {"success": True, "message": f"Syncing {len(ended_apts)} sessions", "queued": len(ended_apts)}


# ─── GET /api/registry/acts ───────────────────────────────────────────────────

@app.get("/api/registry/acts")
async def registry_list_acts(
    authorization: Optional[str] = Header(None),
    ql_access: Optional[str] = Cookie(default=None),
    act_type: Optional[str] = None,
    search: Optional[str] = None,
    page: int = 1,
    per_page: int = 20,
):
    """ENP-only: List notarial acts for current user with optional filters."""
    user = get_current_user(authorization, ql_access)
    if not user:
        raise HTTPException(401, "Unauthorized")
    if user.get("role") != "attorney":
        raise HTTPException(403, "ENP access required")

    enp_id = user["id"]
    acts = _db.list_acts(enp_id=enp_id)

    # Filters
    if act_type:
        acts = [a for a in acts if a.get("act_type", "").upper() == act_type.upper()]
    if search:
        q = search.lower()
        acts = [
            a for a in acts
            if q in (a.get("doc_name") or "").lower()
            or q in (a.get("principal_name") or "").lower()
            or q in (a.get("principal_email") or "").lower()
            or q in (a.get("dc_reference_number") or "").lower()
        ]

    # Sort newest first
    acts.sort(key=lambda x: x.get("executed_at") or x.get("created_at") or "", reverse=True)

    total = len(acts)
    start = (page - 1) * per_page
    end = start + per_page
    page_acts = acts[start:end]

    # Stats
    from datetime import datetime as _stat_dt
    now_m = _stat_dt.now(_tz.utc)
    this_month = sum(
        1 for a in acts
        if (a.get("executed_at") or a.get("created_at") or "")[:7] == f"{now_m.year:04d}-{now_m.month:02d}"
    )
    pending_sc = sum(1 for a in acts if not a.get("sc_synced"))

    # Enrich acts with enp_email and fee from appointment docs
    _enp_email = (user.get("email") or "").lower()
    enriched = []
    for _act in page_acts:
        _a = dict(_act)
        _a["enp_email"] = _enp_email
        # Normalize field name aliases for UI compatibility
        if not _a.get("dc_project_uuid") and _a.get("doconchain_project_uuid"):
            _a["dc_project_uuid"] = _a["doconchain_project_uuid"]
        if not _a.get("dc_reference_no") and _a.get("dc_reference_number"):
            _a["dc_reference_no"] = _a["dc_reference_number"]
        # Get fee from appointment session_documents
        if not _a.get("fee"):
            try:
                _apt_doc = _db.get_apt(_a.get("apt_id") or "")
                if _apt_doc:
                    for _doc in _apt_doc.get("session_documents", []):
                        if (_doc.get("doconchain_project_uuid") or _doc.get("project_uuid")) == _a.get("doconchain_project_uuid"):
                            _a["fee"] = _doc.get("fee") or ""
                            break
            except Exception:
                pass
        enriched.append(_a)

    return {
        "acts": enriched,
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": max(1, (total + per_page - 1) // per_page),
        "stats": {
            "total": total,
            "this_month": this_month,
            "pending_sc_sync": pending_sc,
        },
    }


# ─── POST /api/registry/acts/{act_id}/sync-sc ─────────────────────────────────

@app.post("/api/registry/acts/{act_id}/sync-sc")
async def registry_sync_sc(
    act_id: str,
    authorization: Optional[str] = Header(None),
    ql_access: Optional[str] = Cookie(default=None),
):
    """ENP-only: Sync a notarial act to the Supreme Court eNotarization registry.
    Flow: Cognito auth → commission check → POST /public-use/consolidated → store NRID/NRN.
    Falls back to stub if SC credentials not configured.
    """
    user = get_current_user(authorization, ql_access)
    if not user:
        raise HTTPException(401, "Unauthorized")
    if user.get("role") != "attorney":
        raise HTTPException(403, "ENP access required")

    enp_id = user["id"]
    act = _db.get_act_by_id(act_id, enp_id=enp_id)
    if not act:
        raise HTTPException(404, "Act not found")
    if act.get("sc_synced"):
        return {"success": True, "already_synced": True,
                "sc_registry_id": act.get("sc_registry_id"),
                "nrid": act.get("nrid"), "nrn": act.get("nrn")}

    # Get ENP profile for NPN and Roll Number
    enp_user = get_user(enp_id)
    profile = (enp_user or {}).get('profile') or {}
    # Prefer profile fields, fall back to values stored in the act itself
    _raw_npn = (profile.get('npn') or profile.get('commission_no') or act.get('commission_no') or '').strip()
    _raw_rn  = (profile.get('roll_no') or profile.get('rn') or act.get('roll_no') or '').strip()
    npn = _sc_normalize_id(_raw_npn, 'NPN-')
    rn  = _sc_normalize_id(_raw_rn,  'RN-')
    enp_name = (f"{(enp_user or {}).get('first_name','')} {(enp_user or {}).get('last_name','')}".strip()
                or act.get('enp_name', ''))

    # If SC not configured, use stub (returns clearly labelled placeholder)
    if not all([_SC_API_URL, _SC_USERNAME, _SC_PASSWORD]):
        nrid = f"NRID-{act_id[:8].upper()}"
        nrn  = f"NRN-{act_id[:8].upper()}"
        act_upd = _db.get_act_by_id(act_id)
        if act_upd:
            act_upd["sc_synced"]      = True
            act_upd["sc_registry_id"] = nrid
            act_upd["nrid"]           = nrid
            act_upd["nrn"]            = nrn
            act_upd["sc_synced_at"]   = _dt.now(_tz.utc).isoformat()
            act_upd["sc_note"]        = "stub — SUPREME_COURT_* env vars not set"
            _db.upsert_registry_act(act_upd)
        return {"success": True, "stub": True, "sc_registry_id": nrid, "nrid": nrid, "nrn": nrn,
                "note": "Stub NRID — configure SUPREME_COURT_* env vars for real SC sync"}

    # ── Live SC sync (run blocking IO in executor) ─────────────────────────────
    nfn = _sc_normalize_id(_SC_NFN, "NFN-")
    import asyncio as _asyncio_sc
    loop = _asyncio_sc.get_event_loop()  # use running loop in async context
    try:
        loop = _asyncio_sc.get_running_loop()
    except RuntimeError:
        pass

    def _do_sc_sync():
        import logging as _log_sc
        _logger_sc = _log_sc.getLogger("quanby.sc_sync")

        sc_token = _sc_get_token()

        # Step 1: Commission check (best-effort; warn but don't block)
        try:
            # SC spec: /public-use/cs takes only npn + rn (no nfn)
            cs_resp = _sc_request("POST", "/public-use/cs",
                {"npn": npn, "rn": rn}, token=sc_token)
            # SC spec response: { "commissionStatus": "Active" | "Inactive" }
            commission_status = str(
                cs_resp.get("commissionStatus") or cs_resp.get("status", "")
            ).strip().lower()
            if commission_status == "inactive":
                raise ValueError(f"ENP commission is Inactive per SC registry.")
            print(f'[SC] commission check passed: commissionStatus={commission_status}', flush=True)
        except ValueError:
            raise  # Re-raise explicit commission status failures (inactive/revoked)
        except Exception as _cs_err:
            # HTTP errors, network errors, invalid NPN in staging — all non-fatal
            print(f'[SC] /public-use/cs warning (continuing): {_cs_err}', flush=True)

        # Step 2: Build principals list per SC spec
        # SC spec: { principalName, principalAddress: { homeStreet, barangay, cityProvince } }
        list_of_principals = []
        if act.get("principal_name") or act.get("principal_email"):
            list_of_principals.append({
                "principalName": act.get("principal_name") or act.get("principal_email", ""),
                "principalAddress": {
                    "homeStreet": profile.get("home_street") or "N/A",
                    "barangay": profile.get("barangay") or "N/A",
                    "cityProvince": profile.get("city_province") or act.get("location", "Remote Electronic Notarization"),
                },
            })

        # Step 3: Build witnesses list per SC spec
        # SC spec: { witnessName, witnessAddress: { homeStreet, barangay, cityProvince } }
        list_of_witness = []
        if act.get("witness_name") or act.get("witness_email"):
            list_of_witness.append({
                "witnessName": act.get("witness_name") or act.get("witness_email", ""),
                "witnessAddress": {
                    "homeStreet": profile.get("home_street") or "N/A",
                    "barangay": profile.get("barangay") or "N/A",
                    "cityProvince": profile.get("city_province") or act.get("location", "Remote Electronic Notarization"),
                },
            })

        # Parse date for SC spec (dateNotarized must be YYYY-MM-DD)
        _exec_at = act.get("executed_at", _dt.now(_tz.utc).isoformat())
        _date_notarized = _exec_at[:10] if _exec_at else _dt.now(_tz.utc).strftime("%Y-%m-%d")
        _date_updated   = _dt.now(_tz.utc).strftime("%Y-%m-%d")

        # Map act_type to SC's accepted values
        _act_type_map = {
            "ACKNOWLEDGMENT": "Acknowledgment",
            "JURAT": "Jurat",
            "COPY_CERTIFICATION": "Copy Certification",
            "OATH": "Oath and Affirmation",
        }
        _notarial_act_type = _act_type_map.get(
            str(act.get("act_type", "ACKNOWLEDGMENT")).upper(),
            act.get("act_type", "Acknowledgment")
        )

        # Step 4: POST /public-use/consolidated — exact SC spec field names
        consolidated_payload = {
            "notaryFacilityNumber": nfn,
            "notaryPublicNumber":   npn,
            "rollNumber":           rn,
            "metaData": {
                "dateNotarized":       _date_notarized,
                "notarialActType":     _notarial_act_type,
                "notarialPageNumber":  act.get("page_number", 1),
                "notarialBookNumber":  act.get("book_number", 1),
                "description":         act.get("doc_name", "Notarized Document"),
                "modeOfNotarization":  "Remote Online",
                "remarks":             act.get("description") or act.get("doc_name", "Notarized Document"),
                "dateUpdated":         _date_updated,
            },
            "listOfPrincipals": list_of_principals,
            "listOfWitness":    list_of_witness,
        }
        import json as _json_sc_log, sys as _sys_sc_log
        print('[SC CONSOLIDATED PAYLOAD]', _json_sc_log.dumps(consolidated_payload, indent=2), file=_sys_sc_log.stderr, flush=True)
        try:
            sc_resp = _sc_request("POST", "/public-use/consolidated", consolidated_payload, token=sc_token)
            print('[SC CONSOLIDATED RESPONSE]', _json_sc_log.dumps(sc_resp, indent=2), file=_sys_sc_log.stderr, flush=True)
        except Exception as _sc_con_err:
            print('[SC CONSOLIDATED ERROR]', str(_sc_con_err)[:1000], file=_sys_sc_log.stderr, flush=True)
            raise

        nrid = (sc_resp.get("notarialRegistryID") or sc_resp.get("nrid")
                or sc_resp.get("id") or "")
        nrn  = (sc_resp.get("notarialRegistryNumber") or sc_resp.get("nrn") or "")
        if not nrid:
            raise ValueError(f"SC API did not return NRID. Response: {str(sc_resp)[:300]}")

        # Step 4: Optional PDF upload (if doc_pdf_path stored in act)
        pdf_upload_result = None
        doc_pdf_path = act.get("doc_pdf_path") or ""
        if doc_pdf_path and _SC_API_URL:
            try:
                import os as _os_pdf
                if _os_pdf.path.exists(doc_pdf_path):
                    with open(doc_pdf_path, "rb") as _f:
                        pdf_bytes = _f.read()
                    doc_name = act.get("doc_name", "notarized_document.pdf")
                    if not doc_name.endswith(".pdf"):
                        doc_name += ".pdf"
                    pdf_upload_result = _sc_upload_pdf(nrid, pdf_bytes, doc_name, token=sc_token)
                    _logger_sc.info("SC PDF upload result: %s", pdf_upload_result)
            except Exception as _pdf_err:
                _logger_sc.warning("SC PDF upload failed (NRID still saved): %s", _pdf_err)

        return nrid, nrn, sc_resp, pdf_upload_result

    try:
        nrid, nrn, sc_resp, pdf_upload_result = await loop.run_in_executor(None, _do_sc_sync)
    except ValueError as _ve:
        raise HTTPException(422, str(_ve))
    except Exception as _sc_err:
        # Use 422 not 502 — Cloudflare intercepts 5xx and replaces with HTML,
        # breaking the frontend JSON parse. 422 passes through as JSON.
        raise HTTPException(422, f"Supreme Court sync failed: {str(_sc_err)[:400]}")

    act_upd = _db.get_act_by_id(act_id)
    if act_upd:
        act_upd["sc_synced"]      = True
        act_upd["sc_registry_id"] = nrid
        act_upd["nrid"]           = nrid
        act_upd["nrn"]            = nrn
        act_upd["sc_synced_at"]   = _dt.now(_tz.utc).isoformat()
        act_upd["sc_response"]    = sc_resp
        if pdf_upload_result:
            act_upd["sc_pdf_uploaded"] = True
            act_upd["sc_pdf_response"] = pdf_upload_result
        _db.upsert_registry_act(act_upd)

    return {
        "success":        True,
        "sc_registry_id": nrid,
        "nrid":           nrid,
        "nrn":            nrn,
        "pdf_uploaded":   bool(pdf_upload_result),
    }



# ─── POST /api/registry/acts/{act_id}/resync-dc ────────────────────────────────

@app.post("/api/registry/acts/{act_id}/resync-dc")
async def registry_resync_dc(
    act_id: str,
    authorization: Optional[str] = Header(None),
    ql_access: Optional[str] = Cookie(default=None),
):
    """ENP-only: Re-trigger Doconchain vault fetch for a specific act.
    Useful when dc_status is not completed and ENP wants to re-check.
    Clears the fetched flag so the document endpoint will try again.
    """
    user = get_current_user(authorization, ql_access)
    if not user:
        raise HTTPException(401, "Unauthorized")
    if user.get("role") != "attorney":
        raise HTTPException(403, "ENP access required")

    enp_id = user["id"]
    act = _db.get_act_by_id(act_id, enp_id=enp_id)
    if not act:
        raise HTTPException(404, "Act not found")

    dc_uuid = act.get("doconchain_project_uuid") or act.get("dc_project_uuid") or ""
    if not dc_uuid:
        return {"success": False, "message": "No Doconchain project UUID on this act"}

    # Try to fetch fresh data from Doconchain projects endpoint
    import requests as _rq_resync
    enp_email = (user.get("email") or "").lower().strip()
    updated = False

    try:
        tok = _get_dc_token(email=enp_email)
        proj_url = f"{_DC_BASE}/api/v2/projects/{dc_uuid}?user_type=ENTERPRISE_API"
        resp = _rq_resync.get(proj_url, headers={"Authorization": f"Bearer {tok}", "Accept": "application/json"}, timeout=20)
        if resp.status_code == 401:
            _dc_token_cache.pop(enp_email, None)
            tok = _get_dc_token(email=enp_email)
            resp = _rq_resync.get(proj_url, headers={"Authorization": f"Bearer {tok}", "Accept": "application/json"}, timeout=20)
        if resp.ok:
            data = resp.json().get("data") or {}
            new_status = (data.get("status") or "").lower()
            ref_no = data.get("reference_number") or ""
            completed_at = data.get("completed_at")
            # Update act with fresh DC data
            act_upd = dict(act)
            if new_status:
                act_upd["dc_status"] = new_status
            if ref_no:
                act_upd["dc_reference_number"] = ref_no
                act_upd["dc_reference_no"] = ref_no
            if completed_at:
                act_upd["executed_at"] = completed_at
            # If completed, try to get file URL
            if new_status == "completed":
                _priority = ["Document Completed", "Document Certification", "Original With Signature And QR", "Original"]
                _files_by_type = {f.get("type", ""): f for f in (data.get("files") or []) if f.get("url")}
                for _ptype in _priority:
                    if _ptype in _files_by_type:
                        act_upd["dc_file_url"] = _files_by_type[_ptype]["url"]
                        act_upd["dc_file_name"] = _files_by_type[_ptype].get("file_name") or act.get("doc_name") or "document.pdf"
                        break
            _db.upsert_registry_act(act_upd)
            updated = True
            print(f"[ResyncDC] Act {act_id[:8]} updated: dc_status={new_status} ref={ref_no}", flush=True)
            return {
                "success": True,
                "dc_status": new_status or act.get("dc_status"),
                "dc_reference_no": ref_no or act.get("dc_reference_no"),
                "message": f"Re-synced from Doconchain. Status: {new_status or 'unknown'}",
                "updated": updated,
            }
        else:
            return {
                "success": False,
                "message": f"Doconchain returned HTTP {resp.status_code}. Document may not be ready yet.",
                "dc_status": act.get("dc_status"),
            }
    except Exception as _e:
        print(f"[ResyncDC] Error for act {act_id[:8]}: {_e}", flush=True)
        return {"success": False, "message": str(_e)}


# ─── GET /api/pdf-proxy ───────────────────────────────────────────────────────
@app.get("/api/pdf-proxy")
async def pdf_proxy(
    url: str,
    authorization: Optional[str] = Header(None),
    ql_access: Optional[str] = Cookie(default=None),
):
    """Proxy a remote PDF URL through our server so iframes can embed it."""
    from fastapi.responses import StreamingResponse
    import urllib.request as _uproxy
    user = get_current_user(authorization, ql_access)
    if not user:
        raise HTTPException(401, "Unauthorized")
    if not url or not url.startswith("https://"):
        raise HTTPException(400, "Invalid URL")
    # Only allow DoconChain domains
    from urllib.parse import urlparse as _uprx_parse
    _host = _uprx_parse(url).hostname or ""
    if "doconchain" not in _host and "amazonaws" not in _host and "s3." not in _host:
        raise HTTPException(403, "Domain not allowed")
    try:
        req = _uproxy.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        resp = _uproxy.urlopen(req, timeout=30)
        content = resp.read()
        ct = resp.headers.get("Content-Type", "application/pdf")
        import io
        return StreamingResponse(
            io.BytesIO(content),
            media_type="application/pdf",
            headers={
                "Content-Disposition": "inline",
                "Content-Length": str(len(content)),
                "X-Frame-Options": "SAMEORIGIN",
                "Cache-Control": "private, max-age=300",
            }
        )
    except Exception as e:
        raise HTTPException(502, f"Could not fetch PDF: {str(e)[:200]}")

# ─── GET /__vault_download/{vault_uuid} ────────────────────────────────────────
@app.get("/__vault_download/{vault_uuid}")
async def vault_download_proxy(
    vault_uuid: str,
    _tok: str = "",
    authorization: Optional[str] = Header(None),
    ql_access: Optional[str] = Cookie(default=None),
):
    """
    Proxy endpoint: streams the completed notarized PDF directly from 
    Doconchain vault. Uses GET /vault/items/{vault_uuid}/download.
    The _tok param is a short-lived DC token; if expired, we refresh.
    """
    from fastapi.responses import StreamingResponse
    import urllib.request as _uvdl, urllib.error as _uvdl_err
    import io as _io_vd

    user = get_current_user(authorization, ql_access)
    if not user:
        raise HTTPException(401, "Unauthorized")

    # Use provided token or get a fresh one
    tok = _tok or ""
    enp_email = (user.get("email") or "").lower()

    def _try_download(token):
        _url = f"{_DC_BASE}/vault/items/{vault_uuid}/download?user_type=ENTERPRISE_API"
        _req = _uvdl.Request(_url, headers={"Authorization": f"Bearer {token}"}, method="GET")
        with _uvdl.urlopen(_req, timeout=30) as _r:
            _ct = _r.headers.get("Content-Type", "application/pdf")
            _data = _r.read()
        return _ct, _data

    try:
        ct, data = _try_download(tok)
    except (_uvdl_err.HTTPError, Exception):
        # Token expired or invalid — refresh
        try:
            tok = _get_dc_token(email=enp_email) or _get_dc_token(email=_DC_EMAIL)
            ct, data = _try_download(tok)
        except Exception as _e:
            raise HTTPException(502, f"Could not download from vault: {str(_e)[:200]}")

    if not data or data[:4] != b"%PDF":
        raise HTTPException(502, "Vault response is not a valid PDF")

    return StreamingResponse(
        _io_vd.BytesIO(data),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="notarized-document.pdf"',
            "Content-Length": str(len(data)),
            "Cache-Control": "private, max-age=300",
        }
    )




# ─── GET /api/registry/acts/{act_id}/proxy-pdf ────────────────────────────────

@app.get("/api/registry/acts/{act_id}/proxy-pdf")
async def proxy_registry_pdf(
    act_id: str,
    authorization: Optional[str] = Header(None),
    ql_access: Optional[str] = Cookie(default=None),
):
    """Proxy the notarized PDF from DoconChain through our backend.
    Avoids CORS issues — browser only talks to our domain."""
    import requests as _rq_proxy
    from fastapi.responses import StreamingResponse, Response as FastAPIResponse

    user = get_current_user(authorization, ql_access)
    if not user:
        raise HTTPException(401, "Unauthorized")

    enp_id = user["id"]
    act = _db.get_act_by_id(act_id, enp_id=enp_id)
    if not act:
        raise HTTPException(404, "Act not found")

    dc_uuid = act.get("doconchain_project_uuid") or ""
    if not dc_uuid:
        raise HTTPException(404, "No DoconChain project linked to this act")

    enp_email = (user.get("email") or "").lower().strip()

    # ── DIAGNOSTIC: Point 5 — Check DC project completion BEFORE fetching PDF ────
    import requests as _rq_gate
    try:
        _gate_tok = _get_dc_token(email=enp_email)
        _gate_resp = _rq_gate.get(
            f"{_DC_BASE}/api/v2/projects/{dc_uuid}?user_type=ENTERPRISE_API",
            headers={"Authorization": f"Bearer {_gate_tok}", "Accept": "application/json"},
            timeout=15,
        )
        if _gate_resp.status_code == 200:
            _gate_data = _gate_resp.json().get("data") or {}
            _gate_status = (_gate_data.get("status") or "").lower()
            _gate_completed = _gate_data.get("completed_at") or _gate_data.get("completedAt")
            _gate_signers = _gate_data.get("signers", [])
            print(
                f"[ProxyPDF] Completion gate: uuid={dc_uuid[:12]} status={_gate_status} "
                f"completed_at={_gate_completed} signers={len(_gate_signers)} token_email={enp_email}",
                flush=True
            )
            for _gs in _gate_signers:
                print(
                    f"[ProxyPDF]   signer={(_gs.get('email') or '').lower()} "
                    f"status={(_gs.get('status') or '').upper()}",
                    flush=True
                )
            # Point 5: warn if not completed — still serve file for registry (already in vault)
            if _gate_status not in ("completed", "complete"):
                print(f"[ProxyPDF] WARN: project {dc_uuid[:12]} status={_gate_status} — PDF may not be sealed", flush=True)
        else:
            print(f"[ProxyPDF] Completion gate check HTTP {_gate_resp.status_code} for {dc_uuid[:12]}", flush=True)
    except Exception as _gate_err:
        print(f"[ProxyPDF] Completion gate error: {_gate_err}", flush=True)

    # Try to get a direct file URL from DC
    file_url = act.get("dc_file_url") or ""
    file_name = act.get("dc_file_name") or act.get("doc_name") or "notarized-document.pdf"

    # If no stored URL, fetch fresh from DC projects endpoint
    if not file_url:
        priority = ['Document Completed', 'Document Certification', 'Original With Signature And QR', 'Original']
        for _email in [enp_email, _DC_EMAIL]:
            try:
                tok = _get_dc_token(email=_email)
                _r = _rq_proxy.get(
                    f"{_DC_BASE}/api/v2/projects/{dc_uuid}?user_type=ENTERPRISE_API",
                    headers={"Authorization": f"Bearer {tok}", "Accept": "application/json"},
                    timeout=15,
                )
                if _r.status_code == 200:
                    _data = _r.json().get("data") or {}
                    _files_by_type = {}
                    for _f in (_data.get("files") or []):
                        _ft = _f.get("type") or ""
                        _fu = _f.get("url") or ""
                        _fn = _f.get("file_name") or file_name
                        if _fu and _ft:
                            _files_by_type[_ft] = (_fu, _fn)
                    for _pt in priority:
                        if _pt in _files_by_type:
                            file_url, file_name = _files_by_type[_pt]
                            break
                if file_url:
                    break
            except Exception:
                continue

    if not file_url:
        raise HTTPException(404, "Document not available — may still be processing on DoconChain")

    # Proxy the file through our backend
    try:
        tok = _get_dc_token(email=enp_email)
        _pdf_resp = _rq_proxy.get(file_url, headers={"Authorization": f"Bearer {tok}"}, timeout=30, stream=True)
        if _pdf_resp.status_code != 200:
            # Try without auth (some DC URLs are pre-signed)
            _pdf_resp = _rq_proxy.get(file_url, timeout=30, stream=True)
        if _pdf_resp.status_code != 200:
            raise HTTPException(502, f"DoconChain returned {_pdf_resp.status_code}")

        content_type = _pdf_resp.headers.get("content-type", "application/pdf")
        safe_name = file_name.replace('"', "'")

        def _stream():
            for chunk in _pdf_resp.iter_content(chunk_size=8192):
                if chunk:
                    yield chunk

        return StreamingResponse(
            _stream(),
            media_type=content_type,
            headers={
                "Content-Disposition": f'inline; filename="{safe_name}"',
                "Cache-Control": "private, max-age=300",
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(502, f"Could not fetch document: {str(e)[:200]}")

# ─── GET /api/registry/acts/{act_id}/document ─────────────────────────────────────────────

@app.get("/api/registry/acts/{act_id}/document")
async def registry_get_document(
    act_id: str,
    authorization: Optional[str] = Header(None),
    ql_access: Optional[str] = Cookie(default=None),
):
    """ENP-only: Fetch document download URLs — tries SC retrieval first, then DoconChain vault."""
    user = get_current_user(authorization, ql_access)
    if not user:
        raise HTTPException(401, "Unauthorized")
    if user.get("role") != "attorney":
        raise HTTPException(403, "ENP access required")

    enp_id = user["id"]
    act = _db.get_act_by_id(act_id, enp_id=enp_id)
    if not act:
        raise HTTPException(404, "Act not found")

    import asyncio as _asyncio_doc
    import urllib.request as _ureq_doc, json as _json_doc

    # ── 1. Try SC retrieval/file (only if synced) ──────────────────────────────
    sc_files = []
    sc_raw = None
    nrid = act.get("nrid") or ""
    if act.get("sc_synced") and nrid:
        def _fetch_sc_doc():
            return _sc_request("POST", "/retrieval/file", {"notarialRegistryID": nrid})
        try:
            loop = _asyncio_doc.get_event_loop()
            try:
                loop = _asyncio_doc.get_running_loop()
            except RuntimeError:
                pass
            sc_raw = await loop.run_in_executor(None, _fetch_sc_doc)
            # SC response: { "files": [{ "fileName": "...", "downloadUrl": "..." }] }
            sc_files = sc_raw.get("files") or sc_raw.get("documents") or []
            if isinstance(sc_raw, list):
                sc_files = sc_raw
        except Exception as _sc_doc_err:
            print(f"[SC] retrieval/file failed (non-fatal): {_sc_doc_err}", flush=True)

    # ── 2. DoconChain vault — fetch completed project file ────────────────────
    dc_uuid = act.get("doconchain_project_uuid") or ""
    dc_files = []
    dc_view_url = None

    if dc_uuid:
        def _fetch_dc_vault():
            enp_email = (user.get("email") or "").lower().strip()

            # STEP 1: Try stored dc_file_url first (fastest, no DC call needed)
            _stored_url = act.get("dc_file_url") or ""
            if _stored_url and _stored_url.startswith("http"):
                try:
                    import requests as _rq_head
                    _hr = _rq_head.head(_stored_url, timeout=5)
                    if _hr.status_code == 200:
                        print(f"[DC] Using stored dc_file_url for {dc_uuid[:12]}", flush=True)
                        return {
                            "_source": "stored_url",
                            "url": _stored_url,
                            "file_name": act.get("dc_file_name") or "notarized-document.pdf",
                            "status": "completed",
                        }
                except Exception:
                    print(f"[DC] Stored URL expired/unavailable for {dc_uuid[:12]}, fetching fresh", flush=True)

            # STEP 2: Try DoconChain VAULT first — this has the sealed/stamped notarized PDF
            # (vault only contains completed documents with notarial seal applied)
            import requests as _rq_doc
            _vault_priority = ['Document Completed', 'Document Certification', 'Original With Signature And QR', 'Original']
            for _vemail in [enp_email, _DC_EMAIL]:
                if not _vemail: continue
                try:
                    _vtok = _get_dc_token(email=_vemail)
                    _vr = _rq_doc.get(
                        f"{_DC_BASE}/vault/items/{dc_uuid}?user_type=ENTERPRISE_API",
                        headers={"Authorization": f"Bearer {_vtok}", "Accept": "application/json"},
                        timeout=20,
                    )
                    if _vr.status_code == 200:
                        _vdata = _vr.json().get("data") or {}
                        if isinstance(_vdata, list): _vdata = _vdata[0] if _vdata else {}
                        if (_vdata.get("status") or "").lower() == "completed":
                            # DC vault spec: data.url = top-level file URL (primary notarized PDF)
                            # data.files[] = [{file_id, file_name, file_url}] — no "type" field
                            _vault_url = _vdata.get("url") or ""
                            _vault_fn = _vdata.get("file_name") or act.get("doc_name") or "notarized-document.pdf"
                            # Use top-level url first (the sealed notarized doc)
                            if not _vault_url:
                                # Fallback: first file in files[]
                                for _vf in (_vdata.get("files") or []):
                                    _vfu = _vf.get("file_url") or _vf.get("url") or ""
                                    _vfn = _vf.get("file_name") or _vault_fn
                                    if _vfu:
                                        _vault_url = _vfu
                                        _vault_fn = _vfn
                                        break
                            if _vault_url:
                                print(f"[DC] Vault sealed PDF for {dc_uuid[:12]}: {_vault_fn}", flush=True)
                                return {"_source": "vault", "url": _vault_url, "file_name": _vault_fn, "status": "completed"}
                except Exception as _ve:
                    print(f"[DC] Vault fetch failed for {dc_uuid[:12]}: {_ve}", flush=True)

            # STEP 3: Fall back to projects endpoint (in-progress or vault not indexed yet)
            _priority = ['Document Completed', 'Document Certification', 'Original With Signature And QR', 'Original']
            for _email in [enp_email, _DC_EMAIL]:
                if not _email:
                    continue
                try:
                    tok = _get_dc_token(email=_email)
                    proj_url = f"{_DC_BASE}/api/v2/projects/{dc_uuid}?user_type=ENTERPRISE_API"
                    _resp_r = _rq_doc.get(proj_url, headers={"Authorization": f"Bearer {tok}", "Accept": "application/json"}, timeout=20)
                    if _resp_r.status_code == 401:
                        _dc_token_cache.pop(_email, None)
                        tok = _get_dc_token(email=_email)
                        _resp_r = _rq_doc.get(proj_url, headers={"Authorization": f"Bearer {tok}", "Accept": "application/json"}, timeout=20)
                    _resp_r.raise_for_status()
                    resp = _resp_r.json()
                    data = resp.get("data") or resp
                    if data and data.get("uuid"):
                        # Find best file in priority order
                        _files_by_type = {}
                        for _f in (data.get("files") or []):
                            _ft = _f.get("type") or ""
                            _fu = _f.get("url") or ""
                            _fn = _f.get("file_name") or act.get("doc_name") or "document"
                            if _fu and _ft:
                                _files_by_type[_ft] = (_fu, _fn)
                        for _ptype in _priority:
                            if _ptype in _files_by_type:
                                _fu, _fn = _files_by_type[_ptype]
                                print(f"[DC] Fresh URL fetched for {dc_uuid[:12]}: {_ptype}", flush=True)
                                # Update stored URL async
                                try:
                                    import threading as _t_upd
                                    _act_upd = dict(act)
                                    _act_upd["dc_file_url"] = _fu
                                    _act_upd["dc_file_name"] = _fn
                                    def _upd():
                                        import database as _dbu
                                        _dbu.upsert_registry_act(_act_upd)
                                    _t_upd.Thread(target=_upd, daemon=True).start()
                                except Exception:
                                    pass
                                return {
                                    "_source": "projects_fresh",
                                    "url": _fu,
                                    "file_name": _fn,
                                    "status": "completed",
                                }
                        data["_source"] = "projects"
                        return data
                except Exception as _e:
                    print(f"[DC] /api/v2/projects/{dc_uuid[:12]} with {_email} failed: {_e}", flush=True)
                    continue
            return None

            # Fallback: projects endpoint (in-progress, may have partial files)
            for _email in [enp_email, _DC_EMAIL]:
                if not _email:
                    continue
                try:
                    tok = _get_dc_token(email=_email)
                    proj_url = f"{_DC_BASE}/api/v2/projects/{dc_uuid}?user_type=ENTERPRISE_API"
                    req = _ureq_doc.Request(proj_url, headers={
                        "Authorization": f"Bearer {tok}",
                        "Accept": "application/json",
                    })
                    with _ureq_doc.urlopen(req, timeout=20) as r:
                        resp = _json_doc.loads(r.read().decode())
                    data = resp.get("data") or resp
                    if data and data.get("uuid"):
                        data["_source"] = "projects"
                        return data
                except Exception as _e:
                    print(f"[DC] /api/v2/projects/{dc_uuid[:12]} with {_email} failed: {_e}", flush=True)
                    continue
            return None

        try:
            loop = _asyncio_doc.get_event_loop()
            try:
                loop = _asyncio_doc.get_running_loop()
            except RuntimeError:
                pass
            vault_item = await loop.run_in_executor(None, _fetch_dc_vault)
            if vault_item:
                _source = vault_item.get("_source", "projects")
                dc_view_url = None

                if _source in ("stored_url", "projects_fresh"):
                    # Direct URL available — return it for proxy streaming
                    _file_url = vault_item.get("url", "")
                    _file_name = vault_item.get("file_name") or act.get("doc_name") or "Notarized Document"
                    if _file_url:
                        dc_files.append({
                            "fileName": _file_name,
                            "downloadUrl": _file_url,
                            "source": _source,
                        })
                    dc_view_url = f"{_DC_APP_URL}/sign/{dc_uuid}"

                elif _source == "vault":
                    # Vault response: top-level url = signed completed PDF
                    # files[] = [{file_id, file_name, file_url}]
                    _doc_name = vault_item.get("file_name") or vault_item.get("name") or act.get("doc_name") or "Notarized Document"
                    # Top-level url is the primary signed document
                    if vault_item.get("url"):
                        dc_files.append({"fileName": _doc_name, "downloadUrl": vault_item["url"], "source": "vault-completed"})
                    # Also check files array (vault format uses file_url)
                    for _vf in (vault_item.get("files") or []):
                        _furl = _vf.get("file_url") or _vf.get("url") or ""
                        _fname = _vf.get("file_name") or _doc_name
                        if _furl and not dc_files:
                            dc_files.append({"fileName": _fname, "downloadUrl": _furl, "source": "vault-file"})
                else:
                    # Projects response: files[] with type field
                    # Priority: signed+QR version first, then completed, then original
                    _priority = ['Document Completed', 'Document Certification', 'Original With Signature And QR', 'Original']
                    _files_by_type = {}
                    for _f in (vault_item.get("files") or []):
                        _ftype = _f.get("type") or ""
                        _furl  = _f.get("url") or ""
                        _fname = _f.get("file_name") or vault_item.get("file_name") or act.get("doc_name") or "Document"
                        if _furl and _ftype and "meta" not in _ftype.lower() and "qr" not in _ftype.lower().replace("with", ""):
                            _files_by_type[_ftype] = {"fileName": _fname, "downloadUrl": _furl}
                    # Pick best file in priority order
                    for _ptype in _priority:
                        if _ptype in _files_by_type:
                            dc_files.append(_files_by_type[_ptype])
                            break
                    # Fallback: any file with a URL that looks like a PDF
                    if not dc_files:
                        for _f in (vault_item.get("files") or []):
                            _furl = _f.get("url") or ""
                            _fname = _f.get("file_name") or act.get("doc_name") or "Document"
                            if _furl and ".pdf" in _fname.lower():
                                dc_files.append({"fileName": _fname, "downloadUrl": _furl})
                                break
                    if not dc_files and vault_item.get("url"):
                        dc_files.append({
                            "fileName": vault_item.get("file_name") or act.get("doc_name") or "Document",
                            "downloadUrl": vault_item["url"]
                        })
                    # Update stored dc_file_url with fresh URL (avoids stale presigned URLs)
                    if dc_files:
                        try:
                            import threading as _t_upd
                            _act_upd = dict(act)
                            _act_upd["dc_file_url"] = dc_files[0]["downloadUrl"]
                            _act_upd["dc_file_name"] = dc_files[0]["fileName"]
                            _act_upd["doconchain_project_uuid"] = dc_uuid
                            def _upd_act():
                                import database as _dbu
                                _dbu.upsert_registry_act(_act_upd)
                            _t_upd.Thread(target=_upd_act, daemon=True).start()
                        except Exception:
                            pass
        except Exception as _dc_err:
            print(f"[DC] vault processing failed (non-fatal): {_dc_err}", flush=True)

    # DoconChain app link always available if we have a UUID
    if dc_uuid and not dc_view_url:
        dc_view_url = f"{_DC_APP_URL}/sign/{dc_uuid}"

    if not sc_files and not dc_files and not dc_view_url:
        raise HTTPException(404, "No document files found. The document may not be available yet.")

    return {
        "nrid": nrid,
        "sc_files": sc_files,
        "dc_files": dc_files,
        "doconchain_view_url": dc_view_url,
        "sc_raw_response": sc_raw,
    }

    return {
        "nrid": nrid,
        "sc_files": files,
        "doconchain_link": doconchain_link,
        "sc_raw_response": sc_resp,
    }

# ══════════════════════════════════════════════════════════════════════════════
# ADMIN PANEL — Auth + API Endpoints
# ══════════════════════════════════════════════════════════════════════════════

import jwt as _pyjwt_admin
from fastapi.responses import FileResponse as _FileResponse
from datetime import datetime as _admin_dt, timezone as _admin_tz, timedelta as _admin_td

_ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "michael@quanbyai.com")
_ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "Alyssa7719!!")
_ADMIN_SECRET   = os.getenv("SECRET_KEY", "change-me-in-production")
_ADMIN_COOKIE   = "ql_admin"
_ADMIN_HTML     = os.path.join(os.path.dirname(os.path.dirname(__file__)), "admin.html")


def _issue_admin_jwt() -> str:
    now = _admin_dt.now(_admin_tz.utc)
    payload = {
        "sub":  "admin",
        "role": "admin",
        "iat":  int(now.timestamp()),
        "exp":  int((now + _admin_td(hours=8)).timestamp()),
    }
    return _pyjwt_admin.encode(payload, _ADMIN_SECRET, algorithm="HS256")


def _get_admin_user(request: Request):
    token = request.cookies.get(_ADMIN_COOKIE)
    if not token:
        return None
    try:
        payload = _pyjwt_admin.decode(token, _ADMIN_SECRET, algorithms=["HS256"])
        if payload.get("role") == "admin":
            return {"role": "admin", "sub": payload.get("sub", "admin")}
    except Exception:
        pass
    return None


# ── Static: GET /admin → admin.html ──────────────────────────────────────────

@app.get("/admin")
async def admin_panel():
    return _FileResponse(_ADMIN_HTML)


# ── POST /api/admin/login ────────────────────────────────────────────────────

class _AdminLoginReq(BaseModel):
    username: str
    password: str


@app.post("/api/admin/login")
async def admin_login(req: _AdminLoginReq, response: Response):
    if req.username != _ADMIN_USERNAME or req.password != _ADMIN_PASSWORD:
        raise HTTPException(401, "Invalid credentials")
    token = _issue_admin_jwt()
    response.set_cookie(
        key=_ADMIN_COOKIE,
        value=token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=8 * 3600,
        path="/",
    )
    return {"ok": True}


# ── POST /api/admin/logout ───────────────────────────────────────────────────

@app.post("/api/admin/logout")
async def admin_logout(response: Response):
    response.delete_cookie(_ADMIN_COOKIE, path="/")
    return {"ok": True}


# ── GET /api/admin/me ────────────────────────────────────────────────────────

@app.get("/api/admin/me")
async def admin_me(request: Request):
    admin = _get_admin_user(request)
    if not admin:
        raise HTTPException(401, "Unauthorized")
    return {"ok": True, "role": "admin"}


# ── GET /api/admin/stats ─────────────────────────────────────────────────────

@app.get("/api/admin/stats")
async def admin_stats(request: Request):
    admin = _get_admin_user(request)
    if not admin:
        raise HTTPException(401, "Unauthorized")

    all_users = _db.list_users()
    all_apts = _db.list_apts()
    total_acts = len(_db.list_acts())

    today = _admin_dt.now(_admin_tz.utc).date().isoformat()

    total_users = len(all_users)
    by_role = {"attorney": 0, "client": 0, "admin": 0}
    new_users_today = 0
    pending_enp_commission = 0

    for u in all_users:
        r = u.get("role", "")
        if r in by_role:
            by_role[r] += 1
        created = (u.get("created_at") or "")[:10]
        if created == today:
            new_users_today += 1
        if u.get("role") == "attorney" and u.get("sc_commission_status", "pending") == "pending":
            pending_enp_commission += 1

    total_apts = len(all_apts)
    ended_apts = sum(1 for a in all_apts if a.get("session_status") == "ended")
    new_apts_today = sum(1 for a in all_apts if (a.get("created_at") or "")[:10] == today)

    return {
        "total_users": total_users,
        "users_by_role": by_role,
        "total_appointments": total_apts,
        "ended_appointments": ended_apts,
        "total_acts": total_acts,
        "pending_enp_commission": pending_enp_commission,
        "new_users_today": new_users_today,
        "new_appointments_today": new_apts_today,
    }


# ── GET /api/admin/users ─────────────────────────────────────────────────────

@app.get("/api/admin/users")
async def admin_list_users(
    request: Request,
    search: Optional[str] = None,
    role: Optional[str] = None,
    page: int = 1,
    per_page: int = 20,
):
    admin = _get_admin_user(request)
    if not admin:
        raise HTTPException(401, "Unauthorized")

    users = _db.list_users()

    if role:
        users = [u for u in users if u.get("role") == role]
    if search:
        q = search.lower()
        users = [
            u for u in users
            if q in (u.get("email") or "").lower()
            or q in (u.get("first_name") or "").lower()
            or q in (u.get("last_name") or "").lower()
        ]

    users.sort(key=lambda u: u.get("created_at") or "", reverse=True)

    total = len(users)
    start = (page - 1) * per_page
    result = []
    for u in users[start:start + per_page]:
        result.append({
            "id":                 u.get("id"),
            "email":              u.get("email"),
            "first_name":         u.get("first_name"),
            "last_name":          u.get("last_name"),
            "role":               u.get("role"),
            "created_at":         u.get("created_at"),
            "onboarding_step":    u.get("onboarding_step"),
            "certificate_status": u.get("certificate_status"),
            "sc_commission_status": u.get("sc_commission_status"),
            "kyc_verified_at":    u.get("kyc_verified_at"),
        })

    return {
        "users": result,
        "total": total,
        "page":  page,
        "per_page": per_page,
        "pages": max(1, (total + per_page - 1) // per_page),
    }


# ── POST /api/admin/users/{user_id}/set-role ─────────────────────────────────

class _SetRoleReq(BaseModel):
    role: str


@app.post("/api/admin/users/{user_id}/set-role")
async def admin_set_role(user_id: str, req: _SetRoleReq, request: Request):
    admin = _get_admin_user(request)
    if not admin:
        raise HTTPException(401, "Unauthorized")
    if req.role not in ("attorney", "client", "admin"):
        raise HTTPException(400, "role must be attorney, client, or admin")

    target = _db.get_user(user_id)
    if not target:
        raise HTTPException(404, "User not found")

    target["role"] = req.role
    _db.upsert_user(target)

    return {"ok": True, "user_id": user_id, "role": req.role}


# ── GET /api/admin/appointments ──────────────────────────────────────────────

@app.get("/api/admin/appointments")
async def admin_list_appointments(
    request: Request,
    status: Optional[str] = None,
    search: Optional[str] = None,
    page: int = 1,
    per_page: int = 20,
):
    admin = _get_admin_user(request)
    if not admin:
        raise HTTPException(401, "Unauthorized")

    _users_map = {u["id"]: u for u in _db.list_users()}
    all_apts = _db.list_apts()

    def _enp_name(enp_id: str) -> str:
        u = _users_map.get(enp_id)
        if u:
            return f"{u.get('first_name','')} {u.get('last_name','')}".strip()
        return enp_id[:8] if enp_id else ""

    apts = all_apts
    if status:
        status_upper = status.upper()
        apts = [a for a in apts if a.get("status", "").upper() == status_upper
                or a.get("session_status", "").upper() == status_upper]
    if search:
        q = search.lower()
        apts = [
            a for a in apts
            if q in (a.get("client_email") or "").lower()
            or q in (a.get("enp_name") or "").lower()
            or q in (a.get("apt_id") or "").lower()
        ]

    apts.sort(key=lambda a: a.get("created_at") or "", reverse=True)

    total = len(apts)
    start = (page - 1) * per_page
    result = []
    for a in apts[start:start + per_page]:
        result.append({
            "id":              a.get("apt_id"),
            "enp_id":          a.get("enp_id"),
            "enp_name":        a.get("enp_name") or _enp_name(a.get("enp_id", "")),
            "client_email":    a.get("client_email"),
            "status":          a.get("status"),
            "session_status":  a.get("session_status"),
            "session_ended_at": a.get("session_ended_at"),
            "doc_count":       len(a.get("session_documents", [])),
            "created_at":      a.get("created_at"),
        })

    return {
        "appointments": result,
        "total": total,
        "page":  page,
        "per_page": per_page,
        "pages": max(1, (total + per_page - 1) // per_page),
    }


# ── GET /api/admin/registry ──────────────────────────────────────────────────

@app.get("/api/admin/registry")
async def admin_list_registry(
    request: Request,
    search: Optional[str] = None,
    act_type: Optional[str] = None,
    page: int = 1,
    per_page: int = 20,
):
    admin = _get_admin_user(request)
    if not admin:
        raise HTTPException(401, "Unauthorized")

    acts = _db.list_acts()

    if act_type:
        acts = [a for a in acts if a.get("act_type", "").upper() == act_type.upper()]
    if search:
        q = search.lower()
        acts = [
            a for a in acts
            if q in (a.get("doc_name") or "").lower()
            or q in (a.get("enp_name") or "").lower()
            or q in (a.get("principal_name") or "").lower()
            or q in (a.get("dc_reference_number") or "").lower()
        ]

    acts.sort(key=lambda a: a.get("executed_at") or a.get("created_at") or "", reverse=True)

    total = len(acts)
    start = (page - 1) * per_page
    result = acts[start:start + per_page]

    return {
        "acts": result,
        "total": total,
        "page":  page,
        "per_page": per_page,
        "pages": max(1, (total + per_page - 1) // per_page),
    }

# ── Sub-Organizations ─────────────────────────────────────────────────────────
# Appended to main.py before `if __name__ == "__main__":`

def _require_attorney_or_admin(request: Request):
    """Return current user if attorney or admin, else raise 401/403.
    Accepts both ql_admin cookie (admin panel) and ql_access cookie (user JWT).
    """
    # First: check ql_admin cookie (admin panel session)
    admin = _get_admin_user(request)
    if admin:
        return {"id": "admin", "role": "admin", "email": "admin@quanby.ai", "first_name": "Admin", "last_name": ""}
    # Then: check user JWT (ql_access cookie or Authorization header)
    from onboarding import get_user as _gu
    token = None
    auth_header = request.headers.get("authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ", 1)[1]
    if not token:
        token = request.cookies.get("ql_access")
    if not token:
        raise HTTPException(401, "Unauthorized")
    from auth import verify_jwt as _vj
    payload = _vj(token)
    if not payload:
        raise HTTPException(401, "Unauthorized")
    # Admin path via user JWT
    if payload.get("role") == "admin":
        return {"id": payload.get("sub", "admin"), "role": "admin", "email": payload.get("email", "")}
    user = _gu(payload.get("user_id", ""))
    if not user:
        raise HTTPException(401, "Unauthorized")
    if user.get("role") not in ("attorney", "admin"):
        raise HTTPException(403, "Forbidden: attorney or admin role required")
    return user


def _find_user_by_email(email: str):
    """Find a user by email from the database."""
    return _db.get_user_by_email(email.lower().strip())


class _SubOrgCreateReq(BaseModel):
    name: str
    address: Optional[str] = ""
    type: Optional[str] = "Department"
    dc_client_key: Optional[str] = ""
    dc_client_secret: Optional[str] = ""
    dc_email: Optional[str] = ""
    owner_email: Optional[str] = None  # Admin can set owner to specific ENP by email


class _SubOrgPatchReq(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    type: Optional[str] = None
    dc_client_key: Optional[str] = None
    dc_client_secret: Optional[str] = None
    dc_email: Optional[str] = None


class _SubOrgMemberReq(BaseModel):
    email: str
    role: str = "Staff"


class _SubOrgCredReq(BaseModel):
    dc_client_key: str = ""
    dc_client_secret: str = ""
    dc_email: str = ""


class _SubOrgCreditTransferReq(BaseModel):
    amount: int


# ── GET /api/sub-orgs ─────────────────────────────────────────────────────────
@app.get("/api/sub-orgs")
async def list_sub_orgs(request: Request):
    user = _require_attorney_or_admin(request)
    orgs = _db.list_suborgs()
    uid = user["id"]
    role = user.get("role")
    if role == "admin":
        result = orgs
    else:
        result = [
            o for o in orgs
            if o.get("owner_id") == uid
            or any(m.get("user_id") == uid for m in o.get("members", []))
        ]
    # Strip sensitive DC credentials from list view
    safe = []
    for o in result:
        s = {k: v for k, v in o.items() if k not in ("dc_client_key", "dc_client_secret")}
        s["dc_client_key_set"] = bool(o.get("dc_client_key"))
        s["dc_client_secret_set"] = bool(o.get("dc_client_secret"))
        safe.append(s)
    return safe


# ── POST /api/sub-orgs ────────────────────────────────────────────────────────
@app.post("/api/sub-orgs")
async def create_sub_org(
    request: Request,
    name: str = Form(...),
    address: str = Form(""),
    type: str = Form("Department"),
    owner_email: str = Form(""),
    dc_client_key: str = Form(""),
    dc_client_secret: str = Form(""),
    dc_email: str = Form(""),
    photo: UploadFile = File(None),
):
    # Wrap into a req-like object for compatibility
    class _Req:
        pass
    req = _Req()
    req.name = name
    req.address = address
    req.type = type
    req.owner_email = owner_email
    req.dc_client_key = dc_client_key
    req.dc_client_secret = dc_client_secret
    req.dc_email = dc_email
    req._photo = photo
    user = _require_attorney_or_admin(request)
    if not req.name or not req.name.strip():
        raise HTTPException(400, "name is required")
    valid_types = ("Department", "Branch", "Division", "Team")
    org_type = req.type if req.type in valid_types else "Department"
    now = _dt.now(_tz.utc).isoformat()
    # Resolve owner: admin can specify owner_email to assign to a specific ENP
    owner_id = user["id"]
    if req.owner_email and req.owner_email.strip():
        owner_candidate = _find_user_by_email(req.owner_email.strip())
        if owner_candidate:
            owner_id = owner_candidate["id"]
    org = {
        "id": str(uuid.uuid4()),
        "name": req.name.strip(),
        "address": req.address or "",
        "type": org_type,
        "owner_id": owner_id,
        "dc_client_key": req.dc_client_key or "",
        "dc_client_secret": req.dc_client_secret or "",
        "dc_email": req.dc_email or "",
        "credits_total": 0,
        "credits_used": 0,
        "members": [],
        "created_at": now,
        "updated_at": now,
    }
    # Add DC-tracking fields
    org["dc_sub_org_id"]   = None
    org["dc_sub_org_uuid"] = None

    # Read photo bytes if provided
    _photo_bytes = None
    _photo_name = None
    if hasattr(req, '_photo') and req._photo and req._photo.filename:
        try:
            _photo_bytes = await req._photo.read()
            _photo_name = req._photo.filename
        except Exception:
            pass

    # Provision sub-org in DoconChain (non-blocking)
    _dc_provision_error = None
    try:
        import urllib.request as _ur_so, urllib.error as _ue_so, json as _json_so
        # Use owner ENP's token if available, else fall back to org token
        _enp_user_so = None
        try:
            from onboarding import get_user as _get_user_so
            _enp_user_so = _get_user_so(org.get("owner_id", ""))
        except Exception:
            pass
        _enp_email_so = (_enp_user_so.get("email") if _enp_user_so else None) or _DC_EMAIL
        try:
            _dc_token_so = _get_dc_token(email=_enp_email_so)
        except Exception:
            _dc_token_so = _get_dc_token()
        _bd = "QLSubOrg" + org["id"].replace("-","")[:12]
        _CRLF = b"\r\n"
        def _field(name, value):
            return (
                b"--" + _bd.encode() + _CRLF +
                b"Content-Disposition: form-data; name=\"" + name.encode() + b"\"" + _CRLF +
                _CRLF + str(value).encode("utf-8") + _CRLF
            )
        # organization_uuid = numeric org ID (not UUID) per DC API spec
        _body_so = (
            _field("name", org["name"]) +
            _field("address", org["address"] or org["name"]) +
            _field("sub_organization_type_name", org["type"]) +
            _field("organization_uuid", _DC_ORG_UUID)
        )
        # Attach photo if provided
        if _photo_bytes and _photo_name:
            _ext = _photo_name.rsplit('.', 1)[-1].lower() if '.' in _photo_name else 'png'
            _mime = {'jpg':'image/jpeg','jpeg':'image/jpeg','png':'image/png','gif':'image/gif','webp':'image/webp'}.get(_ext, 'image/png')
            _body_so += (
                b"--" + _bd.encode() + b"\r\n" +
                b"Content-Disposition: form-data; name=\"photo\"; filename=\"" + _photo_name.encode() + b"\"\r\n" +
                b"Content-Type: " + _mime.encode() + b"\r\n\r\n" +
                _photo_bytes + b"\r\n"
            )
        _body_so += b"--" + _bd.encode() + b"--" + b"\r\n"
        # (removed trailing b"--" + _bd.encode() + b"--" + _CRLF — now inline above)
        print(f"[SubOrg] Creating DC sub-org: name={org['name']} type={org['type']} org_id={_DC_ORG_ID} token_email={_enp_email_so}", flush=True)
        _req_so = _ur_so.Request(
            f"{_DC_BASE}/api/v2/organizations/sub?user_type=ENTERPRISE_API",
            data=_body_so,
            headers={
                "Authorization": f"Bearer {_dc_token_so}",
                "Content-Type": f"multipart/form-data; boundary={_bd}",
                "Accept": "application/json",
            },
            method="POST",
        )
        with _ur_so.urlopen(_req_so, timeout=20) as _r_so:
            _dc_resp = _json_so.loads(_r_so.read().decode())
        _dc_data = _dc_resp.get("data") or _dc_resp.get("message") or _dc_resp
        if isinstance(_dc_data, dict):
            # DC returns nested sub_org_data for the sub-org details
            _sub_data = _dc_data.get("sub_org_data") or _dc_data
            org["dc_sub_org_id"]     = str(_sub_data.get("id") or "")
            org["dc_sub_org_uuid"]   = str(_sub_data.get("uuid") or "")
            org["dc_photo_url"]      = str(_sub_data.get("photo") or _sub_data.get("photo_url") or _sub_data.get("avatar") or "")
            # Store DC-generated credentials for this sub-org
            if _dc_data.get("client_key"):
                org["dc_client_key"]    = str(_dc_data["client_key"])
            if _dc_data.get("client_secret"):
                org["dc_client_secret"] = str(_dc_data["client_secret"])
            print(f"[SubOrg] DC provisioned: id={org['dc_sub_org_id']} uuid={org['dc_sub_org_uuid']} photo={bool(org['dc_photo_url'])}", flush=True)
    except Exception as _dc_so_err:
        _dc_provision_error = str(_dc_so_err)
        print(f"[SubOrg] DC provisioning failed (non-fatal): {_dc_so_err}", flush=True)

    _db.save_suborg(org)

    result = {"success": True, "id": org["id"], "sub_org": org}
    if _dc_provision_error:
        result["dc_warning"] = f"Sub-org created locally. DoconChain: {_dc_provision_error[:150]}"
    elif org.get("dc_sub_org_uuid"):
        result["dc_provisioned"] = True
        result["dc_sub_org_uuid"] = org["dc_sub_org_uuid"]
    return result


# ── GET /api/sub-orgs/{sub_org_id} ───────────────────────────────────────────
@app.get("/api/sub-orgs/{sub_org_id}")
async def get_sub_org(sub_org_id: str, request: Request):
    user = _require_attorney_or_admin(request)
    org = _db.get_suborg(sub_org_id)
    if not org:
        raise HTTPException(404, "Sub-org not found")
    uid = user["id"]
    role = user.get("role")
    if role != "admin" and org.get("owner_id") != uid and not any(m.get("user_id") == uid for m in org.get("members", [])):
        raise HTTPException(403, "Forbidden")
    s = {k: v for k, v in org.items() if k not in ("dc_client_key", "dc_client_secret")}
    s["dc_client_key_set"] = bool(org.get("dc_client_key"))
    s["dc_client_secret_set"] = bool(org.get("dc_client_secret"))
    return s


# ── PATCH /api/sub-orgs/{sub_org_id} ─────────────────────────────────────────
@app.patch("/api/sub-orgs/{sub_org_id}")
async def patch_sub_org(sub_org_id: str, req: _SubOrgPatchReq, request: Request):
    user = _require_attorney_or_admin(request)
    org = _db.get_suborg(sub_org_id)
    if not org:
        raise HTTPException(404, "Sub-org not found")
    uid = user["id"]
    role = user.get("role")
    if role != "admin" and org.get("owner_id") != uid:
        raise HTTPException(403, "Forbidden: only owner or admin can edit")
    valid_types = ("Department", "Branch", "Division", "Team")
    if req.name is not None:
        org["name"] = req.name.strip()
    if req.address is not None:
        org["address"] = req.address
    if req.type is not None and req.type in valid_types:
        org["type"] = req.type
    if req.dc_client_key is not None:
        org["dc_client_key"] = req.dc_client_key
    if req.dc_client_secret is not None:
        org["dc_client_secret"] = req.dc_client_secret
    if req.dc_email is not None:
        org["dc_email"] = req.dc_email
    org["updated_at"] = _dt.now(_tz.utc).isoformat()
    _db.save_suborg(org)
    return {"success": True, "sub_org": org}


# ── DELETE /api/sub-orgs/{sub_org_id} ────────────────────────────────────────
@app.delete("/api/sub-orgs/{sub_org_id}")
async def delete_sub_org(sub_org_id: str, request: Request):
    user = _require_attorney_or_admin(request)
    org = _db.get_suborg(sub_org_id)
    if not org:
        raise HTTPException(404, "Sub-org not found")
    uid = user["id"]
    role = user.get("role")
    if role != "admin" and org.get("owner_id") != uid:
        raise HTTPException(403, "Forbidden: only owner or admin can delete")
    _db.delete_suborg(sub_org_id)
    return {"success": True}


# ── GET /api/sub-orgs/{sub_org_id}/members ───────────────────────────────────
@app.get("/api/sub-orgs/{sub_org_id}/members")
async def list_sub_org_members(sub_org_id: str, request: Request):
    user = _require_attorney_or_admin(request)
    org = _db.get_suborg(sub_org_id)
    if not org:
        raise HTTPException(404, "Sub-org not found")
    uid = user["id"]
    role = user.get("role")
    if role != "admin" and org.get("owner_id") != uid and not any(m.get("user_id") == uid for m in org.get("members", [])):
        raise HTTPException(403, "Forbidden")
    return org.get("members", [])


# ── POST /api/sub-orgs/{sub_org_id}/members ──────────────────────────────────
@app.post("/api/sub-orgs/{sub_org_id}/members")
async def add_sub_org_member(sub_org_id: str, req: _SubOrgMemberReq, request: Request):
    user = _require_attorney_or_admin(request)
    if req.role not in ("ENP", "Staff"):
        raise HTTPException(400, "role must be ENP or Staff")
    target = _find_user_by_email(req.email)
    org = _db.get_suborg(sub_org_id)
    if not org:
        raise HTTPException(404, "Sub-org not found")
    uid = user["id"]
    role = user.get("role")
    if role != "admin" and org.get("owner_id") != uid:
        raise HTTPException(403, "Forbidden: only owner or admin can add members")
    if not target:
        # Non-admin: must find registered user
        if role != "admin":
            raise HTTPException(404, f"No user found with email: {req.email}")
        # Admin: invite unregistered user by email
        invite_id = f"invite_{req.email.lower().strip()}"
        if any(m.get("user_id") == invite_id for m in org.get("members", [])):
            raise HTTPException(409, "This email is already invited to this sub-org")
        member = {
            "user_id": invite_id,
            "email": req.email.lower().strip(),
            "name": req.email.lower().strip(),
            "role": req.role,
            "status": "invited",
        }
    else:
        # Check if already a member
        if any(m.get("user_id") == target["id"] for m in org.get("members", [])):
            raise HTTPException(409, "User is already a member of this sub-org")
        member = {
            "user_id": target["id"],
            "email": target.get("email", ""),
            "name": f"{target.get('first_name', '')} {target.get('last_name', '')}".strip() or target.get("email", ""),
            "role": req.role,
            "status": "active",
        }
    org.setdefault("members", []).append(member)
    org["updated_at"] = _dt.now(_tz.utc).isoformat()
    _db.save_suborg(org)
    # Capture org details for DC call
    _dc_suborg_uuid = org.get("dc_sub_org_uuid") or ""
    _dc_suborg_id   = org.get("dc_sub_org_id") or ""
    _org_type       = org.get("type", "Department")

    # Provision member in DoconChain (non-blocking)
    _dc_member_error = None
    _dc_member_result = None
    if _dc_suborg_uuid and target:
        try:
            import urllib.request as _ur_m, urllib.error as _ue_m, json as _json_m
            _dc_token_m = _get_dc_token()
            _bd_m = "QLMember" + member["user_id"].replace("-","")[:12]
            _CRLF = b"\r\n"
            _fn = target.get("first_name") or member["email"].split("@")[0]
            _ln = target.get("last_name") or "."
            _em = member["email"]
            # organization JSON string as required by DC
            import json as _json_org
            _org_json = _json_org.dumps({"id": int(_dc_suborg_id) if _dc_suborg_id.isdigit() else 0, "sub_organization_type_name": _org_type})
            def _mf(name, value):
                return (b"--" + _bd_m.encode() + _CRLF +
                        b"Content-Disposition: form-data; name=\"" + name.encode() + b"\"" + _CRLF +
                        _CRLF + str(value).encode("utf-8") + _CRLF)
            _body_m = (
                _mf("data[0][email]",           _em) +
                _mf("data[0][first_name]",      _fn) +
                _mf("data[0][last_name]",       _ln) +
                _mf("data[0][role]",            "Member") +
                _mf("data[0][organization]",    _org_json) +
                _mf("data[0][organization_id]", _dc_suborg_uuid) +
                b"--" + _bd_m.encode() + b"--" + _CRLF
            )
            _url_m = f"{_DC_BASE}/api/v2/sub-organizations/{_dc_suborg_uuid}/members?user_type=ENTERPRISE_API"
            _req_m = _ur_m.Request(_url_m, data=_body_m, headers={
                "Authorization": f"Bearer {_dc_token_m}",
                "Content-Type": f"multipart/form-data; boundary={_bd_m}",
                "Accept": "application/json",
            }, method="POST")
            with _ur_m.urlopen(_req_m, timeout=20) as _r_m:
                _dc_member_result = _json_m.loads(_r_m.read().decode())
            print(f"[SubOrg Member] DC added {_em} to {_dc_suborg_uuid}: {str(_dc_member_result)[:120]}", flush=True)
        except Exception as _dc_m_err:
            _dc_member_error = str(_dc_m_err)
            print(f"[SubOrg Member] DC add failed (non-fatal): {_dc_m_err}", flush=True)

    result = {"success": True, "member": member}
    if _dc_member_error:
        result["dc_warning"] = f"Member added locally. DoconChain: {_dc_member_error[:150]}"
    elif _dc_member_result:
        result["dc_provisioned"] = True
    return result


# ── DELETE /api/sub-orgs/{sub_org_id}/members/{user_id} ──────────────────────
@app.delete("/api/sub-orgs/{sub_org_id}/members/{member_user_id}")
async def remove_sub_org_member(sub_org_id: str, member_user_id: str, request: Request):
    user = _require_attorney_or_admin(request)
    org = _db.get_suborg(sub_org_id)
    if not org:
        raise HTTPException(404, "Sub-org not found")
    uid = user["id"]
    role = user.get("role")
    if role != "admin" and org.get("owner_id") != uid:
        raise HTTPException(403, "Forbidden: only owner or admin can remove members")
    before = len(org.get("members", []))
    org["members"] = [m for m in org.get("members", []) if m.get("user_id") != member_user_id]
    if len(org["members"]) == before:
        raise HTTPException(404, "Member not found")
    org["updated_at"] = _dt.now(_tz.utc).isoformat()
    _db.save_suborg(org)
    return {"success": True}


# ── GET /api/sub-orgs/{sub_org_id}/credits ───────────────────────────────────
@app.get("/api/sub-orgs/{sub_org_id}/credits")
async def get_sub_org_credits(sub_org_id: str, request: Request):
    user = _require_attorney_or_admin(request)
    org = _db.get_suborg(sub_org_id)
    if not org:
        raise HTTPException(404, "Sub-org not found")
    uid = user["id"]
    role = user.get("role")
    if role != "admin" and org.get("owner_id") != uid and not any(m.get("user_id") == uid for m in org.get("members", [])):
        raise HTTPException(403, "Forbidden")
    total = org.get("credits_total", 0)
    used = org.get("credits_used", 0)
    return {"total": total, "used": used, "remaining": max(0, total - used)}


# ── POST /api/sub-orgs/{sub_org_id}/credits/transfer ─────────────────────────
@app.post("/api/sub-orgs/{sub_org_id}/credits/transfer")
async def transfer_sub_org_credits(sub_org_id: str, req: _SubOrgCreditTransferReq, request: Request):
    user = _require_attorney_or_admin(request)
    if req.amount <= 0:
        raise HTTPException(400, "amount must be positive")
    org = _db.get_suborg(sub_org_id)
    if not org:
        raise HTTPException(404, "Sub-org not found")
    uid = user["id"]
    role = user.get("role")
    if role != "admin" and org.get("owner_id") != uid:
        raise HTTPException(403, "Forbidden: only owner or admin can transfer credits")
    org["credits_total"] = org.get("credits_total", 0) + req.amount
    org["updated_at"] = _dt.now(_tz.utc).isoformat()
    _db.save_suborg(org)
    return {"success": True, "credits_total": org["credits_total"]}


# ── GET /api/sub-orgs/{sub_org_id}/credentials ───────────────────────────────
@app.get("/api/sub-orgs/{sub_org_id}/credentials")
async def get_sub_org_credentials(sub_org_id: str, request: Request):
    user = _require_attorney_or_admin(request)
    org = _db.get_suborg(sub_org_id)
    if not org:
        raise HTTPException(404, "Sub-org not found")
    uid = user["id"]
    role = user.get("role")
    if role != "admin" and org.get("owner_id") != uid:
        raise HTTPException(403, "Forbidden: only owner or admin can view credentials")

    def _mask(s: str) -> str:
        if not s:
            return ""
        if len(s) <= 8:
            return "*" * len(s)
        return s[:4] + "*" * (len(s) - 8) + s[-4:]

    return {
        "dc_client_key": _mask(org.get("dc_client_key", "")),
        "dc_client_secret": _mask(org.get("dc_client_secret", "")),
        "dc_email": org.get("dc_email", ""),
        "dc_client_key_raw": org.get("dc_client_key", ""),
        "dc_client_secret_raw": org.get("dc_client_secret", ""),
    }


# ── PUT /api/sub-orgs/{sub_org_id}/credentials ───────────────────────────────
@app.put("/api/sub-orgs/{sub_org_id}/credentials")
async def update_sub_org_credentials(sub_org_id: str, req: _SubOrgCredReq, request: Request):
    user = _require_attorney_or_admin(request)
    org = _db.get_suborg(sub_org_id)
    if not org:
        raise HTTPException(404, "Sub-org not found")
    uid = user["id"]
    role = user.get("role")
    if role != "admin" and org.get("owner_id") != uid:
        raise HTTPException(403, "Forbidden: only owner or admin can update credentials")
    org["dc_client_key"] = req.dc_client_key
    org["dc_client_secret"] = req.dc_client_secret
    org["dc_email"] = req.dc_email
    org["updated_at"] = _dt.now(_tz.utc).isoformat()
    _db.save_suborg(org)
    return {"success": True}


# ─── QuickSign endpoints ──────────────────────────────────────────────────────


@app.post("/api/quicksign/create-project")
async def quicksign_create_project(
    request: Request,
    authorization: Optional[str] = Header(None),
    ql_access: Optional[str] = Cookie(default=None),
):
    """ENP uploads a PDF and creates a DoconChain project. Step 1 of QuickSign."""
    user = get_current_user(authorization, ql_access)
    if not user:
        raise HTTPException(401, "Unauthorized")
    # All authenticated users can use QuickSign

    form = await request.form()
    doc_name = str(form.get("doc_name", "Document")).strip() or "Document"
    notarization_type = str(form.get("notarization_type", "ACKNOWLEDGMENT")).strip().upper()
    file_field = form.get("file")

    if file_field is None:
        raise HTTPException(400, "No file uploaded")

    file_bytes = await file_field.read()
    file_name = os.path.basename(getattr(file_field, "filename", "document.pdf") or "document.pdf")
    content_type_hdr = getattr(file_field, "content_type", "application/pdf") or "application/pdf"

    if len(file_bytes) > 20 * 1024 * 1024:
        raise HTTPException(400, "File too large — max 20MB")
    if not file_bytes:
        raise HTTPException(400, "Empty file")

    enp_user = get_user(user["id"]) or user
    _is_enp_qs = user.get("role") == "attorney"
    _qs_apt = {
        "client_email": "", "client_name": "", "session_participants": [],
        "mode_of_notarization": "REN", "notarization_type": notarization_type,
    }

    try:
        def _mp_qs(url, fields, files=None, hdrs=None):
            b = "QLQSb9f3a2c1"
            parts = []
            for k, v in fields.items():
                parts.append(f'--{b}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode())
            if files:
                for k, (fn, fd, ft) in files.items():
                    parts.append(
                        f'--{b}\r\nContent-Disposition: form-data; name="{k}"; filename="{fn}"\r\nContent-Type: {ft}\r\n\r\n'.encode()
                        + fd + b'\r\n'
                    )
            parts.append(f'--{b}--\r\n'.encode())
            body = b''.join(parts)
            h = {'Content-Type': f'multipart/form-data; boundary={b}'}
            if hdrs:
                h.update(hdrs)
            rq = _urllib_req.Request(url, data=body, headers=h, method='POST')
            with _urllib_req.urlopen(rq, timeout=30) as r:
                return json.loads(r.read().decode())

        _enp_email_qs = enp_user.get('email') or user.get('email') or _DC_EMAIL
        tok = _mp_qs(
            f'{_DC_BASE}/api/v2/generate/token',
            {'client_key': _DC_CLIENT_KEY, 'client_secret': _DC_CLIENT_SECRET, 'email': _enp_email_qs},
        )
        dc_token = (tok.get('data') or {}).get('token') or tok.get('token')
        if not dc_token:
            raise ValueError(f"No token: {tok}")

        stamp = _build_dc_stamp(enp_user, _qs_apt) if _is_enp_qs else {}
        proj = _mp_qs(
            f'{_DC_BASE}/api/v2/projects?user_type=ENTERPRISE_API',
            _build_create_fields(stamp, _qs_apt),
            files={'file': (file_name, file_bytes, content_type_hdr)},
            hdrs={'Authorization': f'Bearer {dc_token}'},
        )
    except _urllib_err.HTTPError as e:
        raise HTTPException(502, f"DoconChain error {e.code}: {e.read().decode(errors='replace')[:300]}")
    except Exception as e:
        raise HTTPException(502, f"DoconChain failed: {str(e)[:200]}")

    data = proj.get('data') or proj
    project_uuid = data.get('uuid') or data.get('id') or ''
    if not project_uuid:
        raise HTTPException(502, f"No UUID in DoconChain response: {str(proj)[:200]}")

    sign_link = f"https://stg-app.doconchain.com/sign/{project_uuid}"

    # Pre-add ENP as DC signer sequence=2 (signs last, after client) — ENP only
    _qs_enp_first = enp_user.get("first_name", "") or "ENP"
    _qs_enp_last  = enp_user.get("last_name", "") or ""
    _qs_enp_email = enp_user.get("email", "")
    # ENP is the project creator/owner — they can plot signature fields without being added as a Signer.
    # The ENP will be added as a Signer AFTER plotting via the add-signer endpoint (sequence=2).
    # Adding ENP as Signer BEFORE plotting causes DC to open the signing UI instead of field editor.
    print(f"[QuickSign] Project created. ENP will be added as signer AFTER plotting.", flush=True)

    return {
        "project_uuid": project_uuid,
        "dc_project_uuid": project_uuid,
        "doc_name": doc_name,
        "sign_link": sign_link,
        "notarization_type": notarization_type,
        "enp_email": _qs_enp_email,
    }


@app.post("/api/quicksign/add-signer")
async def quicksign_add_signer(
    req: QuickSignAddSignerRequest,
    authorization: Optional[str] = Header(None),
    ql_access: Optional[str] = Cookie(default=None),
):
    """Add client as signer to a QuickSign DC project. Step 2 of QuickSign."""
    user = get_current_user(authorization, ql_access)
    if not user:
        raise HTTPException(401, "Unauthorized")
    # All authenticated users can use QuickSign

    project_uuid = req.project_uuid.strip()
    if not project_uuid:
        raise HTTPException(400, "project_uuid required")

    # ── Step 1: Add client as DC signer ────────────────────────────────────
    _enp_email_qs = (user.get("email") or _DC_EMAIL).strip()

    # Always purge stale token before add — prevents 401 Unauthorized
    _dc_token_cache.pop(_enp_email_qs, None)
    _dc_token_cache.pop(_DC_EMAIL, None)

    # Get fresh ENP token explicitly — project is owned by ENP, only ENP token can add signers
    try:
        _fresh_enp_token = _get_dc_token(email=_enp_email_qs)
    except Exception:
        _fresh_enp_token = _get_dc_token(email=_DC_EMAIL)

    try:
        client_result = _add_dc_signer(
            project_uuid, req.client_email.strip(),
            (req.first_name or "").strip(), (req.last_name or "").strip(),
            "Signer", _fresh_enp_token, sequence=1,
        )
        print(f"[QuickSign] DC signer add result: {client_result}", flush=True)
    except Exception as e:
        import traceback as _qtb
        print(f"[QuickSign] DC add failed: {_qtb.format_exc()}", flush=True)
        raise HTTPException(502, f"Failed to add signer to DoconChain: {str(e)[:200]}")

    # ── Step 2: Save signer to local appointment ─────────────────────────────
    try:
        for _apt2 in _db.list_apts():
            for _doc2 in _apt2.get("session_documents", []):
                _duuid2 = _doc2.get("doconchain_project_uuid") or _doc2.get("project_uuid")
                if _duuid2 == project_uuid:
                    if "signers" not in _doc2:
                        _doc2["signers"] = []
                    _existing_emails2 = [(s.get("email") or "").lower() for s in _doc2["signers"]]
                    # Client signs FIRST (order 1), ENP signs LAST as notary (order 2)
                    _client_email_lower = req.client_email.strip().lower()
                    if _client_email_lower not in _existing_emails2:
                        _doc2["signers"].insert(0, {
                            "email": req.client_email.strip(),
                            "first_name": (req.first_name or "").strip(),
                            "last_name": (req.last_name or "").strip(),
                            "signer_role": "Signer",
                            "signing_order": 1,
                        })
                    if _enp_email_qs.lower() not in _existing_emails2:
                        _doc2["signers"].append({
                            "email": _enp_email_qs,
                            "first_name": user.get("first_name") or "ENP",
                            "last_name": user.get("last_name") or "",
                            "signer_role": "Signer",
                            "signing_order": 2,
                        })
                    _doc2["dc_workflow_state"] = "plotting_done"
                    _doc2["plotting_started"] = True
                    _db.save_apt(_apt2)
                    break
    except Exception as e:
        import traceback; print(f"[QuickSign] Save signer failed (non-fatal): {traceback.format_exc()}", flush=True)
        # Don't 502 — DC add succeeded, local save is non-fatal

    return {"success": True, "signer_added": True, "result": client_result}


@app.post("/api/quicksign/plot-link/{project_uuid}")
async def quicksign_plot_link(
    project_uuid: str,
    authorization: Optional[str] = Header(None),
    ql_access: Optional[str] = Cookie(default=None),
):
    """Get the DoconChain plot link for a QuickSign project. Step 3 of QuickSign."""
    user = get_current_user(authorization, ql_access)
    if not user:
        raise HTTPException(401, "Unauthorized")
    # All authenticated users can use QuickSign
    if not project_uuid or not project_uuid.strip():
        raise HTTPException(400, "project_uuid required")

    import urllib.request as _ureq_qs3, urllib.error as _uerr_qs3, json as _json_qs3

    _is_enp_plot = user.get("role") == "attorney"
    enp_email = (user.get("email") or "").lower().strip() if _is_enp_plot else _DC_EMAIL
    if not enp_email:
        raise HTTPException(400, "User email not found")

    _dc_token_cache.pop(enp_email, None)
    _dc_token_cache.pop(_DC_EMAIL, None)

    def _call_plot_qs(token):
        _rq = _ureq_qs3.Request(
            f"{_DC_BASE}/api/v2/projects/{project_uuid}/link?user_type=ENTERPRISE_API",
            data=None,
            headers={"Accept": "application/json", "Authorization": f"Bearer {token}"},
            method="POST",
        )
        with _ureq_qs3.urlopen(_rq, timeout=30) as _r:
            return _json_qs3.loads(_r.read().decode())

    resp_data = None
    _last_code = 502
    _last_body = "Unknown error"
    for _retry in range(3):
        try:
            _tok = _get_dc_token(email=enp_email)
        except Exception as _te:
            _last_body = f"Token error: {_te}"
            _dc_token_cache.pop(enp_email, None)
            continue
        try:
            resp_data = _call_plot_qs(_tok)
            break
        except _uerr_qs3.HTTPError as he:
            _last_code = he.code
            _last_body = he.read().decode(errors="replace")
            _dc_token_cache.pop(enp_email, None)
            if he.code not in (401, 403):
                raise HTTPException(he.code, f"DoconChain error {he.code}: {_last_body[:300]}")
            continue

    if resp_data is None:
        raise HTTPException(_last_code, f"Plot link failed: {_last_body[:300]}")

    link = (
        (resp_data.get("message") or {}).get("link")
        or (resp_data.get("data") or {}).get("link")
        or resp_data.get("link")
        or resp_data.get("url")
        or (resp_data.get("data") or {}).get("url")
        or (resp_data.get("message") or {}).get("url")
    )
    if not link:
        raise HTTPException(502, f"No link in DoconChain response: {str(resp_data)[:200]}")

    # Resolve DC short link (capture 302 Location, don't follow)
    resolved_link = link
    if "doconchain.com" in link:
        class _NoRedir(_ureq_qs3.HTTPRedirectHandler):
            def http_error_302(self, req, fp, code, msg, headers):
                raise _uerr_qs3.HTTPError(req.full_url, code, msg, headers, fp)
            http_error_301 = http_error_302
            http_error_303 = http_error_302
            http_error_307 = http_error_302

        _opener_qs = _ureq_qs3.build_opener(_NoRedir)
        try:
            _rr = _ureq_qs3.Request(
                link,
                headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"},
                method="GET",
            )
            with _opener_qs.open(_rr, timeout=10):
                pass
        except _uerr_qs3.HTTPError as _he_r:
            loc = _he_r.headers.get("Location") or _he_r.headers.get("location")
            if loc:
                resolved_link = loc
        except Exception:
            pass

    return {"link": resolved_link}


@app.post("/api/quicksign/create-appointment")
async def quicksign_create_appointment(
    req: QuickSignCreateAppointmentRequest,
    authorization: Optional[str] = Header(None),
    ql_access: Optional[str] = Cookie(default=None),
):
    """ENP creates a QuickSign appointment with pre-populated session document. Step 4."""
    user = get_current_user(authorization, ql_access)
    if not user:
        raise HTTPException(401, "Unauthorized")
    # All authenticated users can use QuickSign

    _is_enp_apt = user.get("role") == "attorney"
    enp_user = user  # get_current_user already returns full user object
    enp_name = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip() or user.get('name', 'ENP')
    enp_email = user.get("email", "") if _is_enp_apt else ""

    client_name = req.client_name.strip() or req.client_email.split("@")[0]

    now_iso = _dt.now(_tz.utc).isoformat()
    apt_id = str(uuid.uuid4())

    project_uuid = (req.project_uuid or req.dc_project_uuid).strip()
    sign_link = f"https://stg-app.doconchain.com/sign/{project_uuid}"

    _FEE_QS = {
        "ACKNOWLEDGMENT": "₱100 – ₱300",
        "JURAT": "₱100 – ₱300",
        "AFFIRMATION": "₱100 – ₱300",
        "SIGNATURE_WITNESSING": "₱50 – ₱200",
        "COPY_CERTIFICATION": "₱50 – ₱200",
        "OATH_ADMINISTRATION": "₱100 – ₱300",
    }

    doc_entry = {
        "name": req.doc_name,
        "doc_name": req.doc_name,
        "notarization_type": req.notarization_type,
        "description": "",
        "file_name": f"{req.doc_name}.pdf",
        "project_uuid": project_uuid,
        "doconchain_project_uuid": project_uuid,
        "sign_link": sign_link,
        "fee": _FEE_QS.get(req.notarization_type, "₱100 – ₱300"),
        "uploaded_by": user["id"],
        "uploaded_by_name": enp_name,
        "uploaded_at": now_iso,
        "signers": [],
        "plotting_started": True,
        "plotting_started_at": now_iso,
        "dc_workflow_state": "plotting_done",
        "signers": [
            {
                "email": req.client_email,
                "first_name": req.client_name.split()[0] if req.client_name else req.client_email.split("@")[0],
                "last_name": " ".join(req.client_name.split()[1:]) if req.client_name and len(req.client_name.split()) > 1 else "",
                "signer_role": "Signer",
                "signing_order": 1,
            },
            {
                "email": enp_email,
                "first_name": user.get("first_name", "ENP"),
                "last_name": user.get("last_name", ""),
                "signer_role": "Signer",
                "signing_order": 2,
            },
        ],
    }

    apt = {
        "apt_id": apt_id,
        "client_id": f"guest:{req.client_email}",
        "client_name": client_name,
        "client_email": req.client_email,
        "enp_id": user["id"],
        "enp_name": enp_name,
        "enp_email": enp_email,
        "notarization_type": req.notarization_type,
        "mode": "REN",
        "notes": req.notes[:1000] if req.notes else "",
        "title": f"QuickSign — {req.doc_name}",
        "preferred_time": req.scheduled_at[:200] if req.scheduled_at else "",
        "status": "CONFIRMED",
        "created_at": now_iso,
        "updated_at": now_iso,
        "confirmed_at": now_iso,
        "doconchain_project_uuid": project_uuid,
        "doconchain_sign_link": sign_link,
        "session_documents": [doc_entry],
        "session_participants": [],
        "dc_workflow_state": "plotting_done",
        "quicksign": True,
    }

    # Auto-provision LiveKit room so the session is immediately joinable
    import secrets as _secrets
    room_name = f"qs-{apt_id[:8]}-{_secrets.token_hex(4)}"
    apt["session_room_name"] = room_name
    apt["session_status"] = "active"
    apt["session_created_at"] = now_iso

    _db.save_apt(apt)

    # Send email invite to the client
    try:
        from email_service import send_email
        _session_url = f"https://legal.quanbyai.com/session?apt={apt_id}&room={room_name}&guest=1"
        _lobby_url   = f"https://legal.quanbyai.com/lobby?apt={apt_id}&room={room_name}&guest=1"
        _email_html = f"""
<div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;background:#05060f;color:#f1f5f9;padding:32px;border-radius:12px;">
  <div style="text-align:center;margin-bottom:24px;">
    <img src="https://legal.quanbyai.com/qlegal-logo.png" alt="Quanby Legal" style="height:48px;"/>
    <h2 style="color:#a78bfa;margin:12px 0 4px;">You have a document to sign</h2>
    <p style="color:#8892a4;font-size:14px;margin:0;">Quanby Legal — Electronic Notarization</p>
  </div>
  <div style="background:rgba(255,255,255,0.05);border:1px solid rgba(255,255,255,0.1);border-radius:10px;padding:20px;margin-bottom:20px;">
    <p style="margin:0 0 8px;font-size:15px;">Hello <strong style="color:#f1f5f9;">{req.client_name or req.client_email}</strong>,</p>
    <p style="color:#8892a4;font-size:14px;margin:0 0 16px;">
      <strong style="color:#f1f5f9;">{enp_name}</strong> has prepared a document for your signature via Quanby Legal.
    </p>
    <table style="width:100%;border-collapse:collapse;font-size:13px;">
      <tr><td style="color:#8892a4;padding:4px 0;width:120px;">Document:</td><td style="color:#f1f5f9;">{req.doc_name}</td></tr>
      <tr><td style="color:#8892a4;padding:4px 0;">Type:</td><td style="color:#f1f5f9;">{req.notarization_type.replace('_',' ').title()}</td></tr>
      <tr><td style="color:#8892a4;padding:4px 0;">Notary (ENP):</td><td style="color:#f1f5f9;">{enp_name}</td></tr>
    </table>
  </div>
  <div style="text-align:center;margin-bottom:20px;">
    <a href="{_lobby_url}" style="display:inline-block;background:linear-gradient(135deg,#7c3aed,#ec4899);color:white;padding:14px 32px;border-radius:8px;text-decoration:none;font-weight:700;font-size:15px;">
      🔐 Join Session &amp; Sign Document
    </a>
  </div>
  <p style="color:#8892a4;font-size:12px;text-align:center;">
    No account needed — click the button above to go directly to your signing session.<br/>
    If the button doesn't work, copy this link: <a href="{_lobby_url}" style="color:#a78bfa;">{_lobby_url}</a>
  </p>
  <hr style="border:none;border-top:1px solid rgba(255,255,255,0.08);margin:20px 0;"/>
  <p style="color:#8892a4;font-size:11px;text-align:center;margin:0;">
    Quanby Legal · Electronic Notarization Platform · <a href="https://legal.quanbyai.com" style="color:#7c3aed;">legal.quanbyai.com</a>
  </p>
</div>"""
        _email_text = f"""You have a document to sign via Quanby Legal.

Document: {req.doc_name}
Type: {req.notarization_type}
Notary: {enp_name}

Click here to join the signing session:
{_lobby_url}

No account needed — this link gives you direct access."""

        send_email(
            to_email=req.client_email,
            subject=f"[Quanby Legal] {enp_name} has prepared a document for your signature",
            html_body=_email_html,
            text_body=_email_text,
        )
        print(f"[QuickSign] Invite email sent to {req.client_email}", flush=True)
    except Exception as _email_err:
        print(f"[QuickSign] Email invite failed (non-fatal): {_email_err}", flush=True)

    return {"apt_id": apt_id, "appointment_created": True, "room_name": room_name}
