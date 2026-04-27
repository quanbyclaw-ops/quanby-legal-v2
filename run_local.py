"""
Local dev launcher for QLegal.

Behavior:
- Imports the FastAPI app from backend/main.py
- Mounts the repo root (HTML frontends) as static files
- Rewrites SPA-style routes (/auth-complete, /onboard, /session, /dashboard, etc.)
  to serve the correct HTML file, so URLs that production nginx handles via
  try_files work here too.
- Runs uvicorn on 127.0.0.1:8080 (matches APP_PORT / nginx prod setup).

Usage:
    source .venv/bin/activate
    python run_local.py
"""
import os
import sys
from pathlib import Path

# Make `backend/` importable as top-level (so `from main import app` works)
ROOT = Path(__file__).resolve().parent
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))
os.chdir(BACKEND)  # main.py uses relative paths for data/, etc.

from fastapi import FastAPI  # noqa: E402
from fastapi.responses import FileResponse, HTMLResponse  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402

from main import app  # noqa: E402  (loads .env, registers all routes)

# ---------------------------------------------------------------------------
# SPA-style frontend routes → explicit HTML files
#
# Nginx in prod does `try_files $uri $uri/ /index.html;`. We emulate the
# named routes the app actually uses. index.html is mounted last as a catch-all.
# ---------------------------------------------------------------------------
FRONTEND_ROUTES = {
    "/": "index.html",
    "/index.html": "index.html",
    "/auth-complete": "onboard.html",   # onboard flow picks up ?step=
    "/onboard": "onboard.html",
    "/login": "login.html",
    "/signin": "login.html",
    "/dashboard": "dashboard.html",
    "/appointments": "appointments.html",
    "/browse": "browse.html",
    "/profile": "profile.html",
    "/calendar": "calendar.html",
    "/registry": "registry.html",
    "/session": "session.html",
    "/lobby": "lobby.html",
    "/quicksign": "quicksign.html",
    "/admin": "admin.html",
    "/suborgs": "suborgs.html",
    "/test-room": "test-room.html",
    "/messages": "messages.html",
}

for route, fname in FRONTEND_ROUTES.items():
    html_path = ROOT / fname
    if not html_path.exists():
        continue

    def _make_handler(p: Path):
        async def _serve():
            return FileResponse(str(p))
        return _serve

    # Do NOT register "/" — StaticFiles mount below handles it and avoids
    # colliding with FastAPI API routes.
    if route == "/":
        continue
    app.add_api_route(route, _make_handler(html_path), methods=["GET"], include_in_schema=False)


# Static assets + catch-all for root. Must be mounted LAST so /api/* still wins.
class _SpaStatic(StaticFiles):
    """Serve files from repo root; fall back to index.html for unknown paths."""

    async def get_response(self, path, scope):
        full = Path(self.directory) / path
        if full.is_file():
            return await super().get_response(path, scope)
        # fall back to index.html for SPA-style deep links
        return await super().get_response("index.html", scope)


app.mount("/", _SpaStatic(directory=str(ROOT), html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("APP_PORT", 8080))
    print(f"\n  QLegal local dev server")
    print(f"  → http://localhost:{port}\n")
    uvicorn.run(app, host="127.0.0.1", port=port, reload=False, log_level="info")
