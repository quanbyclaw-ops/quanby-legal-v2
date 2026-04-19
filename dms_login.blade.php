<!DOCTYPE html>
<html lang="en">
<head>
  <link rel="icon" href="/favicon.ico">
  <link rel="icon" type="image/png" href="/favicon.png">
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Login &mdash; Quanby DMS</title>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
  <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.css" rel="stylesheet">
  <style>
    :root { --ql-navy: #1e3a5f; --ql-teal: #00d4c8; --ql-purple: #7c3aed; }
    body { background: #0a0e1a; min-height: 100vh; display: flex; flex-direction: column; font-family: 'Inter', 'Segoe UI', sans-serif; }
    .login-card { background: #111827; border: 1px solid rgba(255,255,255,0.08); border-radius: 12px; box-shadow: 0 20px 60px rgba(0,0,0,0.6); max-width: 420px; width: 100%; }
    .login-header { background: linear-gradient(135deg, #1e3a5f 0%, #254a78 100%); border-radius: 12px 12px 0 0; padding: 32px 24px 24px; text-align: center; border-bottom: 3px solid var(--ql-teal); }
    .form-control { background: rgba(0,0,0,0.3); border-color: rgba(255,255,255,0.1); color: #e6edf3; }
    .form-control:focus { background: rgba(0,0,0,0.3); border-color: #00d4c8; color: #e6edf3; box-shadow: 0 0 0 0.2rem rgba(0,212,200,0.2); }
    .form-control::placeholder { color: #475569; }
    .btn-login { background: linear-gradient(135deg,#7c3aed,#9d5ff3); color: white; width: 100%; padding: 12px; font-weight: 700; border: none; border-radius: 8px; }
    .btn-login:hover { opacity: 0.88; }
  </style>
</head>
<body>
  <div class="d-flex align-items-center justify-content-center flex-grow-1 p-3">
    <div class="login-card">
      <div class="login-header">
        <i class="bi bi-folder2-open" style="font-size:3rem;color:var(--ql-teal)"></i>
        <h4 style="color:var(--ql-teal);font-weight:800;margin:8px 0 4px">Quanby DMS</h4>
        <p style="color:rgba(255,255,255,0.8);font-size:0.8rem;margin:0">Quanby Solutions, Inc.<br>Electronic Document Management System</p>
      </div>
      <div class="p-4">
        <h6 class="text-center mb-4" style="color:#94a3b8;">Sign in to your account</h6>

        @if($errors->any())
          <div class="alert alert-danger py-2 small">
            <i class="bi bi-exclamation-circle me-1"></i>{{ $errors->first() }}
          </div>
        @endif

        <form method="POST" action="{{ route('login') }}">
          @csrf
          <div class="mb-3">
            <label class="form-label fw-semibold small" style="color:#94a3b8;">Email Address</label>
            <div class="input-group">
              <span class="input-group-text" style="background:rgba(0,0,0,0.3);border-color:rgba(255,255,255,0.1);color:#94a3b8;"><i class="bi bi-envelope"></i></span>
              <input type="email" name="email" class="form-control @error('email') is-invalid @enderror"
                value="{{ old('email') }}" placeholder="your@email.com" required autofocus>
            </div>
          </div>
          <div class="mb-3">
            <label class="form-label fw-semibold small" style="color:#94a3b8;">Password</label>
            <div class="input-group">
              <span class="input-group-text" style="background:rgba(0,0,0,0.3);border-color:rgba(255,255,255,0.1);color:#94a3b8;"><i class="bi bi-lock"></i></span>
              <input type="password" name="password" class="form-control" placeholder="••••••••" required>
            </div>
          </div>
          <div class="mb-4 d-flex align-items-center">
            <div class="form-check">
              <input class="form-check-input" type="checkbox" name="remember" id="remember">
              <label class="form-check-label small" style="color:#94a3b8;" for="remember">Remember me</label>
            </div>
          </div>
          <button type="submit" class="btn btn-login rounded-2">
            <i class="bi bi-box-arrow-in-right me-2"></i>Sign In
          </button>
        </form>

        <div class="text-center mt-4 pt-3 border-top">
          <small style="color:#475569;">
            <i class="bi bi-shield-lock me-1"></i>
            Authorized users only &mdash; Quanby Solutions, Inc.
          </small>
        </div>
      </div>
    </div>
  </div>
  <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
